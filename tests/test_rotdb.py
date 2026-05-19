"""Tests for stack_rot.rotdb."""

from __future__ import annotations

import json

import pytest

from stack_rot.rotdb import RotDB


def _make_db(packages: dict) -> RotDB:
    return RotDB.from_json(json.dumps({"packages": packages}))


def test_loads_default_database() -> None:
    """The bundled rot-db.json must load and contain at least one entry."""
    db = RotDB.load_default()
    assert len(db) > 0
    assert db.lookup("moment", "npm") is not None


def test_lookup_returns_none_for_unknown_package() -> None:
    db = _make_db({})
    assert db.lookup("totally-fake", "npm") is None


def test_lookup_is_scoped_by_ecosystem() -> None:
    db = _make_db(
        {
            "shared-name": {
                "ecosystem": "npm",
                "status": "dead",
                "reason": "test",
                "alternatives": ["alt"],
                "evidence": "https://example.com",
                "verified_by": "test",
                "verified_date": "2026-05-19",
            }
        }
    )
    assert db.lookup("shared-name", "npm") is not None
    assert db.lookup("shared-name", "pypi") is None


def test_alternatives_are_tuple() -> None:
    """Alternatives should be immutable so they can't be accidentally mutated."""
    db = _make_db(
        {
            "x": {
                "ecosystem": "npm",
                "status": "dead",
                "reason": "test",
                "alternatives": ["a", "b"],
                "evidence": "https://example.com",
                "verified_by": "test",
                "verified_date": "2026-05-19",
            }
        }
    )
    entry = db.lookup("x", "npm")
    assert entry is not None
    assert entry.alternatives == ("a", "b")
    assert isinstance(entry.alternatives, tuple)


def test_default_db_entries_have_required_fields() -> None:
    """Every entry in the bundled rot-db.json must have the full schema."""
    db = RotDB.load_default()
    # Sample a known entry
    entry = db.lookup("moment", "npm")
    assert entry is not None
    assert entry.status in {"dead", "deprecated", "stale", "healthy", "warning"}
    assert entry.reason
    assert entry.alternatives
    assert entry.evidence.startswith("http")
    assert entry.verified_by
    assert entry.verified_date