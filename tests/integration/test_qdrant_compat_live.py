"""
Opt-in live smoke test for the Qdrant compatibility client.

Run:
    LAMBDADB_RUN_LIVE_TESTS=1 poetry run pytest tests/integration/test_qdrant_compat_live.py -v

Required environment, either exported or placed in .env / .env.local:
    LAMBDADB_RUN_LIVE_TESTS=1
    LAMBDADB_PROJECT_API_KEY=...
    LAMBDADB_PROJECT_NAME=...
    LAMBDADB_BASE_URL=https://api.lambdadb.ai
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _load_local_env() -> None:
    root = Path(__file__).resolve().parents[2]
    _load_env_file(root / ".env")
    _load_env_file(root / ".env.local")


def _live_config() -> tuple[str, str, str]:
    _load_local_env()
    run_live_tests = os.getenv("LAMBDADB_RUN_LIVE_TESTS", "").lower()
    if run_live_tests not in {"1", "true", "yes"}:
        pytest.skip("Set LAMBDADB_RUN_LIVE_TESTS=1 to run live LambdaDB tests")

    api_key = os.getenv("LAMBDADB_PROJECT_API_KEY")
    project_name = os.getenv("LAMBDADB_PROJECT_NAME")
    base_url = os.getenv("LAMBDADB_BASE_URL", "https://api.lambdadb.ai")
    missing = [
        name
        for name, value in [
            ("LAMBDADB_PROJECT_API_KEY", api_key),
            ("LAMBDADB_PROJECT_NAME", project_name),
        ]
        if not value
    ]
    if missing:
        pytest.skip(f"Live LambdaDB config missing: {', '.join(missing)}")
    assert api_key is not None
    assert project_name is not None
    return api_key, project_name, base_url


@pytest.mark.integration
def test_qdrant_compat_live_smoke() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models
    from lambdadb.utils.retries import BackoffStrategy, RetryConfig

    api_key, project_name, base_url = _live_config()
    collection_name = f"qdrant_compat_smoke_{int(time.time() * 1000)}"
    client = QdrantCompatClient(
        project_api_key=api_key,
        project_name=project_name,
        base_url=base_url,
        timeout_ms=30000,
        retry_config=RetryConfig(
            "backoff",
            BackoffStrategy(0, 0, 1, 1000),
            False,
        ),
    )

    try:
        assert not client.collection_exists(collection_name)
        assert client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=3,
                distance=models.Distance.COSINE,
            ),
            payload_schema={"tenant": models.PayloadSchemaType.KEYWORD},
        )
        assert client.collection_exists(collection_name)

        upsert_result = client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=1,
                    vector=[1.0, 0.0, 0.0],
                    payload={"tenant": "acme", "title": "alpha"},
                ),
                models.PointStruct(
                    id=2,
                    vector=[0.0, 1.0, 0.0],
                    payload={"tenant": "acme", "title": "beta"},
                ),
                models.PointStruct(
                    id=3,
                    vector=[0.0, 0.0, 1.0],
                    payload={"tenant": "other", "title": "gamma"},
                ),
            ],
        )
        assert upsert_result.status == models.UpdateStatus.COMPLETED

        fetched = client.retrieve(collection_name=collection_name, ids=[1], with_vectors=True)
        assert fetched
        assert fetched[0].id in {1, "1"}
        assert fetched[0].payload is not None
        assert fetched[0].payload["tenant"] == "acme"

        queried = client.query_points(
            collection_name=collection_name,
            query=[1.0, 0.0, 0.0],
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="tenant",
                        match=models.MatchValue(value="acme"),
                    )
                ]
            ),
            limit=2,
            with_payload=True,
        )
        assert queried.points
        assert queried.points[0].payload is not None
        assert queried.points[0].payload["tenant"] == "acme"

        delete_result = client.delete(collection_name=collection_name, points_selector=[1])
        assert delete_result.status == models.UpdateStatus.COMPLETED
    finally:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
