"""Tests for the trunk-based publish and next-development-version workflows."""

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
NEXT_DEV = (ROOT / ".github/workflows/next-dev-version.yaml").read_text(encoding="utf-8")
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


@pytest.mark.parametrize(
    ("event", "version", "expected"),
    [
        ("push", "0.13.1.dev0", "mode=development\nsmoke_prefix=LAMBDADB_DEV_"),
        ("push", "0.14.0rc1", "mode=verify\nsmoke_prefix=LAMBDADB_PROD_"),
        ("push", "0.14.0", "mode=verify\nsmoke_prefix=LAMBDADB_PROD_"),
        ("push", "0.14.0.dev3", None),
        ("release", "0.14.0", "mode=release\nsmoke_prefix=LAMBDADB_PROD_"),
        ("release", "0.14.0rc1", "mode=release\nsmoke_prefix=LAMBDADB_PROD_"),
    ],
)
def test_run_mode_follows_the_committed_version(
    tmp_path: Path, event: str, version: str, expected: str | None
) -> None:
    bin_dir = _bin(tmp_path, "python", 'echo "$COMMITTED_VERSION"')
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", "-e", "-c", _step_script(PUBLISH, "Select the run mode")],
        env={
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
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
        assert ".dev0 placeholder" in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert output.read_text(encoding="utf-8").strip() == expected


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
    assert "id-token: write" in publish
    smoke = _job(PUBLISH, "live-smoke")
    assert "id-token: write" in smoke
    assert "id-token" not in PUBLISH.replace(publish, "").replace(smoke, "")


def test_every_mode_runs_the_live_smoke_against_its_environment() -> None:
    assert "smoke_prefix: ${{ steps.mode.outputs.smoke_prefix }}" in _job(PUBLISH, "validate")
    smoke = _job(PUBLISH, "live-smoke")
    assert "needs: validate\n" in smoke
    assert "\n    if:" not in smoke
    assert (
        "ref: ${{ github.event_name == 'push' && github.sha "
        "|| github.event.release.tag_name }}" in smoke
    )
    # Each value comes only from the selected environment's Variable; a missing
    # Variable stays empty and fails instead of falling back.
    for name in ("SMOKE_AWS_ROLE_ARN", "BASE_URL", "PROJECT_NAME", "SMOKE_SECRET_ARN"):
        assert (
            f"${{{{ vars[format('{{0}}{name}', needs.validate.outputs.smoke_prefix)] }}}}"
            in smoke
        )
    assert "||" not in smoke.replace("github.sha || github.event.release.tag_name", "")
    assert "secrets." not in PUBLISH
    assert smoke.index("Authenticate smoke tests to AWS") < smoke.index(
        "python scripts/run_live_smoke.py"
    )


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


def test_next_dev_workflow_runs_only_after_a_successful_release() -> None:
    assert re.search(
        r'workflow_run:\n\s+workflows: \["Publish to PyPI"\]\n\s+types: \[completed\]',
        NEXT_DEV,
    )
    assert re.search(r"(?m)^name: Publish to PyPI$", PUBLISH)
    assert (
        "if: github.event.workflow_run.conclusion == 'success' "
        "&& github.event.workflow_run.event == 'release'" in NEXT_DEV
    )
    assert "ref: main" in NEXT_DEV


def _next_dev_repo(tmp_path: Path, version: str) -> tuple[Path, Path, dict[str, str]]:
    env = _git_env(tmp_path)
    remote = tmp_path / "remote.git"
    _git(tmp_path, env, "init", "--bare", str(remote))
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy(ROOT / "scripts/version.py", repo / "scripts/version.py")
    _release_tree(repo, version)
    _git(repo, env, "init")
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-m", f"Release {version}")
    _git(repo, env, "remote", "add", "origin", str(remote))
    _git(repo, env, "push", "origin", "main")
    bin_dir = _bin(
        tmp_path,
        "gh",
        'if [ "$1 $2" = "pr list" ]; then printf "%s" "$OPEN_PR"; exit 0; fi\n'
        '[ -z "$GH_CREATE_FAILS" ] || exit 1\n'
        'printf "%s\\n" "$@" > "$GH_CALL_LOG"',
    )
    (bin_dir / "python").symlink_to(sys.executable)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["GH_CALL_LOG"] = str(tmp_path / "gh-call")
    return repo, remote, env


@pytest.mark.parametrize(
    ("tag", "next_version"),
    [("v0.14.0rc1", "0.14.0.dev0"), ("v0.14.0", "0.14.1.dev0")],
)
def test_next_dev_workflow_opens_the_placeholder_pull_request(
    tmp_path: Path, tag: str, next_version: str
) -> None:
    repo, remote, env = _next_dev_repo(tmp_path, tag[1:])
    script = _step_script(NEXT_DEV, "Open the next development version pull request")
    branch = f"chore/next-dev-{next_version}"
    gh_log = tmp_path / "gh-call"

    def run(**extra: str) -> subprocess.CompletedProcess[str]:
        # Each workflow run starts from a fresh checkout of main.
        _git(repo, env, "checkout", "-f", "main")
        subprocess.run(
            ["git", "branch", "-D", branch], cwd=repo, env=env, capture_output=True, check=False
        )
        gh_log.unlink(missing_ok=True)
        return subprocess.run(
            ["bash", "-e", "-c", script],
            cwd=repo,
            env={**env, "RELEASE_TAG": tag, **extra},
            capture_output=True,
            text=True,
            check=False,
        )

    def pushed() -> tuple[str, str]:
        return (
            _git(remote, env, "rev-parse", f"{branch}^"),
            _git(remote, env, "show", f"{branch}:src/lambdadb/version.py"),
        )

    main = _git(repo, env, "rev-parse", "main")
    expected = (main, f'SDK_VERSION: str = "{next_version}"')

    # The branch is pushed, but opening the pull request fails.
    assert run(GH_CREATE_FAILS="1").returncode != 0
    assert pushed() == expected and not gh_log.exists()

    # A rerun without an open pull request refreshes the branch and opens one.
    result = run()
    assert result.returncode == 0, result.stderr
    assert pushed() == expected
    gh_call = gh_log.read_text(encoding="utf-8").splitlines()
    assert gh_call[:6] == ["pr", "create", "--base", "main", "--head", branch]

    # An open pull request built on the current main is left alone.
    head = _git(remote, env, "rev-parse", branch)
    result = run(OPEN_PR="https://example.test/pull/1")
    assert result.returncode == 0, result.stderr
    assert "already proposes" in result.stdout
    assert _git(remote, env, "rev-parse", branch) == head and not gh_log.exists()

    # An open pull request behind main is refreshed in place.
    _git(repo, env, "commit", "--allow-empty", "-m", "Later change on main")
    _git(repo, env, "push", "origin", "main")
    main = _git(repo, env, "rev-parse", "main")
    result = run(OPEN_PR="https://example.test/pull/1")
    assert result.returncode == 0, result.stderr
    assert "Refreshed" in result.stdout
    assert pushed() == (main, expected[1]) and not gh_log.exists()


@pytest.mark.parametrize("delete_branch", [True, False])
def test_next_dev_workflow_opens_a_new_pull_request_after_each_rc(
    tmp_path: Path, delete_branch: bool
) -> None:
    repo, remote, env = _next_dev_repo(tmp_path, "0.14.0rc1")
    script = _step_script(NEXT_DEV, "Open the next development version pull request")
    branch = "chore/next-dev-0.14.0.dev0"
    gh_log = tmp_path / "gh-call"

    def run(tag: str) -> list[str]:
        gh_log.unlink(missing_ok=True)
        result = subprocess.run(
            ["bash", "-e", "-c", script],
            cwd=repo,
            env={**env, "RELEASE_TAG": tag},
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return gh_log.read_text(encoding="utf-8").splitlines()[:6]

    assert run("v0.14.0rc1") == ["pr", "create", "--base", "main", "--head", branch]

    # The rc1 pull request merges (its branch deleted or kept), then rc2 releases.
    _git(repo, env, "checkout", "main")
    _git(repo, env, "merge", "--no-ff", "-m", "Merge next development version", branch)
    _git(repo, env, "branch", "-D", branch)
    set_rc2 = [sys.executable, "scripts/version.py", "set", "0.14.0rc2"]
    subprocess.run(set_rc2, cwd=repo, env=env, check=True, capture_output=True)
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n## 0.14.0rc2\n", encoding="utf-8")
    _git(repo, env, "commit", "-am", "Release 0.14.0rc2")
    _git(repo, env, "push", "origin", "main")
    if delete_branch:
        _git(repo, env, "push", "origin", "--delete", branch)
    main = _git(repo, env, "rev-parse", "main")

    # No pull request is open, so rc2 opens a new one from the current main.
    assert run("v0.14.0rc2") == ["pr", "create", "--base", "main", "--head", branch]
    assert _git(remote, env, "rev-parse", f"{branch}^") == main
    assert (
        _git(remote, env, "show", f"{branch}:src/lambdadb/version.py")
        == 'SDK_VERSION: str = "0.14.0.dev0"'
    )


@pytest.mark.parametrize(
    ("tag", "status", "message"),
    [
        ("v0.13.0", 0, "nothing to do"),
        ("v0.14.0.dev1", 1, "Unexpected release tag"),
        ("v0.14.0-rc.1", 1, "Unexpected release tag"),
    ],
)
def test_next_dev_workflow_ignores_other_versions(
    tmp_path: Path, tag: str, status: int, message: str
) -> None:
    repo, remote, env = _next_dev_repo(tmp_path, "0.14.0")
    result = subprocess.run(
        ["bash", "-e", "-c", _step_script(NEXT_DEV, "Open the next development version pull request")],
        cwd=repo,
        env={**env, "RELEASE_TAG": tag},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == status
    assert message in result.stdout + result.stderr
    assert _git(remote, env, "for-each-ref", "--format=%(refname)", "refs/heads") == "refs/heads/main"
    assert not (tmp_path / "gh-call").exists()
