"""Native reranking wire contract, legacy compatibility and result hydration."""
from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path
import subprocess
import sys

import httpx
import pytest
from pydantic import ValidationError

from lambdadb import LambdaDB, models

CONFIG = {"provider": "typesafe", "model": "jev-1.13.0", "queryText": "restore", "fields": ["title", "body"]}
QUERY = {"knn": {"field": "embedding", "vector": [1.0, 0.0], "k": 20}}
OPTIONS = dict(base_url="https://api.example", project_name="project", project_api_key="test-key")


def test_schema_and_generated_outputs() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "schemas/native-reranking.json").read_text())
    assert schema["source"]["revision"] == "55d888299fee44466326a9db8016af9811ade13b"
    assert schema["schemas"]["RerankConfig"]["required"] == ["provider", "model", "queryText", "fields"]
    subprocess.run([sys.executable, str(root / "scripts/generate_reranking.py"), "--check"], check=True)
    for name in ["RerankConfig", "RerankConfigTypedDict", "RerankResponse", "RerankResponseTypedDict"]:
        assert getattr(models, name) is not None
        assert name in models.__all__


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("high_level", [False, True])
@pytest.mark.parametrize("download", [False, True])
@pytest.mark.parametrize("use_model", [False, True])
@pytest.mark.parametrize("levels", [None, 2, 3, 10])
@pytest.mark.parametrize("retrieval", ["lexical", "vector", "bayesian"])
def test_rerank_wire_round_trip(async_mode, high_level, download, use_model, levels, retrieval):
    query = QUERY if retrieval == "vector" else {"queryString": {"query": "body:restore"}}
    if retrieval == "bayesian":
        query = {"bayesian": [{"queryString": {"query": "body:restore"}}, QUERY]}
    facets = {"tags": {"size": 3}} if retrieval == "lexical" else None
    config = {**CONFIG, "candidateSize": 50, "onFailure": "returnOriginal"}
    if levels is not None:
        config["criteria"] = [f"Relevance level {i}" for i in range(levels)]
    model = models.RerankConfig.model_validate(config)
    request = model if use_model else model.model_dump(mode="json")
    documents = [
        {"collection": "items", "doc": {"id": "second"}, "score": .80000002000004, "retrievalScore": .1},
        {"collection": "items", "doc": {"id": "first"}, "score": 0.0, "retrievalScore": 3.0},
    ]
    metadata = {"status": "applied", "provider": "typesafe", "model": "jev-1.13.0",
                "resolvedModel": "jev-1.13.0", "candidateCount": 4, "scoredCount": 4, "took": 12,
                "criteriaVersion": "custom" if levels else "default-relevance-v1"}
    calls = []

    def handler(request):
        calls.append(request.method)
        if request.method == "GET":
            assert "x-api-key" not in request.headers
            return httpx.Response(200, json=documents)
        body = json.loads(request.content)
        assert body["rerank"] == config
        assert body["query"] == query  # knn.k is independent of candidateSize.
        assert body["size"] == 2
        if facets is None:
            assert "facets" not in body
        else:
            assert body["facets"] == facets
        assert body["fields"] == {"include": ["id"]}
        payload = {"took": 20, "total": 2, "docs": [] if download else documents,
                   "isDocsInline": not download, "maxScore": .80000002000004,
                   "rerank": metadata}
        if facets is not None:
            payload["facets"] = {"tags": {"buckets": [{"value": "x", "count": 100}]}}
        if download:
            payload["docsUrl"] = "https://files.example/docs"
        return httpx.Response(200, json=payload)

    args = dict(query=copy.deepcopy(query), rerank=request, size=2,
                facets=facets, fields={"include": ["id"]}, retries=None)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
            client = LambdaDB(**OPTIONS, async_client=transport)
            if high_level:
                return await client.collection("items").query_async(**args)
            return await client.collections.query_async(collection_name="items", **args)

    if async_mode:
        response = asyncio.run(run())
    else:
        with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
            client = LambdaDB(**OPTIONS, client=transport)
            response = client.collection("items").query(**args) if high_level else client.collections.query(collection_name="items", **args)
    assert response.rerank.model_dump(mode="json", by_alias=True) == metadata
    assert response.max_score == .80000002000004
    if facets is not None:
        assert response.facets["tags"].buckets[0].count == 100
    else:
        assert response.facets is None
    populated = high_level or not download
    assert calls == (["POST", "GET"] if download and high_level else ["POST"])
    assert [item.model_dump(mode="json", by_alias=True) for item in response.results] == (documents if populated else [])
    if populated:
        assert response.results[1].score == 0.0
        assert response.results[1].retrieval_score == 3.0
        assert "retrievalScore" not in response.documents[1]
    assert args["query"] == query
    assert model.model_dump(mode="json", by_alias=True) == config


@pytest.mark.parametrize("status", ["skipped", "fallback"])
@pytest.mark.parametrize("async_mode", [False, True])
def test_skipped_and_fallback_results(status, async_mode):
    docs = [] if status == "skipped" else [{"collection": "items", "doc": {"id": "1"}, "score": 3.0}]
    metadata = {"status": status, "provider": "typesafe", "model": "jev-1.13.0",
                "candidateCount": 0 if status == "skipped" else 4, "scoredCount": 0,
                "took": 0, "reason": "noCandidates" if status == "skipped" else "timeout"}
    payload = {"took": 1, "total": len(docs), "docs": docs, "isDocsInline": True, "rerank": metadata}
    if docs:
        payload["maxScore"] = 3.0
    def handler(_):
        return httpx.Response(200, json=payload)
    args = dict(query={"queryString": {"query": "body:restore"}}, rerank=models.RerankConfig.model_validate(CONFIG), retries=None)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
            return await LambdaDB(**OPTIONS, async_client=transport).collection("items").query_async(**args)
    if async_mode:
        result = asyncio.run(run())
    else:
        with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
            result = LambdaDB(**OPTIONS, client=transport).collection("items").query(**args)
    assert result.model_dump(mode="json", by_alias=True) == payload
    assert result.rerank.criteria_version is None
    assert all(item.retrieval_score is None for item in result.results)


def test_legacy_and_null_are_omitted_and_defaults_stay_server_side():
    legacy = models.QueryCollectionRequestBody(query=QUERY)
    null = models.QueryCollectionRequestBody(query=QUERY, rerank=None)
    assert null.model_dump(mode="json", by_alias=True) == legacy.model_dump(mode="json", by_alias=True)
    assert "rerank" not in null.model_dump(mode="json", by_alias=True)
    config = models.RerankConfig.model_validate({**CONFIG, "candidateSize": None, "onFailure": None, "criteria": None})
    assert config.model_dump(mode="json", by_alias=True) == CONFIG
    request = models.QueryCollectionRequestBody(query=QUERY, rerank=config, size=60)
    assert "candidateSize" not in request.model_dump(mode="json", by_alias=True)["rerank"]
    response = models.QueryCollectionResponse.model_validate({"took": 0, "total": 1, "isDocsInline": True,
                "maxScore": 0, "docs": [{"collection": "items", "doc": {}, "score": 0}]})
    wire = response.model_dump(mode="json", by_alias=True)
    assert "rerank" not in wire
    assert "retrievalScore" not in wire["docs"][0]
    assert wire["maxScore"] == wire["docs"][0]["score"] == 0
    assert models.RerankResponse(status="applied", provider="typesafe", model="jev-1.13.0",
                                 candidate_count=1, scored_count=1, took=0).criteria_version is None


@pytest.mark.parametrize("patch", [
    {"provider": "cohere"}, {"model": "other"}, {"queryText": " "}, {"queryText": "가" * 2731},
    {"fields": []}, {"fields": ["x"] * 2}, {"fields": [str(i) for i in range(9)]}, {"fields": ["a..b"]},
    {"candidateSize": 0}, {"candidateSize": 101}, {"candidateSize": True}, {"onFailure": "ignore"},
    {"criteria": []}, {"criteria": ["one"]}, {"criteria": ["x", "x"]}, {"criteria": ["x", " "]},
    {"criteria": ["x", None]}, {"criteria": [{}, {}]}, {"criteria": [str(i) for i in range(11)]},
    {"criteria": ["x", "가" * 683]}, {"criteria": [str(i) + "x" * 1700 for i in range(5)]},
    {"weights": [0, 1]}, {"threshold": .5}, {"rubricVersion": "v1"}, {"apiKey": "not-supported"},
])
def test_invalid_config_rejected_without_loss(patch):
    with pytest.raises(ValidationError):
        models.RerankConfig.model_validate({**CONFIG, **patch})


@pytest.mark.parametrize("field", ["provider", "model", "queryText", "fields"])
def test_required_config_fields(field):
    missing = {key: value for key, value in CONFIG.items() if key != field}
    with pytest.raises(ValidationError):
        models.RerankConfig.model_validate(missing)


def test_utf8_boundaries_and_exact_criteria_text():
    values = [str(i) + "x" * 2047 for i in range(4)]
    config = models.RerankConfig.model_validate({**CONFIG, "criteria": values, "queryText": "x" * 8192})
    assert config.criteria == values
    assert models.RerankConfig.model_validate({**CONFIG, "criteria": [" No match ", "Best match"]}).criteria == [" No match ", "Best match"]
    with pytest.raises(ValidationError):
        models.RerankConfig.model_validate({**CONFIG, "criteria": [*values, "x"]})


@pytest.mark.parametrize("patch", [{"size": 0}, {"size": 101}, {"size": 51}, {"sort": []}, {"query": None}, {"query": {}}])
def test_invalid_request_context(patch):
    with pytest.raises(ValidationError):
        models.QueryCollectionRequestBody.model_validate({"query": QUERY, "size": 10,
            "rerank": {**CONFIG, "candidateSize": 50}, **patch})


def test_legacy_facet_only_request_stays_valid():
    request = models.QueryCollectionRequestBody(size=0, facets={"tags": {}})
    assert "rerank" not in request.model_dump(mode="json", by_alias=True)


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("high_level", [False, True])
@pytest.mark.parametrize("explicit_null", [False, True])
def test_legacy_wire_request_and_response(async_mode, high_level, explicit_null):
    def handler(request):
        body = json.loads(request.content)
        assert "rerank" not in body
        assert body == {"query": QUERY, "consistentRead": False, "includeVectors": False}
        return httpx.Response(200, json={"took": 1, "total": 1, "isDocsInline": True,
            "maxScore": .1, "docs": [{"collection": "items", "doc": {"id": "1"}, "score": .1}]})
    args = dict(query=QUERY, retries=None)
    if explicit_null:
        args["rerank"] = None
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
            client = LambdaDB(**OPTIONS, async_client=transport)
            if high_level:
                return await client.collection("items").query_async(**args)
            return await client.collections.query_async(collection_name="items", **args)
    if async_mode:
        result = asyncio.run(run())
    else:
        with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
            client = LambdaDB(**OPTIONS, client=transport)
            result = client.collection("items").query(**args) if high_level else client.collections.query(collection_name="items", **args)
    assert result.rerank is None
    assert result.results[0].score == .1
    assert result.results[0].retrieval_score is None


@pytest.mark.parametrize("query", [{"term": {"field": "tag", "value": "x"}}, QUERY])
def test_server_validation_errors_do_not_become_client_fallback(query):
    from lambdadb import errors

    def handler(request):
        body = json.loads(request.content)
        assert body["rerank"]["onFailure"] == "returnOriginal"
        return httpx.Response(400, json={"message": "Invalid selected text or query"})
    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        client = LambdaDB(**OPTIONS, client=transport)
        with pytest.raises(errors.BadRequestError):
            client.collection("items").query(query=query, rerank={**CONFIG, "onFailure": "returnOriginal"}, retries=None)
