"""Run every deployed LambdaDB live test as a release gate.

The publish workflow runs this script after assuming the smoke OIDC role. It
reads the dedicated project API key from AWS Secrets Manager, masks it in GitHub
Actions, and passes it only in the pytest child process environment, never in
command arguments or files.

The pytest child also loads this module as a plugin (``-p
scripts.run_live_smoke``) so that a skipped live test fails the gate instead of
counting as a pass.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CONFIGURATION = (
    "LAMBDADB_BASE_URL",
    "LAMBDADB_PROJECT_NAME",
    "LAMBDADB_SMOKE_SECRET_ARN",
)
# Every live suite's opt-in flag. A suite whose flag is missing here skips,
# which fails the gate.
SUITE_FLAGS = {
    "LAMBDADB_RUN_LIVE_TESTS": "1",
    "LAMBDADB_RUN_VERSIONING_SMOKE": "1",
    "LAMBDADB_RUN_QUERY_SCORE_SMOKE": "1",
    "LAMBDADB_RUN_BAYESIAN_SMOKE": "1",
}
LIVE_TESTS = tuple(
    sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "tests/integration").glob("test_*_live.py")
    )
)
# Tests run one at a time (pytest's default); the project rate limit is sized
# for a sequential run.
PYTEST_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    *LIVE_TESTS,
    "-p",
    "scripts.run_live_smoke",
    "-v",
    "--tb=short",
)


class SmokeError(RuntimeError):
    """A live smoke failure that must block publication."""


def _emit(line: str) -> None:
    # Flush so the mask is registered before the child writes any output.
    print(line, flush=True)


def run_live_smoke(
    env: Mapping[str, str],
    execute: Callable[..., Any] = subprocess.run,
    spawn: Callable[..., Any] = subprocess.run,
    mask: Callable[[str], None] = _emit,
) -> None:
    for name in REQUIRED_CONFIGURATION:
        if not env.get(name, "").strip():
            raise SmokeError(f"Missing smoke configuration: {name}")
    try:
        result = execute(
            [
                "aws", "secretsmanager", "get-secret-value",
                "--region", "ap-northeast-2",
                "--secret-id", env["LAMBDADB_SMOKE_SECRET_ARN"],
                "--query", "SecretString", "--output", "text",
            ],
            env=dict(env),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        # Do not include AWS command output or credentials in errors.
        raise SmokeError(
            "Unable to read the dedicated smoke project key from Secrets Manager"
        ) from None
    key = result.stdout.strip()
    if not key or key == "None" or "\r" in key or "\n" in key:
        raise SmokeError("Expected a single project API key in SecretString")
    # A workflow command only works in GitHub Actions; elsewhere it would print the key.
    if env.get("GITHUB_ACTIONS") == "true":
        mask("::add-mask::" + key.replace("%", "%25"))
    result = spawn(
        list(PYTEST_COMMAND),
        cwd=ROOT,
        env={**env, **SUITE_FLAGS, "LAMBDADB_PROJECT_API_KEY": key},
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        raise SmokeError("Deployed live smoke failed")


# pytest plugin hooks, active only in the smoke child process. pytest itself
# fails a run that collects no tests.
_SKIPPED: list[str] = []


def pytest_collectreport(report: Any) -> None:
    if report.skipped:
        _SKIPPED.append(report.nodeid)


def pytest_runtest_logreport(report: Any) -> None:
    if report.skipped:
        _SKIPPED.append(report.nodeid)


def pytest_sessionfinish(session: Any) -> None:
    if _SKIPPED and session.exitstatus == 0:
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter: Any) -> None:
    for nodeid in _SKIPPED:
        terminalreporter.write_line(f"Live smoke must not skip: {nodeid}", red=True)


def main() -> int:
    try:
        run_live_smoke(os.environ)
    except SmokeError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
