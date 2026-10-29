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
    "LAMBDADB_SMOKE_SECRET_ARN": (
        "arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:smoke-key"
    ),
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


def _secret(value: str) -> Any:
    return lambda *_args, **_kwargs: SimpleNamespace(stdout=value)


@pytest.mark.parametrize("actions", [True, False])
def test_key_is_read_through_aws_masked_and_passed_only_to_the_child(actions: bool) -> None:
    env = {**ENV, **({"GITHUB_ACTIONS": "true"} if actions else {})}
    calls: list[str] = []

    def execute(args: list[str], **options: Any) -> Any:
        calls.append("aws")
        assert args == [
            "aws", "secretsmanager", "get-secret-value", "--region", "ap-northeast-2",
            "--secret-id", ENV["LAMBDADB_SMOKE_SECRET_ARN"],
            "--query", "SecretString", "--output", "text",
        ]
        assert options["capture_output"] and options["check"]
        return SimpleNamespace(stdout="synthetic%test-key\n")

    def spawn(args: list[str], **options: Any) -> Any:
        calls.append("pytest")
        assert args[:3] == [sys.executable, "-m", "pytest"]
        assert args[3:7] == LIVE_FILES
        assert args[7:9] == ["-p", "scripts.run_live_smoke"]
        assert not any("synthetic" in arg for arg in args)
        assert options["cwd"] == ROOT
        child = options["env"]
        assert child["LAMBDADB_PROJECT_API_KEY"] == "synthetic%test-key"
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

    def mask(line: str) -> None:
        calls.append("mask")
        assert line == "::add-mask::synthetic%25test-key"

    SMOKE.run_live_smoke(env, execute, spawn, mask)

    assert calls == (["aws", "mask", "pytest"] if actions else ["aws", "pytest"])
    assert "LAMBDADB_PROJECT_API_KEY" not in env


def test_every_live_suite_flag_is_enabled() -> None:
    flags = {
        flag
        for path in SMOKE.LIVE_TESTS
        for flag in re.findall(r"LAMBDADB_RUN_[A-Z_]+", (ROOT / path).read_text(encoding="utf-8"))
    }
    assert flags == set(SMOKE.SUITE_FLAGS)


@pytest.mark.parametrize("name", SMOKE.REQUIRED_CONFIGURATION)
def test_missing_configuration_fails_before_reading_the_key(name: str) -> None:
    for value in ("", "  "):
        with pytest.raises(SMOKE.SmokeError, match=f"Missing smoke configuration: {name}"):
            SMOKE.run_live_smoke({**ENV, name: value}, _unexpected, _unexpected, _unexpected)


@pytest.mark.parametrize(
    "error",
    [subprocess.CalledProcessError(255, ["aws"], "sensitive", "sensitive"), OSError("sensitive")],
)
def test_secret_read_failures_hide_aws_output(error: Exception) -> None:
    def execute(*_args: Any, **_kwargs: Any) -> Any:
        raise error

    with pytest.raises(SMOKE.SmokeError) as raised:
        SMOKE.run_live_smoke(ENV, execute, _unexpected, _unexpected)
    assert str(raised.value) == (
        "Unable to read the dedicated smoke project key from Secrets Manager"
    )
    assert raised.value.__cause__ is None and raised.value.__suppress_context__


@pytest.mark.parametrize("value", ["", "\n", "None", "key\nother-key", "key\rother"])
def test_invalid_keys_fail_before_starting_the_smoke(value: str) -> None:
    with pytest.raises(SMOKE.SmokeError, match="single project API key"):
        SMOKE.run_live_smoke(ENV, _secret(value), _unexpected, _unexpected)


@pytest.mark.parametrize("returncode", [1, 2, 5, -15])
def test_failed_smoke_blocks_publication(returncode: int) -> None:
    def spawn(*_args: Any, **_kwargs: Any) -> Any:
        return SimpleNamespace(returncode=returncode)

    with pytest.raises(SMOKE.SmokeError, match="Deployed live smoke failed"):
        SMOKE.run_live_smoke(ENV, _secret("key"), spawn, lambda _line: None)


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


def test_mask_is_flushed_before_the_child_starts(tmp_path: Path) -> None:
    script = (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('smoke', {str(ROOT / 'scripts/run_live_smoke.py')!r})\n"
        "smoke = importlib.util.module_from_spec(spec); spec.loader.exec_module(smoke)\n"
        "class R: stdout = 'key'; returncode = 0\n"
        "def spawn(*a, **k):\n"
        "    import os; os.write(1, b'child output\\n'); return R\n"
        "smoke.run_live_smoke(" + repr({**ENV, "GITHUB_ACTIONS": "true"}) + ", lambda *a, **k: R, spawn)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert result.stdout == "::add-mask::key\nchild output\n"
