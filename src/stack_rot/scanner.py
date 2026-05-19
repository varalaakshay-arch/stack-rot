"""Scan dependencies against the rot DB and registry signals.

For each dependency, produce a Finding describing its health. The order
of precedence:

  1. Curated entry in rot-db.json wins (it has human-verified evidence)
  2. Otherwise, npm's deprecation flag wins
  3. Otherwise, package looks healthy

v0.1 does not do automated abandonment detection from last-publish dates
or commit activity. That arrives in v0.3.
"""

from __future__ import annotations

from dataclasses import dataclass

from stack_rot.parsers import Dependency
from stack_rot.registry import Registry, RegistryInfo
from stack_rot.rotdb import RotDB, RotEntry


@dataclass(frozen=True)
class Finding:
    """The result of evaluating a single dependency."""

    dependency: Dependency
    status: str
    reason: str
    alternatives: tuple[str, ...]
    evidence: str | None
    source: str


def scan(
    dependencies: list[Dependency],
    rotdb: RotDB,
    registry: Registry,
) -> list[Finding]:
    """Evaluate each dependency. Returns one Finding per dependency."""
    findings: list[Finding] = []
    for dep in dependencies:
        findings.append(_evaluate(dep, rotdb, registry))
    return findings


def _evaluate(
    dep: Dependency,
    rotdb: RotDB,
    registry: Registry,
) -> Finding:
    # 1. Curated rot-db entry wins
    entry = rotdb.lookup(dep.name, dep.ecosystem)
    if entry is not None:
        return _from_rotdb(dep, entry)

    # 2. Registry signal
    info = registry.fetch(dep.name)
    if info.not_found:
        return Finding(
            dependency=dep,
            status="unknown",
            reason="Package not found on registry.",
            alternatives=(),
            evidence=None,
            source="registry",
        )
    if info.is_deprecated:
        return _from_registry_deprecation(dep, info)

    # 3. Healthy by default
    return Finding(
        dependency=dep,
        status="healthy",
        reason="",
        alternatives=(),
        evidence=None,
        source="none",
    )


def _from_rotdb(dep: Dependency, entry: RotEntry) -> Finding:
    return Finding(
        dependency=dep,
        status=entry.status,
        reason=entry.reason,
        alternatives=entry.alternatives,
        evidence=entry.evidence,
        source="rot-db",
    )


def _from_registry_deprecation(dep: Dependency, info: RegistryInfo) -> Finding:
    message = info.deprecation_message or "Package marked deprecated on registry."
    return Finding(
        dependency=dep,
        status="deprecated",
        reason=message,
        alternatives=(),
        evidence=f"https://www.npmjs.com/package/{dep.name}",
        source="registry",
    )