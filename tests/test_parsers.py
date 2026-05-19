"""Tests for stack_rot.parsers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from stack_rot.parsers import Dependency, ManifestError, parse_package_json


def _write(tmp_path: Path, content: dict | str) -> Path:
    path = tmp_path / "package.json"
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_text(json.dumps(content), encoding="utf-8")
    return path


def test_parses_runtime_dependencies(tmp_path: Path) -> None:
    path = _write(tmp_path, {"dependencies": {"moment": "^2.29.4"}})
    deps = parse_package_json(path)
    assert deps == [
        Dependency(name="moment", version_spec="^2.29.4", ecosystem="npm", dep_type="runtime")
    ]


def test_parses_dev_dependencies(tmp_path: Path) -> None:
    path = _write(tmp_path, {"devDependencies": {"mocha": "^10.2.0"}})
    deps = parse_package_json(path)
    assert deps == [
        Dependency(name="mocha", version_spec="^10.2.0", ecosystem="npm", dep_type="dev")
    ]


def test_parses_both_sections(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        {
            "dependencies": {"a": "1.0.0"},
            "devDependencies": {"b": "2.0.0"},
        },
    )
    deps = parse_package_json(path)
    names = [(d.name, d.dep_type) for d in deps]
    assert ("a", "runtime") in names
    assert ("b", "dev") in names


def test_handles_missing_sections(tmp_path: Path) -> None:
    path = _write(tmp_path, {"name": "lonely"})
    deps = parse_package_json(path)
    assert deps == []


def test_handles_null_dependencies(tmp_path: Path) -> None:
    """If a package.json has 'dependencies': null, don't crash."""
    path = _write(tmp_path, {"dependencies": None, "devDependencies": None})
    deps = parse_package_json(path)
    assert deps == []


def test_raises_on_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    with pytest.raises(ManifestError, match="No such file"):
        parse_package_json(missing)


def test_raises_on_invalid_json(tmp_path: Path) -> None:
    path = _write(tmp_path, "{ not valid json")
    with pytest.raises(ManifestError, match="Invalid JSON"):
        parse_package_json(path)


def test_raises_on_non_object_root(tmp_path: Path) -> None:
    path = _write(tmp_path, "[1, 2, 3]")
    with pytest.raises(ManifestError, match="not a JSON object"):
        parse_package_json(path)


def test_version_as_non_string_coerced(tmp_path: Path) -> None:
    """package.json should have string versions, but tolerate weird inputs."""
    path = _write(tmp_path, {"dependencies": {"x": 1}})
    deps = parse_package_json(path)
    assert deps[0].version_spec == "1"