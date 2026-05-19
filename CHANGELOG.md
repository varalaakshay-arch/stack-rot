# Changelog

All notable changes to stack-rot are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-19

First release.

### Added

- CLI command `stack-rot` that scans a `package.json` and reports dependency health.
- npm registry client that detects packages marked deprecated.
- Curated rot database (`rot-db.json`) with 8 verified entries: `moment`, `request`, `node-sass`, `tslint`, `bower`, `coffee-script`, `phantomjs`, `phantomjs-prebuilt`.
- Terminal report with severity buckets, recommended alternatives, evidence URLs, and a 0–10 project health score.
- `--no-network` flag for offline scans against the curated database only.
- Exit codes for CI integration: `0` clean, `1` problems found, `2` error.
- 14 pytest tests covering parsing and rot-db loading.

### Notes

- Python 3.10 or newer is required.
- The curated database starts intentionally small. Entries grow by community contribution (see `CONTRIBUTING.md`).