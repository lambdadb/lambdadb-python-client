"""Run every deployed LambdaDB live test as a release gate.

The publish workflow runs this script in the GitHub Environment that holds the
dedicated smoke project API key. The key arrives in ``LAMBDADB_PROJECT_API_KEY``,
which Actions masks in logs, and is passed only in the pytest child process
environment, never in command arguments or files.

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
    "LAMBDADB_PROJECT_API_KEY",
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


def run_live_smoke(
    env: Mapping[str, str],
    spawn: Callable[..., Any] = subprocess.run,
) -> None:
    for name in REQUIRED_CONFIGURATION:
        if not env.get(name, "").strip():
            raise SmokeError(f"Missing smoke configuration: {name}")
    key = env["LAMBDADB_PROJECT_API_KEY"].strip()
    if "\r" in key or "\n" in key:
        raise SmokeError("Expected a single project API key")
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
