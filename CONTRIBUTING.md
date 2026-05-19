# Contributing to stack-rot

Thanks for wanting to help. This guide covers what we accept and what we don't.

## Adding an entry to rot-db.json

The curated database is the heart of this project. Every entry must meet the following requirements or it will be rejected.

### Required fields

Every entry in `src/stack_rot/rot-db.json` must have all of:

```json
"package-name": {
  "ecosystem": "npm",
  "status": "dead | deprecated | stale",
  "reason": "Short explanation of why this package is flagged.",
  "alternatives": ["replacement-1", "replacement-2"],
  "evidence": "https://...",
  "verified_by": "your-github-username",
  "verified_date": "YYYY-MM-DD"
}
```

### Status definitions

- **`deprecated`** — the registry has flagged the package as deprecated, or the maintainers have officially announced sunset.
- **`dead`** — not officially deprecated, but the community has clearly moved on (e.g. `moment`). Requires stronger evidence than `deprecated`.
- **`stale`** — significant inactivity (last release > 18 months) and the maintainer has acknowledged the project is unmaintained. Do not use this status for packages that simply released slowly.

### Evidence requirements

The `evidence` URL must be a public, verifiable source. Acceptable sources:

- An official maintainer announcement (blog post, GitHub issue, README notice)
- A registry deprecation flag (e.g. an npm page showing the package as deprecated)
- A GitHub repo marked archived
- A pinned issue from the maintainer confirming the project is no longer maintained

Not acceptable:

- A random blog post
- A Stack Overflow answer
- Your personal opinion that the project is dead
- An issue from a non-maintainer saying the project is dead

### Alternatives requirements

Every entry must list at least one `alternative`. Each alternative should:

- Be a real, installable package
- Be actively maintained (last release within the past 12 months)
- Be a reasonable replacement for the deprecated package's use case

Do not list more than five alternatives. If there are more, pick the most popular and well-maintained ones.

### Before you submit

1. Verify the evidence URL works.
2. Run `uv run pytest -v` to confirm the existing test suite still passes.
3. Make sure the JSON is valid (`python -m json.tool src/stack_rot/rot-db.json`).

PRs that fail any of these will be asked to fix the issue before review.

## Reporting bugs

Open an issue with:

- The command you ran
- The output you got
- The output you expected
- Your Python version (`python --version`)
- A minimal `package.json` that reproduces the issue, if possible

## Code contributions

For changes to the scanner, parser, or report code:

1. Open an issue first if it's non-trivial. Avoids duplicate work.
2. Keep changes focused. One feature or fix per PR.
3. Add or update tests for any logic change.
4. Match the existing code style (small files, single-purpose, type hints).

## Code of conduct

Be respectful. Disagree on technical grounds, not personal ones. We don't have a separate `CODE_OF_CONDUCT.md` yet; this paragraph is the policy.

## License

By contributing, you agree your contribution is licensed under the same MIT license as the project.