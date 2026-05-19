"""Parsers for dependency manifests.

v0.1 supports JavaScript only: package.json.
Future versions will add requirements.txt, go.mod, Cargo.toml, etc.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Dependency:
    """A single dependency declared in a manifest file.

    Attributes:
        name: Package name as declared (e.g. "moment", "@types/node").
        version_spec: Raw version string from the manifest (e.g. "^2.29.4").
        ecosystem: Package ecosystem ("npm" for v0.1).
        dep_type: Where it was declared ("runtime" or "dev").
    """

    name: str
    version_spec: str
    ecosystem: str
    dep_type: str


class ManifestError(Exception):
    """Raised when a manifest file is missing or malformed."""


def parse_package_json(path: Path) -> list[Dependency]:
    """Parse a package.json file and return all dependencies.

    Reads both "dependencies" and "devDependencies". Peer and optional
    dependencies are ignored in v0.1.
    """
    if not path.exists():
        raise ManifestError(f"No such file: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ManifestError(f"Invalid JSON in {path}: {e}") from e

    if not isinstance(data, dict):
        raise ManifestError(f"{path} is not a JSON object")

    deps: list[Dependency] = []

    for name, version in (data.get("dependencies") or {}).items():
        deps.append(
            Dependency(
                name=name,
                version_spec=str(version),
                ecosystem="npm",
                dep_type="runtime",
            )
        )

    for name, version in (data.get("devDependencies") or {}).items():
        deps.append(
            Dependency(
                name=name,
                version_spec=str(version),
                ecosystem="npm",
                dep_type="dev",
            )
        )

    return deps