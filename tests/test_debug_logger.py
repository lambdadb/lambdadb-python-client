"""LAMBDADB_DEBUG parsing for the default debug logger (no network)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Each case runs in a fresh interpreter because the enabled logger calls
# logging.basicConfig, which changes process-wide logging state.
SCRIPT = """
import httpx
from lambdadb import LambdaDB

transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"collections": []}))
with httpx.Client(transport=transport) as http_client:
    LambdaDB(project_api_key="debug-env-test-key", client=http_client).collections.list()
"""


def _request_logged(value: Optional[str]) -> bool:
    env = {key: item for key, item in os.environ.items() if key != "LAMBDADB_DEBUG"}
    if value is not None:
        env["LAMBDADB_DEBUG"] = value
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    logged = "Request:" in result.stderr
    assert logged == ("debug-env-test-key" in result.stderr)
    return logged


def test_lambdadb_debug_enables_default_logger_only_for_true_or_one() -> None:
    for value in (None, "", "false", "FALSE", "0", "no", "off"):
        assert _request_logged(value) is False, f"LAMBDADB_DEBUG={value!r}"
    for value in ("true", "TRUE", " true ", "1"):
        assert _request_logged(value) is True, f"LAMBDADB_DEBUG={value!r}"
