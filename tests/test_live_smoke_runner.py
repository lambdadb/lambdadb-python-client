"""Tests for the deployed live smoke runner used by the publish workflow."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_live_smoke_under_test", ROOT / "scripts/run_live_smoke.py"
)
assert SPEC is not None and SPEC.loader is not None
SMOKE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SMOKE)

ENV = {
    "LAMBDADB_BASE_URL": "https://test.example",
    "LAMBDADB_PROJECT_NAME": "sdk-smoke",
    "LAMBDADB_PROJECT_API_KEY": "synthetic-test-key",
    "LAMBDADB_RUN_BAYESIAN_SMOKE": "0",
    "PATH": "/bin",
}
LIVE_FILES = [
    "tests/integration/test_bayesian_native_live.py",
    "tests/integration/test_data_versioning_live.py",
    "tests/integration/test_qdrant_compat_live.py",
    "tests/integration/test_query_scores_live.py",
]


def _unexpected(*_args: Any, **_kwargs: Any) -> Any:
    pytest.fail("must not start the smoke")


def test_the_live_suite_runs_with_the_configured_key_in_the_child_environment() -> None:
    env = {**ENV, "LAMBDADB_PROJECT_API_KEY": " synthetic-test-key\n"}
    calls: list[list[str]] = []

    def spawn(args: list[str], **options: Any) -> Any:
        calls.append(args)
        assert args[:3] == [sys.executable, "-m", "pytest"]
        assert args[3:7] == LIVE_FILES
        assert args[7:9] == ["-p", "scripts.run_live_smoke"]
        assert not any("synthetic" in arg for arg in args)
        assert options["cwd"] == ROOT
        child = options["env"]
        assert child["LAMBDADB_PROJECT_API_KEY"] == "synthetic-test-key"
        assert child["LAMBDADB_BASE_URL"] == ENV["LAMBDADB_BASE_URL"]
        # Every suite is enabled, even when the caller disabled one.
        for flag in (
            "LAMBDADB_RUN_LIVE_TESTS",
            "LAMBDADB_RUN_VERSIONING_SMOKE",
            "LAMBDADB_RUN_QUERY_SCORE_SMOKE",
            "LAMBDADB_RUN_BAYESIAN_SMOKE",
        ):
            assert child[flag] == "1"
        return SimpleNamespace(returncode=0)

    SMOKE.run_live_smoke(env, spawn)

    assert len(calls) == 1
    # The caller's environment is not modified.
    assert env == {**ENV, "LAMBDADB_PROJECT_API_KEY": " synthetic-test-key\n"}


def test_every_live_suite_flag_is_enabled() -> None:
    flags = {
        flag
        for path in SMOKE.LIVE_TESTS
        for flag in re.findall(r"LAMBDADB_RUN_[A-Z_]+", (ROOT / path).read_text(encoding="utf-8"))
    }
    assert flags == set(SMOKE.SUITE_FLAGS)


@pytest.mark.parametrize("name", SMOKE.REQUIRED_CONFIGURATION)
def test_missing_configuration_fails_before_starting_the_smoke(name: str) -> None:
    missing = {key: value for key, value in ENV.items() if key != name}
    for env in (missing, {**ENV, name: ""}, {**ENV, name: "  "}):
        with pytest.raises(SMOKE.SmokeError, match=f"Missing smoke configuration: {name}"):
            SMOKE.run_live_smoke(env, _unexpected)


@pytest.mark.parametrize("value", ["key\nother-key", "key\rother"])
def test_multi_line_keys_fail_before_starting_the_smoke(value: str) -> None:
    with pytest.raises(SMOKE.SmokeError, match="single project API key"):
        SMOKE.run_live_smoke({**ENV, "LAMBDADB_PROJECT_API_KEY": value}, _unexpected)


@pytest.mark.parametrize("returncode", [1, 2, 5, -15])
def test_failed_smoke_blocks_publication(returncode: int) -> None:
    def spawn(*_args: Any, **_kwargs: Any) -> Any:
        return SimpleNamespace(returncode=returncode)

    with pytest.raises(SMOKE.SmokeError, match="Deployed live smoke failed"):
        SMOKE.run_live_smoke(ENV, spawn)


def _run_plugin(tmp_path: Path, source: str) -> subprocess.CompletedProcess[str]:
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(source, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-p", "scripts.run_live_smoke",
         "-p", "no:cacheprovider", "--rootdir", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("source", "status", "message"),
    [
        ("def test_pass():\n    pass\n", 0, None),
        (
            "import pytest\n\ndef test_pass():\n    pass\n\n"
            "def test_skip():\n    pytest.skip('flag unset')\n",
            1,
            "Live smoke must not skip: test_sample.py::test_skip",
        ),
        (
            "import pytest\n\n@pytest.fixture\ndef live():\n    pytest.skip('flag unset')\n\n"
            "def test_live(live):\n    pass\n",
            1,
            "Live smoke must not skip: test_sample.py::test_live",
        ),
        (
            "import pytest\npytest.skip('flag unset', allow_module_level=True)\n",
            5,
            "Live smoke must not skip: test_sample.py",
        ),
        ("def test_fail():\n    assert False\n", 1, None),
        ("", 5, None),
    ],
)
def test_plugin_fails_skipped_or_empty_runs(
    tmp_path: Path, source: str, status: int, message: str | None
) -> None:
    result = _run_plugin(tmp_path, source)
    assert result.returncode == status, result.stdout + result.stderr
    if message:
        assert message in result.stdout
