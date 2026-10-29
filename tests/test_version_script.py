"""Tests for scripts/version.py, which sets every package version source."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/version.py"
SPEC = importlib.util.spec_from_file_location("version_script", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

PYPROJECT = """\
# Keep this comment.
[project]
name = "lambdadb"
version = "{version}"
dependencies = [
    "httpx >=0.28.1,<1",
]

[tool.example]
version = "9.9.9"
"""

RUNTIME = """\
\"\"\"Runtime version and SDK metadata.\"\"\"

TITLE: str = "lambdadb"
SDK_VERSION: str = "{version}"
GEN_VERSION: str = "2.798.0"
"""


def _tree(root: Path, version: str, runtime_version: str | None = None) -> Path:
    (root / "src/lambdadb").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        PYPROJECT.format(version=version), encoding="utf-8"
    )
    (root / "src/lambdadb/version.py").write_text(
        RUNTIME.format(version=runtime_version or version), encoding="utf-8"
    )
    return root


def _snapshot(root: Path) -> dict[str, str]:
    return {
        path: (root / path).read_text(encoding="utf-8")
        for path in ("pyproject.toml", "src/lambdadb/version.py")
    }


def test_repository_commits_a_supported_version() -> None:
    version = MODULE.read_version()
    assert MODULE.COMMITTED_VERSION.fullmatch(version)


@pytest.mark.parametrize("version", ["0.13.1.dev0", "0.14.0rc1", "0.14.0rc12", "1.0.0"])
def test_set_updates_every_source_and_preserves_formatting(
    tmp_path: Path, version: str
) -> None:
    root = _tree(tmp_path, "0.13.0")

    assert MODULE.set_version(version, root) == version
    assert MODULE.read_version(root) == version
    assert _snapshot(root) == {
        "pyproject.toml": PYPROJECT.format(version=version),
        "src/lambdadb/version.py": RUNTIME.format(version=version),
    }


@pytest.mark.parametrize(
    "version",
    [
        "0.13.1.dev3",
        "0.13.1.dev",
        "0.13.1rc0",
        "0.13.1-rc.1",
        "0.13.1-dev.0",
        "0.13.1a1",
        "0.13.1.post1",
        "v0.13.1",
        "0.13",
        "01.2.3",
    ],
)
def test_set_accepts_only_committed_forms(tmp_path: Path, version: str) -> None:
    root = _tree(tmp_path, "0.13.0")
    before = _snapshot(root)

    with pytest.raises(ValueError, match="Unsupported version"):
        MODULE.set_version(version, root)
    assert _snapshot(root) == before


def test_mismatched_sources_are_rejected_without_mutation(tmp_path: Path) -> None:
    root = _tree(tmp_path, "0.13.0", runtime_version="0.12.1")
    before = _snapshot(root)

    with pytest.raises(ValueError, match="Version sources must agree"):
        MODULE.read_version(root)
    with pytest.raises(ValueError, match="Version sources must agree"):
        MODULE.set_version("0.13.1.dev0", root)
    assert _snapshot(root) == before


@pytest.mark.parametrize(
    ("released", "expected"),
    [
        ("0.14.0rc1", "0.14.0.dev0"),
        ("0.14.0rc12", "0.14.0.dev0"),
        ("0.13.0", "0.13.1.dev0"),
        ("1.9.9", "1.9.10.dev0"),
    ],
)
def test_next_dev_follows_rc_and_stable_releases(released: str, expected: str) -> None:
    assert MODULE.next_dev_version(released) == expected


@pytest.mark.parametrize("released", ["0.13.1.dev0", "0.13.1.dev4", "0.13.1rc0", "v0.13.0"])
def test_next_dev_rejects_unreleased_versions(released: str) -> None:
    with pytest.raises(ValueError, match="Expected an RC or stable version"):
        MODULE.next_dev_version(released)


def test_cli_reports_usage_and_errors() -> None:
    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    assert run("get").stdout.strip() == MODULE.read_version()
    assert run("next-dev", "0.13.0").stdout.strip() == "0.13.1.dev0"
    assert run().returncode == 2
    failed = run("next-dev", "0.13.1.dev0")
    assert failed.returncode == 1
    assert "Expected an RC or stable version" in failed.stderr
