# stack-rot Architecture

A walkthrough of every file in the project, what it does, and why it's built that way. Written for v0.1.

## Project layout
stack-rot/
├── pyproject.toml          Package manifest (metadata, dependencies, entry point)
├── README.md               Public-facing description
├── LICENSE                 MIT license text
├── CONTRIBUTING.md         Rules for rot-db entries and PRs
├── CHANGELOG.md            Version history
├── .gitignore              Files git should not track
├── uv.lock                 Exact dependency versions (lockfile)
├── .python-version         Python version pin for local dev
├── docs/
│   └── ARCHITECTURE.md     This file
├── src/
│   └── stack_rot/
│       ├── init.py     Package marker (empty)
│       ├── parsers.py      Reads package.json into Dependency objects
│       ├── registry.py     Talks to npm registry, returns metadata
│       ├── rotdb.py        Loads the curated rot database
│       ├── rot-db.json     The curated database (8 entries)
│       ├── scanner.py      Combines parser + rotdb + registry, returns findings
│       ├── report.py       Renders findings to the terminal with colors
│       └── cli.py          The stack-rot command entry point
└── tests/
├── init.py         Package marker
├── test_parsers.py     9 tests for parsers.py
├── test_rotdb.py       5 tests for rotdb.py
└── fixtures/           Sample package.json files for testing
├── sample-package.json
└── real/           Real-world project manifests downloaded for smoke tests

## The source files, in dependency order

The modules build on each other. Reading them in this order makes the architecture clear.

### `parsers.py` — input layer

**Job:** Read a `package.json` file and return a list of `Dependency` objects.

**Key things in this file:**

- `Dependency` dataclass — a typed record with `name`, `version_spec`, `ecosystem`, `dep_type`. Frozen (immutable) to prevent accidental mutation.
- `ManifestError` exception — raised when the file is missing or malformed. A custom exception type lets callers catch parsing failures specifically.
- `parse_package_json(path)` — the public function. Reads the file, parses JSON, walks `dependencies` and `devDependencies` keys, returns a flat list.

**Why it looks this way:**

- Using a dataclass instead of a raw dict means future code gets type checking and IDE autocomplete. Costs nothing.
- The `(data.get("dependencies") or {}).items()` pattern handles the case where the JSON has `"dependencies": null` or no `dependencies` key at all. Defensive.
- `version_spec=str(version)` coerces non-string values to strings. Real-world `package.json` files sometimes have integers in version fields.

**What's NOT in v0.1:**

- Python parsing (`requirements.txt`) — coming in v0.2.
- Workspace/monorepo handling — currently treats workspace packages as regular deps that fail to look up. Good enough for v0.1.
- Peer/optional dependencies — ignored intentionally.

---

### `registry.py` — network layer

**Job:** Given a package name, ask npm's registry for metadata (latest version, last publish date, deprecation flag).

**Key things in this file:**

- `RegistryInfo` dataclass — typed record of what we learn about a package.
- `Registry` class — wraps an HTTP client (`httpx`) with in-memory caching. Same package asked twice = one network call.
- `fetch(package_name)` — the only public method we call from outside.
- `_fetch_uncached()` — internal method that actually hits the network. Returns empty `RegistryInfo` on failure, never raises.
- `_parse_registry_payload()` — pulls the three fields we care about (latest version, publish time, deprecation flag) from npm's giant JSON blob.

**Why it looks this way:**

- **In-memory cache** — a real project has 100-200 deps. Some appear twice across `dependencies` and `devDependencies`. Caching avoids redundant calls.
- **httpx instead of requests** — modern async-capable HTTP library. We don't use async in v0.1 but the API is nicer and we'll need async for v0.3 when we add GitHub API calls in parallel.
- **Defensive error handling** — if npm is slow, down, or returns weird data, we return an empty `RegistryInfo`. A dependency scanner that crashes on one network blip would be unusable.
- **User-Agent header** — identifies us to npm. Good open-source citizenship; if our tool misbehaves, they can find us instead of just IP-blocking.
- **`__enter__` / `__exit__`** — makes `Registry` work as a context manager (`with Registry() as r:`). Guarantees we close the HTTP connection cleanly.

---

### `rotdb.py` — the curated database loader

**Job:** Load `rot-db.json` and let other code query it by package name.

**Key things in this file:**

- `Status` type alias — restricts valid statuses to exactly five strings using `Literal`. Catches typos at lint time.
- `RotEntry` dataclass — one entry from the JSON, as a typed Python object.
- `RotDB` class — holds the entries in a dict keyed by `(ecosystem, name)`.
- `RotDB.load_default()` — loads the bundled `rot-db.json` using `importlib.resources`.
- `RotDB.from_json(raw)` — parses a JSON string into entries. Separate from `load_default()` so tests can use strings.
- `lookup(name, ecosystem)` — returns an entry or `None`.

**Why it looks this way:**

- **`importlib.resources`** instead of `open("rot-db.json")` — when users `pip install stack-rot`, the file lives deep inside site-packages, not in their current directory. `importlib.resources` is the standard way to read files bundled with a Python package.
- **Dict keyed by `(ecosystem, name)`** — currently we only have npm packages, but v0.2 adds Python, v0.4 Go, v0.5 Rust. A package named `requests` exists on both npm and PyPI. The tuple key handles that without re-architecture.
- **Tuple instead of list for alternatives** — tuples are immutable, so once loaded, no code can accidentally mutate the alternatives list of a shared entry.

---

### `rot-db.json` — the curated database

**Job:** A JSON file containing the hand-verified list of abandoned/deprecated packages.

**Schema** (per entry):

```json
"package-name": {
  "ecosystem": "npm",
  "status": "dead | deprecated | stale",
  "reason": "Why this package is flagged.",
  "alternatives": ["replacement-1", "replacement-2"],
  "evidence": "https://...",
  "verified_by": "github-username",
  "verified_date": "YYYY-MM-DD"
}
```

**Current contents (8 entries):** moment, request, node-sass, tslint, bower, coffee-script, phantomjs, phantomjs-prebuilt. Each verified against a primary source (maintainer announcement or npm deprecation flag).

**Why JSON not YAML or TOML:** every PR contributor knows JSON. Lower barrier than learning YAML's whitespace rules.

---

### `scanner.py` — the decision logic

**Job:** Combine parser output + rotdb + registry into a list of `Finding` objects.

**Key things in this file:**

- `Finding` dataclass — the verdict for one dependency. Includes status, reason, alternatives, evidence URL, and `source` (where the verdict came from).
- `scan(deps, rotdb, registry)` — public entry point. Loops over deps, evaluates each.
- `_evaluate()` — the decision tree.

**The decision tree, in priority order:**

1. **Curated rot-db entry exists?** Use it. Human-verified data beats automated signals.
2. **Registry says package is deprecated?** Flag as deprecated.
3. **Registry says package not found?** Flag as unknown (likely a private/monorepo package).
4. **Otherwise:** healthy.

**Why precedence matters:** rot-db wins because we verified it ourselves with public evidence. Registry flag is second because it's automated but reliable. Healthy is the default.

**What's NOT here:**

- Last-publish-date scoring — v0.3.
- GitHub commit activity — v0.3.
- Community sentiment — v0.6.

We don't guess. v0.1 only flags what we (or npm) explicitly know.

---

### `report.py` — output formatting

**Job:** Take a list of `Finding` objects, print a colored terminal report.

**Key things in this file:**

- `render(manifest_path, findings)` — the only public function.
- `_BUCKETS` constant — defines order (dead → deprecated → stale → unknown) and styling for each severity.
- `_group()` — splits findings into buckets so we can print "ABANDONED (3 packages)" instead of mixing.
- `_render_bucket()` — prints one severity group with name, version, reason, alternatives, evidence.
- `_render_footer()` — the 0–10 health score. Excludes unknown packages from scoring. Caps below 10.0 if any problems exist.

**Why it looks this way:**

- **`rich` library** for colors — handles Windows terminal color codes properly, falls back to plain text when piped to files or CI logs, looks good in modern terminals. The standard tool for Python CLI output.
- **Severity bucket order** — most-severe first because users scan top to bottom. Healthy is one summary line at the bottom because users don't want to scroll through 200 healthy packages.
- **Score capping at 9.9** — a project with rot should never display 10/10. Avoids "math rounded up so they ignored the report" failures.
- **Excluding unknowns from scoring** — Ghost's monorepo internals would otherwise pollute the score. We exclude them and note it transparently in the footer.

---

### `cli.py` — the command entry point

**Job:** When someone types `stack-rot` in their terminal, this runs.

**Key things in this file:**

- `@click.command()` — turns the `main` function into a CLI command.
- `@click.argument("path")` — optional positional argument for which file to scan.
- `@click.option("--no-network")` — flag to skip the registry, use only the curated database.
- `@click.version_option()` — automatic `--version` flag.
- `_resolve_manifest()` — figures out what file to scan based on the argument.
- `_OfflineRegistry` — duck-typed stub for `--no-network`. Same interface as `Registry` but always returns "unknown".

**Exit codes:**

- `0` — clean scan, no problems
- `1` — problems found (used by CI to fail the build)
- `2` — error reading the manifest

**Why it looks this way:**

- **`click` instead of `argparse`** — `click` handles `--help` generation, type coercion, error messages, and decorators cleanly. Standard for modern Python CLIs.
- **Exit codes follow Unix convention** — 0 is success, non-zero is failure. CI systems and shell pipes rely on this.
- **`_OfflineRegistry` as a stub** — same interface as the real one. The scanner code doesn't have to know which one it's using. This is called "duck typing": if it acts like a registry, it is one.

---

## The non-code files

### `pyproject.toml` — the package manifest

What it declares:
- Package name (`stack-rot`), version, description, license
- Python version requirement (`>=3.10`)
- Runtime dependencies (`click`, `httpx`, `rich`)
- Dev dependencies (`pytest`, `pytest-asyncio`)
- Entry point: `stack-rot = "stack_rot.cli:main"` — this is what makes the `stack-rot` shell command point to our `main()` function
- Bundled data: `rot-db.json` is included in the built wheel
- PyPI classifiers (Python versions, license, topic, dev status)
- URLs (homepage, repository, issues)

**Why pyproject.toml not setup.py:** pyproject.toml is the modern Python packaging standard (PEP 621). setup.py is legacy.

### `uv.lock` — the lockfile

Auto-generated by `uv sync`. Records the exact version of every dependency (including transitive ones — e.g. `httpx` requires `httpcore` which requires `h11`). Committed to git so contributors get identical installs.

### `.gitignore` — files git ignores

Tells git not to track:
- `.venv/` (virtual environment, hundreds of MB)
- `__pycache__/`, `*.pyc` (Python bytecode)
- `dist/`, `build/`, `*.egg-info/` (build artifacts)
- `.pytest_cache/` (test runner cache)
- `.vscode/`, `.idea/` (editor configs)

### `LICENSE` — MIT license

Most permissive open-source license. Lets anyone use, modify, distribute, including commercially, with attribution.

### `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`

User-facing docs. README is what visitors read first. CONTRIBUTING tells PR authors the rules. CHANGELOG documents what shipped in each version.

---

## The tests

### `tests/test_parsers.py` — 9 tests

Covers: parsing runtime deps, dev deps, missing sections, null sections, malformed JSON, missing files, non-object roots, non-string version coercion.

### `tests/test_rotdb.py` — 5 tests

Covers: loading the default bundled DB, lookup returns None for unknown packages, ecosystem scoping (npm vs pypi), alternatives are tuples not lists, default DB entries have all required fields.

### `tests/fixtures/`

Sample input files. `sample-package.json` is a controlled test case. `real/` contains downloaded `package.json` files from real projects (Ghost, Strapi, etc.) used for end-to-end smoke testing.

---

## Why this many small files instead of one big one

Three reasons:

1. **Each file does one thing.** Easier to reason about, easier to test, easier for new contributors to navigate.
2. **Future versions add features without growing existing files.** v0.2's Python parser goes in `parsers.py` alongside the npm one. v0.3's GitHub API client goes alongside `registry.py`. The current files don't need to grow.
3. **Tests stay focused.** Each test file targets one source file. When a test fails, you know which module to look at.

This is standard Python project layout. Django, Flask, requests, FastAPI all follow this pattern at different scales.

---

## Dependencies — why these three?

- **`click`** — CLI framework. Handles arg parsing, `--help`, error messages, exit codes. Used by Flask, pip, and thousands of other Python CLIs.
- **`httpx`** — HTTP client. Modern, async-capable, friendlier API than `requests`. We'll need async in v0.3.
- **`rich`** — terminal colors and formatting. Handles Windows correctly, falls back gracefully to plain text in non-TTY environments. Used by pip, poetry, and most modern Python CLIs.

Three dependencies. No more. The project plan rule was "prefer standard library over dependencies" — we used the standard library for JSON parsing, file reading, dataclasses, and type hints. We only reached for third-party libraries where they genuinely saved real work.