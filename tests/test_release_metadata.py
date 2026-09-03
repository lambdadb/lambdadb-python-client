"""Tests for release metadata immutability checks."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validate_release_metadata.py"
SPEC = importlib.util.spec_from_file_location("validate_release_metadata", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _release_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str
) -> ModuleType:
    (tmp_path / "src/lambdadb").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "lambdadb"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    (tmp_path / "src/lambdadb/version.py").write_text(
        f'SDK_VERSION = "{version}"\n', encoding="utf-8"
    )
    (tmp_path / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## {version}\n", encoding="utf-8"
    )
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    return MODULE


def test_validator_rejects_release_name_that_differs_from_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _release_tree(tmp_path, monkeypatch, "0.9.0rc1")
    with pytest.raises(ValueError, match="name must exactly match tag"):
        module.validate_release_metadata(
            release_tag="v0.9.0rc1",
            release_name="Different",
            release_is_prerelease=True,
        )


def test_validator_rejects_prerelease_flag_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _release_tree(tmp_path, monkeypatch, "0.9.0rc1")
    with pytest.raises(ValueError, match="prerelease flag"):
        module.validate_release_metadata(
            release_tag="v0.9.0rc1",
            release_name="v0.9.0rc1",
            release_is_prerelease=False,
        )


@pytest.mark.parametrize(
    ("version", "is_prerelease"),
    [("0.9.0rc1", True), ("0.9.0", False)],
)
def test_validator_accepts_matching_rc_and_stable_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    version: str,
    is_prerelease: bool,
) -> None:
    module = _release_tree(tmp_path, monkeypatch, version)

    assert (
        module.validate_release_metadata(
            release_tag=f"v{version}",
            release_name=f"v{version}",
            release_is_prerelease=is_prerelease,
        )
        == version
    )


def test_validator_rejects_development_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _release_tree(tmp_path, monkeypatch, "0.9.0.dev1")
    with pytest.raises(ValueError, match="must not be published"):
        module.validate_release_metadata(
            release_tag="v0.9.0.dev1",
            release_name="v0.9.0.dev1",
            release_is_prerelease=True,
        )


def test_validator_rejects_noncanonical_pep440_tag() -> None:
    with pytest.raises(ValueError, match="canonical PEP 440"):
        MODULE.validate_release_metadata(
            release_tag="v0.9.0-rc.1",
            release_name="v0.9.0-rc.1",
            release_is_prerelease=True,
        )


def test_validator_requires_exact_changelog_heading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _release_tree(tmp_path, monkeypatch, "0.9.0rc1")
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## Unreleased\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="level-2 heading"):
        module.validate_release_metadata(
            release_tag="v0.9.0rc1",
            release_name="v0.9.0rc1",
            release_is_prerelease=True,
        )
