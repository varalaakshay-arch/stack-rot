"""Load and query the curated rot database.

The rot database (rot-db.json) is the heart of stack-rot. It is a
hand-curated list of packages known to be dead, deprecated, or stale,
with evidence URLs and recommended alternatives.

This module loads the JSON file and exposes lookup functions. The data
is read once and cached in memory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Literal


Status = Literal["dead", "deprecated", "stale", "healthy", "warning"]


@dataclass(frozen=True)
class RotEntry:
    """A single curated entry from rot-db.json."""

    name: str
    ecosystem: str
    status: Status
    reason: str
    alternatives: tuple[str, ...]
    evidence: str
    verified_by: str
    verified_date: str


class RotDB:
    """In-memory view of the curated rot database."""

    def __init__(self, entries: dict[str, RotEntry]) -> None:
        self._entries = entries

    @classmethod
    def load_default(cls) -> "RotDB":
        """Load the rot-db.json file bundled with this package."""
        raw = (
            resources.files("stack_rot")
            .joinpath("rot-db.json")
            .read_text(encoding="utf-8")
        )
        return cls.from_json(raw)

    @classmethod
    def from_json(cls, raw: str) -> "RotDB":
        data = json.loads(raw)
        packages = data.get("packages") or {}

        entries: dict[str, RotEntry] = {}
        for name, fields in packages.items():
            entries[(fields["ecosystem"], name)] = RotEntry(
                name=name,
                ecosystem=fields["ecosystem"],
                status=fields["status"],
                reason=fields["reason"],
                alternatives=tuple(fields.get("alternatives") or ()),
                evidence=fields["evidence"],
                verified_by=fields["verified_by"],
                verified_date=fields["verified_date"],
            )
        return cls(entries)

    def lookup(self, name: str, ecosystem: str) -> RotEntry | None:
        """Return the entry for (ecosystem, name), or None if not curated."""
        return self._entries.get((ecosystem, name))

    def __len__(self) -> int:
        return len(self._entries)