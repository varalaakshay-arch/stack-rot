"""Command-line entry point for stack-rot.

Usage:
    stack-rot                       # scan ./package.json in current directory
    stack-rot path/to/package.json  # scan a specific file
    stack-rot --no-network          # skip the npm registry, use rot-db only
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from stack_rot.parsers import ManifestError, parse_package_json
from stack_rot.registry import Registry
from stack_rot.report import render
from stack_rot.rotdb import RotDB
from stack_rot.scanner import Finding, scan


@click.command()
@click.argument(
    "path",
    type=click.Path(path_type=Path),
    required=False,
)
@click.option(
    "--no-network",
    is_flag=True,
    default=False,
    help="Skip the npm registry. Use only the curated rot-db.",
)
@click.version_option(package_name="stack-rot", prog_name="stack-rot")
def main(path: Path | None, no_network: bool) -> None:
    """Scan a project's dependencies for dead, deprecated, or abandoned packages."""
    manifest_path = _resolve_manifest(path)
    if manifest_path is None:
        click.echo(
            "error: no package.json found. Pass a path or run from a project directory.",
            err=True,
        )
        sys.exit(2)

    try:
        deps = parse_package_json(manifest_path)
    except ManifestError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(2)

    rotdb = RotDB.load_default()

    findings: list[Finding]
    if no_network:
        with _OfflineRegistry() as reg:
            findings = scan(deps, rotdb, reg)
    else:
        with Registry() as reg:
            findings = scan(deps, rotdb, reg)

    render(manifest_path, findings)

    # Non-zero exit if anything is dead/deprecated. Lets CI fail the build.
    bad = any(f.status in ("dead", "deprecated") for f in findings)
    sys.exit(1 if bad else 0)


def _resolve_manifest(path: Path | None) -> Path | None:
    if path is None:
        candidate = Path.cwd() / "package.json"
        return candidate if candidate.exists() else None
    if path.is_dir():
        candidate = path / "package.json"
        return candidate if candidate.exists() else None
    return path if path.exists() else None


class _OfflineRegistry:
    """A Registry stub that returns 'unknown' for everything.

    Used with --no-network so the rot-db can be queried without
    hitting npm at all.
    """

    def fetch(self, package_name):  # noqa: D401
        from stack_rot.registry import RegistryInfo
        return RegistryInfo(name=package_name)

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return None