"""Tests for scripts/version.py, which sets every package version source."""

from __future__ import annotations

import importlib.util
import os
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


@pytest.mark.parametrize("version", ["0.14.0rc1", "0.14.0rc12", "1.0.0"])
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
        "0.13.1.dev0",
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
        MODULE.set_version("0.13.1rc1", root)
    assert _snapshot(root) == before


def _git(root: Path, *args: str) -> str:
    config = root.parent / "gitconfig"
    config.write_text(
        "[user]\n\tname = Version Test\n\temail = version-test@example.com\n"
        "[commit]\n\tgpgsign = false\n[tag]\n\tgpgsign = false\n"
        "[core]\n\thooksPath = /dev/null\n[init]\n\tdefaultBranch = main\n",
        encoding="utf-8",
    )
    env = {**os.environ, "GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"}
    result = subprocess.run(
        ["git", *args], cwd=root, env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _release(root: Path, version: str) -> None:
    """Commit and tag a release on the current branch."""
    MODULE.set_version(version, root)
    _git(root, "commit", "-am", f"Release {version}")
    _git(root, "tag", f"v{version}")


def _repo(tmp_path: Path) -> Path:
    root = _tree(tmp_path / "repo", "0.9.0")
    _git(root, "init")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "Release 0.9.0")
    _git(root, "tag", "v0.9.0")
    _release(root, "0.10.0")
    return root


def test_development_version_after_stable_counts_first_parent_commits(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    # A merge counts once on main; its side-branch commits do not count, nor
    # does a stable tag that HEAD cannot reach.
    _git(root, "checkout", "-b", "side")
    _git(root, "commit", "--allow-empty", "-m", "Side 1")
    _git(root, "commit", "--allow-empty", "-m", "Side 2")
    _git(root, "checkout", "-b", "unmerged", "main")
    _git(root, "commit", "--allow-empty", "-m", "Unmerged")
    _git(root, "tag", "v0.99.0")
    _git(root, "checkout", "main")
    _git(root, "commit", "--allow-empty", "-m", "Change 1")
    _git(root, "merge", "--no-ff", "-m", "Merge side", "side")

    # v0.10.0 is newer than v0.9.0 although it sorts first as text.
    assert MODULE.development_version(root) == "0.10.1.dev2"


def test_development_version_after_rc_keeps_the_core_and_counts_from_stable(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    _git(root, "commit", "--allow-empty", "-m", "Change 1")
    _release(root, "0.11.0rc1")
    _git(root, "commit", "--allow-empty", "-m", "Change 2")

    # N counts from v0.10.0; RC tags do not reset it.
    assert MODULE.development_version(root) == "0.11.0.dev3"
    assert MODULE.read_version(root) == "0.11.0rc1"
    assert MODULE.set_development_version(root) == "0.11.0.dev3"
    assert MODULE.read_version(root) == "0.11.0.dev3"


def test_development_version_without_a_stable_tag_counts_every_commit(
    tmp_path: Path,
) -> None:
    root = _tree(tmp_path / "repo", "0.1.0rc1")
    _git(root, "init")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "Initial")
    _git(root, "tag", "v0.1.0rc1")
    _git(root, "commit", "--allow-empty", "-m", "Change 1")

    assert MODULE.development_version(root) == "0.1.0.dev2"


def test_development_version_requires_a_commit_after_the_stable_tag(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    before = _snapshot(root)

    with pytest.raises(ValueError, match="at least one first-parent commit"):
        MODULE.set_development_version(root)
    assert _snapshot(root) == before


def test_development_version_rejects_a_committed_development_version(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    MODULE._write_version("0.10.1.dev0", root)
    _git(root, "commit", "-am", "Commit a development version")

    with pytest.raises(ValueError, match="must be an RC or stable version"):
        MODULE.development_version(root)


def test_cli_reports_usage_and_errors() -> None:
    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    assert run("get").stdout.strip() == MODULE.read_version()
    assert run().returncode == 2
    assert run("next-dev", "0.13.0").returncode == 2
    assert run("set-dev", "0.13.1.dev1").returncode == 2
