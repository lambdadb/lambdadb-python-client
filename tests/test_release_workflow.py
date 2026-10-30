"""Tests for the trunk-based publish and development package workflows."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = (ROOT / ".github/workflows/publish.yaml").read_text(encoding="utf-8")
DEV_PACKAGE = (ROOT / ".github/workflows/dev-package.yaml").read_text(encoding="utf-8")
CI = (ROOT / ".github/workflows/ci.yaml").read_text(encoding="utf-8")

SPEC = importlib.util.spec_from_file_location(
    "validate_release_metadata_workflow", ROOT / "scripts/validate_release_metadata.py"
)
assert SPEC is not None and SPEC.loader is not None
METADATA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(METADATA)


def _step_script(workflow: str, name: str) -> str:
    """Return the dedented `run: |` block of the named step."""
    start = workflow.index(f"- name: {name}\n")
    block = workflow.index("run: |\n", start) + len("run: |\n")
    lines = []
    for line in workflow[block:].splitlines():
        if lines and line.strip() and not line.startswith(" " * 10):
            break
        lines.append(line)
    return textwrap.dedent("\n".join(lines)).strip() + "\n"


def _job(workflow: str, name: str) -> str:
    match = re.search(rf"(?ms)^  {name}:\n(.*?)(?=^  [a-z-]+:\n|\Z)", workflow)
    assert match is not None, name
    return match.group(1)


def _bin(tmp_path: Path, name: str, body: str) -> Path:
    directory = tmp_path / "bin"
    directory.mkdir(exist_ok=True)
    path = directory / name
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(0o755)
    return directory


def _git_env(tmp_path: Path) -> dict[str, str]:
    config = tmp_path / "gitconfig"
    config.write_text(
        "[user]\n\tname = Release Test\n\temail = release-test@example.com\n"
        "[commit]\n\tgpgsign = false\n[core]\n\thooksPath = /dev/null\n"
        "[init]\n\tdefaultBranch = main\n",
        encoding="utf-8",
    )
    return {**os.environ, "GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"}


def _git(cwd: Path, env: dict[str, str], *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_publish_runs_for_main_pushes_and_releases_only() -> None:
    assert re.search(
        r"\non:\n  push:\n    branches: \[main\]\n  release:\n    types: \[published\]\n",
        PUBLISH,
    )
    assert (
        "group: pypi-${{ github.event_name == 'push' && 'main' "
        "|| github.event.release.tag_name }}" in PUBLISH
    )
    assert not re.search(r"\bdevelop\b", PUBLISH + CI)
    assert CI.count("branches: [main]") == 2


def _origin_repo(tmp_path: Path, env: dict[str, str]) -> Path:
    """Return a checkout whose origin has v0.14.0rc1 and v0.14.0 tags."""
    remote = tmp_path / "remote.git"
    _git(tmp_path, env, "init", "--bare", str(remote))
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, env, "init")
    _git(repo, env, "commit", "--allow-empty", "-m", "Release")
    _git(repo, env, "tag", "v0.14.0rc1")
    _git(repo, env, "tag", "v0.14.0")
    _git(repo, env, "remote", "add", "origin", str(remote))
    _git(repo, env, "push", "origin", "main", "--tags")
    # A tag that exists only in the local checkout does not count.
    _git(repo, env, "tag", "v0.15.0")
    return repo


@pytest.mark.parametrize(
    ("event", "version", "expected"),
    [
        ("push", "0.14.0", "mode=development\nsmoke_prefix=LAMBDADB_DEV_\nenvironment=dev"),
        ("push", "0.14.0rc1", "mode=development\nsmoke_prefix=LAMBDADB_DEV_\nenvironment=dev"),
        ("push", "0.15.0rc1", "mode=verify\nsmoke_prefix=LAMBDADB_PROD_\nenvironment=prod"),
        ("push", "0.15.0", "mode=verify\nsmoke_prefix=LAMBDADB_PROD_\nenvironment=prod"),
        ("push", "0.14.1.dev0", None),
        ("push", "0.14.1.dev3", None),
        ("push", "0.15.0-rc.1", None),
        ("release", "0.14.0", "mode=release\nsmoke_prefix=LAMBDADB_PROD_\nenvironment=prod"),
        ("release", "0.14.0rc1", "mode=release\nsmoke_prefix=LAMBDADB_PROD_\nenvironment=prod"),
    ],
)
def test_run_mode_follows_the_committed_version_tag_on_origin(
    tmp_path: Path, event: str, version: str, expected: str | None
) -> None:
    env = _git_env(tmp_path)
    repo = _origin_repo(tmp_path, env)
    bin_dir = _bin(tmp_path, "python", 'echo "$COMMITTED_VERSION"')
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", "-e", "-c", _step_script(PUBLISH, "Select the run mode")],
        cwd=repo,
        env={
            **env,
            "PATH": f"{bin_dir}:{env['PATH']}",
            "GITHUB_OUTPUT": str(output),
            "PUBLISH_EVENT": event,
            "COMMITTED_VERSION": version,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    if expected is None:
        assert result.returncode != 0
        assert "must be an RC or stable version" in result.stderr
        assert not output.exists()
    else:
        assert result.returncode == 0, result.stderr
        assert output.read_text(encoding="utf-8").strip() == expected


def test_run_mode_fails_when_origin_cannot_be_queried(tmp_path: Path) -> None:
    env = _git_env(tmp_path)
    repo = _origin_repo(tmp_path, env)
    _git(repo, env, "remote", "set-url", "origin", str(tmp_path / "missing.git"))
    bin_dir = _bin(tmp_path, "python", "echo 0.15.0")
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", "-e", "-c", _step_script(PUBLISH, "Select the run mode")],
        cwd=repo,
        env={
            **env,
            "PATH": f"{bin_dir}:{env['PATH']}",
            "GITHUB_OUTPUT": str(output),
            "PUBLISH_EVENT": "push",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Could not query origin for tag v0.15.0" in result.stderr
    assert not output.exists()


def test_only_releases_publish_and_verification_runs_every_check() -> None:
    validate = _job(PUBLISH, "validate")
    assert "mode: ${{ steps.mode.outputs.mode }}" in validate
    assert (
        "- name: Validate committed release versions\n"
        "        if: steps.mode.outputs.mode == 'verify'\n"
        "        run: python scripts/validate_release_metadata.py --commit\n"
    ) in validate
    assert (
        "- name: Validate release tag and package versions\n"
        "        if: steps.mode.outputs.mode == 'release'\n"
    ) in validate
    assert (
        "- name: Verify release commit is on main\n"
        "        if: steps.mode.outputs.mode != 'development'\n"
    ) in validate
    for name in ("test", "build"):
        job = _job(PUBLISH, name)
        assert "if: needs.validate.outputs.mode != 'development'" in job
        assert (
            "ref: ${{ github.event_name == 'push' && github.sha "
            "|| github.event.release.tag_name }}" in job
        )
    publish = _job(PUBLISH, "pypi-publish")
    assert "needs: [validate, test, build, live-smoke]" in publish
    assert "if: needs.validate.outputs.mode == 'release'" in publish
    assert PUBLISH.count("pypa/gh-action-pypi-publish") == 1
    assert "pypa/gh-action-pypi-publish" in publish
    # Only the publishing job receives an OIDC token, for PyPI Trusted Publishing.
    assert "id-token: write" in publish
    assert "id-token" not in PUBLISH.replace(publish, "")


def test_every_mode_runs_the_live_smoke_against_its_environment() -> None:
    validate = _job(PUBLISH, "validate")
    assert "smoke_prefix: ${{ steps.mode.outputs.smoke_prefix }}" in validate
    assert "environment: ${{ steps.mode.outputs.environment }}" in validate
    smoke = _job(PUBLISH, "live-smoke")
    assert smoke.startswith(
        "    needs: validate\n"
        "    runs-on: ubuntu-latest\n"
        "    environment: ${{ needs.validate.outputs.environment }}\n"
    )
    assert "permissions:" not in smoke
    assert "\n    if:" not in smoke
    assert (
        "ref: ${{ github.event_name == 'push' && github.sha "
        "|| github.event.release.tag_name }}" in smoke
    )
    # Each value comes only from the selected environment's Variable; a missing
    # Variable stays empty and fails instead of falling back.
    for name in ("BASE_URL", "PROJECT_NAME"):
        assert (
            f"${{{{ vars[format('{{0}}{name}', needs.validate.outputs.smoke_prefix)] }}}}"
            in smoke
        )
    assert "||" not in smoke.replace("github.sha || github.event.release.tag_name", "")
    # The key comes only from the selected GitHub Environment's secret.
    assert PUBLISH.count("secrets.") == 1
    assert "LAMBDADB_PROJECT_API_KEY: ${{ secrets.LAMBDADB_PROJECT_API_KEY }}" in smoke
    assert not re.search(r"(?i)aws-actions|configure-aws-credentials|_ARN\b|secretsmanager", PUBLISH)


def test_release_commits_must_be_on_main(tmp_path: Path) -> None:
    env = _git_env(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, env, "init")
    _git(repo, env, "commit", "--allow-empty", "-m", "Base")
    older = _git(repo, env, "rev-parse", "HEAD")
    _git(repo, env, "commit", "--allow-empty", "-m", "Head")
    head = _git(repo, env, "rev-parse", "HEAD")
    _git(repo, env, "checkout", "-b", "feature")
    _git(repo, env, "commit", "--allow-empty", "-m", "Unmerged change")
    feature = _git(repo, env, "rev-parse", "HEAD")
    _git(repo, env, "remote", "add", "origin", str(repo))
    script = _step_script(PUBLISH, "Verify release commit is on main")

    for commit, status in ((head, 0), (older, 0), (feature, 1)):
        _git(repo, env, "checkout", "--detach", commit)
        result = subprocess.run(
            ["bash", "-e", "-c", script],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == status, result.stderr


def _release_tree(root: Path, version: str, *, runtime: str | None = None) -> None:
    (root / "src/lambdadb").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "lambdadb"\nversion = "{version}"\n', encoding="utf-8"
    )
    (root / "src/lambdadb/version.py").write_text(
        f'SDK_VERSION: str = "{runtime or version}"\n', encoding="utf-8"
    )
    (root / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## Unreleased\n\n## {version}\n", encoding="utf-8"
    )


@pytest.mark.parametrize("version", ["0.14.0rc1", "0.14.0"])
def test_commit_verification_accepts_committed_rc_and_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    _release_tree(tmp_path, version)
    monkeypatch.setattr(METADATA, "ROOT", tmp_path)

    assert METADATA.validate_release_commit_metadata() == version


@pytest.mark.parametrize(
    ("version", "runtime", "changelog", "message"),
    [
        ("0.14.0.dev0", None, True, "must not be published"),
        ("0.14.0-rc.1", None, True, "Project version must use canonical"),
        ("0.14.0a1", None, True, r"exactly X\.Y\.Z or X\.Y\.ZrcN"),
        ("0.14.0", "0.13.0", True, "Project and runtime versions must match"),
        ("0.14.0", None, False, "level-2 heading"),
    ],
)
def test_commit_verification_rejects_unreleasable_commits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    version: str,
    runtime: str | None,
    changelog: bool,
    message: str,
) -> None:
    _release_tree(tmp_path, version, runtime=runtime)
    if not changelog:
        (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    monkeypatch.setattr(METADATA, "ROOT", tmp_path)

    with pytest.raises(ValueError, match=message):
        METADATA.validate_release_commit_metadata()


def test_dev_package_builds_the_derived_development_version(tmp_path: Path) -> None:
    pytest.importorskip("tomllib")
    assert "fetch-depth: 0" in DEV_PACKAGE
    assert DEV_PACKAGE.index("Run non-integration tests") < DEV_PACKAGE.index(
        "Set development version"
    ) < DEV_PACKAGE.index("Build distributions")
    assert (
        "name: lambdadb-${{ steps.package.outputs.version }}-"
        "${{ steps.package.outputs.sha }}" in DEV_PACKAGE
    )
    env = _git_env(tmp_path)
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    for script in ("version.py", "validate_release_metadata.py"):
        shutil.copy(ROOT / "scripts" / script, repo / "scripts" / script)
    _release_tree(repo, "0.14.0")
    _git(repo, env, "init")
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-m", "Release 0.14.0")
    _git(repo, env, "tag", "v0.14.0")
    _git(repo, env, "commit", "--allow-empty", "-m", "Change 1")
    _git(repo, env, "commit", "--allow-empty", "-m", "Change 2")
    # The step runs `python` from the environment that runs these tests.
    python_dir = Path(sys.executable).parent
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", "-e", "-c", _step_script(DEV_PACKAGE, "Set development version")],
        cwd=repo,
        env={**env, "PATH": f"{python_dir}:{env['PATH']}", "GITHUB_OUTPUT": str(output)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    sha = _git(repo, env, "rev-parse", "--short=12", "HEAD")
    assert output.read_text(encoding="utf-8") == f"version=0.14.1.dev2\nsha={sha}\n"
    assert 'SDK_VERSION: str = "0.14.1.dev2"' in (
        repo / "src/lambdadb/version.py"
    ).read_text(encoding="utf-8")
