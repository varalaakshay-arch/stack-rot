# stack-rot

A dependency health scanner that finds dead, deprecated, and abandoned packages in your project — and tells you what to migrate to.

```
📦 stack-rot v0.1 — scanning ./package.json

🪦 ABANDONED (1 package):
  ❌ moment 2.24.0
     → In maintenance mode since 2020. Maintainers officially recommend alternatives.
     → Migrate to: dayjs, date-fns, luxon
     → Evidence: https://momentjs.com/docs/#/-project-status/

⚠️  DEPRECATED (2 packages):
  ❌ brute-knex 4.0.1
     → Package no longer supported.
  ❌ path-match 1.2.4
     → Archived and no longer maintained.

✅ HEALTHY (207 packages)

────────────────────────────────────────
📊 Project health: 9.9/10
   207/210 dependencies are healthy (2 unknown packages excluded).
```

The example above is a real scan of [TryGhost/Ghost](https://github.com/TryGhost/Ghost).

## What it does

`stack-rot` reads your `package.json` and reports which dependencies are:

- **Abandoned** — community has moved away, even if the registry doesn't say so (e.g. moment)
- **Deprecated** — officially marked deprecated on npm or by maintainers (e.g. request, node-sass)
- **Healthy** — actively maintained

For each problematic dependency, it tells you:

- Why it's flagged
- A link to public evidence (maintainer announcement, deprecation notice, archived repo)
- Recommended alternatives

## Why this exists

Existing tools handle adjacent problems:

| Tool | Primary focus |
|---|---|
| `npm outdated` | Newer versions available |
| `npm audit` | Security vulnerabilities |
| Dependabot | Automated version bumps |
| Snyk | Security vulnerabilities + license issues |
| Socket.dev | Supply-chain risk |
| `stack-rot` | Community migration intelligence (open-source, free, CLI) |

None of those answer the question developers actually ask when they inherit an old codebase: *which of these packages should I stop using?*

`stack-rot` answers that. It combines a hand-curated database of known-abandoned packages with the npm registry's deprecation flag to surface problems no other tool catches.

## Install

```
pip install stack-rot
```

Requires Python 3.10 or newer.

## Usage

Scan the `package.json` in the current directory:

```
stack-rot
```

Scan a specific file:

```
stack-rot path/to/package.json
```

Scan without hitting the npm registry (uses only the curated database):

```
stack-rot --no-network
```

Exit codes:

- `0` — no abandoned or deprecated dependencies found
- `1` — problems found (useful for CI)
- `2` — error reading the manifest

## What's in v0.1

- JavaScript / npm support (reads `package.json`, queries `https://registry.npmjs.org`)
- 8 hand-verified entries in the curated database, each with an evidence URL
- Live npm deprecation detection for every other package on the registry

## Roadmap

- **v0.2** — Python (`requirements.txt`, `pyproject.toml`)
- **v0.3** — Automated abandonment signals (last-publish dates, repo activity)
- **v0.4** — Go (`go.mod`)
- **v0.5** — Rust (`Cargo.toml`)
- **v0.6** — Community sentiment data from public sources
- **v0.7** — JSON/HTML reports, CI mode, GitHub Action
- **v0.8** — Safe codemods for trivial migrations
- **v0.9** — Web dashboard and README badges
- **v1.0** — Stability and sustainability

## Contributing

The curated database (`src/stack_rot/rot-db.json`) grows by community contribution. Every new entry requires:

- A `status` of `dead`, `deprecated`, or `stale`
- A `reason` explaining the verdict
- A list of at least one `alternative` package
- A public `evidence` URL (maintainer announcement, deprecation notice, archived repo, or registry flag)
- `verified_by` and `verified_date` fields

PRs missing any of these will be rejected automatically. See `CONTRIBUTING.md` for full rules.

## License

MIT. See `LICENSE`.