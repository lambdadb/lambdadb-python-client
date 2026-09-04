"""Tests for release metadata immutability checks."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
from types import ModuleType

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validate_release_metadata.py"
SPEC = importlib.util.spec_from_file_location("validate_release_metadata", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize("version", ["0.9.0.dev1", "10.20.30.dev40"])
def test_development_validator_accepts_exact_channel(version: str) -> None:
    assert (
        MODULE.validate_development_metadata(
            project_version_text=version,
            runtime_version_text=version,
        )
        == version
    )


@pytest.mark.parametrize(
    "version",
    [
        "1.2.dev3",
        "1!1.2.3.dev4",
        "1.2.3rc1.dev4",
        "1.2.3.dev4+local",
        "1.2.3",
        "1.2.3rc1",
    ],
)
def test_development_validator_rejects_versions_outside_exact_channel(
    version: str,
) -> None:
    with pytest.raises(ValueError, match=r"exactly an X\.Y\.Z\.devN"):
        MODULE.validate_development_metadata(
            project_version_text=version,
            runtime_version_text=version,
        )


def test_development_validator_rejects_runtime_version_mismatch() -> None:
    with pytest.raises(ValueError, match="Project and runtime versions must match"):
        MODULE.validate_development_metadata(
            project_version_text="0.9.0.dev1",
            runtime_version_text="0.9.0.dev2",
        )


def _project_requirements() -> dict[str, Requirement]:
    pyproject = (SCRIPT.parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r"(?ms)^dependencies\s*=\s*\[(?P<body>.*?)^\]", pyproject)
    assert match is not None
    requirements = [
        Requirement(value) for value in re.findall(r'"([^"]+)"', match.group("body"))
    ]
    return {requirement.name: requirement for requirement in requirements}


@pytest.mark.parametrize(
    ("name", "supported", "next_major_prerelease"),
    [
        ("httpcore", "1.0.9", "2.0.dev1"),
        ("httpx", "0.28.1", "1.0.dev1"),
        ("pydantic", "2.11.2", "3.0a1"),
    ],
)
def test_runtime_dependencies_exclude_incompatible_major_prereleases(
    name: str, supported: str, next_major_prerelease: str
) -> None:
    requirement = _project_requirements()[name]

    assert requirement.specifier.contains(Version(supported), prereleases=True)
    assert not requirement.specifier.contains(
        Version(next_major_prerelease), prereleases=True
    )


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


@pytest.mark.parametrize(
    "version",
    ["0.9", "0.9.0.post1", "1!0.9.0", "0.9.0+private", "0.9.0a1"],
)
def test_validator_rejects_versions_outside_stable_and_rc_channels(
    version: str,
) -> None:
    with pytest.raises(ValueError, match=r"exactly X\.Y\.Z or X\.Y\.ZrcN"):
        MODULE.validate_release_metadata(
            release_tag=f"v{version}",
            release_name=f"v{version}",
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
