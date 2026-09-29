"""Query score contract checks, including an opt-in live response matrix.

The SDK's float coercion accepts the string "NaN". Check the wire response
independently of parsing, including the document array downloaded via docsUrl.
"""

import asyncio
import json
import math
import os
import time
import uuid
from urllib.parse import urlsplit

import httpx
import pytest

from lambdadb import LambdaDB, errors, models


def _score_errors(path, value):
    if value is None:
        return []
    if type(value) not in (int, float) or not math.isfinite(value):
        return [f"{path}: expected a finite number or absent/null, got {value!r}"]
    return []


def _wire_scores(payload):
    """Extract only score metadata; never retain document bodies or signed URLs."""
    scores = {}
    if isinstance(payload, dict):
        if "maxScore" in payload:
            scores["wire.maxScore"] = payload["maxScore"]
        docs = payload["docs"]
        prefix = "wire.docs"
    else:
        docs = payload
        prefix = "wire.docsUrl"
    for i, doc in enumerate(docs):
        if "score" in doc:
            scores[f"{prefix}[{i}].score"] = doc["score"]
    return scores


def _contract_errors(wire_scores, result):
    scores = {
        **wire_scores,
        "parsed.max_score": result.max_score,
        **{f"parsed.results[{i}].score": doc.score
           for i, doc in enumerate(result.results)},
    }
    return [error for path, value in scores.items()
            for error in _score_errors(path, value)]


class _ScoreCapture:
    def __init__(self):
        self.scores = {}
        self.query_responses = 0
        self.download_responses = 0

    def _capture(self, response):
        request = response.request
        if response.status_code != 200:
            return
        if request.method == "POST" and request.url.path.endswith("/query"):
            self.query_responses += 1
        elif request.method == "GET":
            # These clients are used exclusively for query and its docsUrl GET.
            self.download_responses += 1
        else:
            return
        self.scores.update(_wire_scores(response.json()))

    def sync_hook(self, response):
        response.read()
        self._capture(response)

    async def async_hook(self, response):
        await response.aread()
        self._capture(response)


@pytest.mark.parametrize("value", [None, 0, 1, -1.5, 2.5])
def test_score_contract_accepts_finite_or_missing_values(value):
    assert _score_errors("score", value) == []


@pytest.mark.parametrize("value", ["NaN", "1.0", True, float("nan"),
                                  float("inf"), float("-inf")])
def test_score_contract_rejects_invalid_values(value):
    assert _score_errors("score", value)


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("download", [False, True])
def test_nan_is_detected_even_when_sdk_parsing_succeeds(async_mode, download):
    capture = _ScoreCapture()

    def handler(request):
        docs = [{"collection": "items", "doc": {"id": "1"}, "score": "NaN"}]
        if request.method == "GET":
            return httpx.Response(200, json=docs)
        assert "query" not in json.loads(request.content)
        return httpx.Response(200, json={
            "took": 1, "total": 1, "maxScore": "NaN",
            "docs": [] if download else docs, "isDocsInline": not download,
            "docsUrl": "https://files.example/docs" if download else None,
        })

    config = dict(base_url="https://api.example", project_name="test",
                  project_api_key="test-key")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler),
                event_hooks={"response": [capture.async_hook]}) as transport:
            async with LambdaDB(**config, async_client=transport) as sdk:
                return await sdk.collection("items").query_async(size=1, retries=None)

    if async_mode:
        result = asyncio.run(run())
    else:
        with httpx.Client(transport=httpx.MockTransport(handler),
                event_hooks={"response": [capture.sync_hook]}) as transport:
            with LambdaDB(**config, client=transport) as sdk:
                result = sdk.collection("items").query(size=1, retries=None)
    violations = _contract_errors(capture.scores, result)
    assert len(violations) == 4  # Both fields, before and after SDK parsing.
    assert capture.query_responses == 1
    assert capture.download_responses == int(download)
    assert capture.scores["wire.maxScore"] == "NaN"
    doc_path = "wire.docsUrl[0].score" if download else "wire.docs[0].score"
    assert capture.scores[doc_path] == "NaN"
    assert math.isnan(result.max_score) and math.isnan(result.results[0].score)


def _live_config():
    names = ("LAMBDADB_BASE_URL", "LAMBDADB_PROJECT_NAME", "LAMBDADB_PROJECT_API_KEY")
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        pytest.fail("missing live configuration: " + ", ".join(missing))
    url = os.environ[names[0]]
    assert urlsplit(url).scheme in {"http", "https"} and urlsplit(url).netloc
    return dict(base_url=url, project_name=os.environ[names[1]],
                project_api_key=os.environ[names[2]], timeout_ms=30000,
                retry_config=None)


@pytest.fixture(scope="module")
def live_collection():
    if os.getenv("LAMBDADB_RUN_QUERY_SCORE_SMOKE") != "1":
        pytest.skip("set LAMBDADB_RUN_QUERY_SCORE_SMOKE=1 to run")
    config = _live_config()
    name = "python-score-smoke-" + uuid.uuid4().hex[:10]
    with LambdaDB(**config) as sdk:
        try:
            sdk.collections.create(collection_name=name,
                index_configs={"tags": models.IndexConfigs(type=models.Type.KEYWORD)},
                description="Temporary query score contract smoke", retries=None)
            print(f"created temporary collection: {name}")
            collection = sdk.collection(name)
            for i in range(6):
                collection.docs.upsert(docs=[{
                    "id": str(i), "tags": ["match"], "payload": "x" * 1100000,
                }], retries=None)
            deadline = time.monotonic() + 180
            while True:
                response = collection.query(query={"queryString": {"query": "tags:match"}},
                    size=6, fields={"exclude": ["payload"]}, retries=None)
                if response.total == 6:
                    break
                if time.monotonic() >= deadline:
                    pytest.fail("timed out waiting for committed documents")
                time.sleep(2)
            # Keep credentials out of fixture argument reprs in pytest failures.
            yield name
        finally:
            try:
                sdk.collections.delete(collection_name=name, retries=None)
            except errors.ResourceNotFoundError:
                pass
            deadline = time.monotonic() + 180
            while True:
                try:
                    sdk.collections.get(collection_name=name, retries=None)
                except errors.ResourceNotFoundError:
                    print(f"cleanup verified absent (HTTP 404): {name}")
                    break
                if time.monotonic() >= deadline:
                    pytest.fail(f"cleanup not confirmed for collection {name}")
                time.sleep(2)


@pytest.mark.integration
@pytest.mark.parametrize("query_kind", ["omitted", "empty", "query_string"])
@pytest.mark.parametrize("with_facets", [False, True])
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("response_kind", ["inline", "docs_url", "facet_only"])
def test_live_query_score_contract(live_collection, query_kind, with_facets,
                                  async_mode, response_kind, record_property):
    if response_kind == "facet_only" and not with_facets:
        pytest.skip("size=0 requires facets; not a valid score-contract request")
    config, name = _live_config(), live_collection
    args = dict(size=0 if response_kind == "facet_only" else 6, retries=None)
    if query_kind == "empty":
        args["query"] = {}
    elif query_kind == "query_string":
        args["query"] = {"queryString": {"query": "tags:match"}}
    if with_facets:
        args["facets"] = {"tags": {}}
    if response_kind == "inline":
        args["fields"] = {"exclude": ["payload"]}
    capture = _ScoreCapture()

    async def run():
        async with httpx.AsyncClient(event_hooks={"response": [capture.async_hook]}) as transport:
            async with LambdaDB(**config, async_client=transport) as sdk:
                return await sdk.collection(name).query_async(**args)

    if async_mode:
        result = asyncio.run(run())
    else:
        with httpx.Client(event_hooks={"response": [capture.sync_hook]}) as transport:
            with LambdaDB(**config, client=transport) as sdk:
                result = sdk.collection(name).query(**args)

    # Retain only small score summaries; never record credentials or docsUrl.
    record_property("wire_scores", json.dumps(capture.scores, ensure_ascii=False))
    record_property("collection", name)
    violations = _contract_errors(capture.scores, result)
    record_property("score_contract_errors", json.dumps(violations, ensure_ascii=False))
    assert capture.query_responses == 1
    assert capture.download_responses == int(response_kind == "docs_url")
    assert result.is_docs_inline == (response_kind != "docs_url")
    assert len(result.results) == result.total == args["size"]
    if response_kind == "docs_url":
        assert all(len(doc.doc["payload"]) == 1100000 for doc in result.results)
    if with_facets:
        assert [(b.value, b.count) for b in result.facets["tags"].buckets] == [("match", 6)]
    else:
        assert result.facets is None
    assert not violations, "\n".join(violations)
