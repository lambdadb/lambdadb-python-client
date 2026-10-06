"""Scoped contract at backend 9072a1bc8925954369a887f558f1eaf387b7ea0e."""

import asyncio
import copy
import json

import httpx
import pytest
from pydantic import ValidationError

from lambdadb import LambdaDB, errors, models

LEXICAL = {"queryString": {"query": "body:restore"}}
VECTOR = {"knn": {"field": "vector", "queryVector": [1, 0], "k": 30}}
BAYESIAN = {"bayesian": [LEXICAL, VECTOR]}
EMBEDDING = {"provider": "openai", "model": "text-embedding-3-small", "sourceField": "body"}
RERANK = {"provider": "typesafe", "model": "jev-1.13.0", "queryText": "restore", "fields": ["body"]}
OPTIONS = dict(base_url="https://api.example", project_name="project", project_api_key="test-key")
EMPTY = {"took": 1, "total": 0, "docs": [], "isDocsInline": True}


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("high_level", [False, True])
@pytest.mark.parametrize("args,expected", [
    ({"query": BAYESIAN, "candidate_size": 30, "size": 2},
     {"query": BAYESIAN, "candidateSize": 30, "size": 2}),
    ({"query": BAYESIAN, "rerank": RERANK}, {"query": BAYESIAN, "rerank": RERANK}),
    ({"query": BAYESIAN, "size": 2, "rerank": {**RERANK, "candidateSize": 30}},
     {"query": BAYESIAN, "size": 2, "rerank": {**RERANK, "candidateSize": 30}}),
    ({"query": BAYESIAN, "candidate_size": 30, "rerank": None},
     {"query": BAYESIAN, "candidateSize": 30}),
    *[({"query": query}, {"query": query}) for query in
      [LEXICAL, VECTOR, *[{method: [LEXICAL, VECTOR]} for method in ("rrf", "mm", "l2")]]],
])
def test_query_wire(async_mode, high_level, args, expected):
    original = copy.deepcopy(args)
    calls = []

    def handler(request):
        body = json.loads(request.content)
        assert body == {**expected, "consistentRead": False, "includeVectors": False}
        calls.append(request.url.path)
        return httpx.Response(200, json=EMPTY)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async with LambdaDB(**OPTIONS, async_client=http) as sdk:
                if high_level:
                    await sdk.collection("items").query_async(**args)
                else:
                    await sdk.collections.query_async(collection_name="items", **args)

    if async_mode:
        asyncio.run(run())
    else:
        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            with LambdaDB(**OPTIONS, client=http) as sdk:
                if high_level:
                    sdk.collection("items").query(**args)
                else:
                    sdk.collections.query(collection_name="items", **args)
    assert calls == ["/projects/project/collections/items/query"]
    assert args == original


INVALID_QUERIES = [
    {"bayesian": [LEXICAL]}, {"bayesian": [LEXICAL, VECTOR, LEXICAL]},
    {"bayesian": [{**LEXICAL, "boost": 1}, VECTOR]},
    {"bayesian": [LEXICAL, {**VECTOR, "boost": 1}]},
    {"bayesian": [{"bool": [{"bool": [{**LEXICAL, "boost": 1}]}]}, VECTOR]},
    *[{"bayesian": [{method: [LEXICAL, VECTOR]}, VECTOR]} for method in ("bayesian", "rrf", "mm", "l2")],
    *[{"bayesian": [{"bool": [{"bool": [{method: [LEXICAL, VECTOR]}]}]}, VECTOR]}
      for method in ("bayesian", "rrf", "mm", "l2")],
]


@pytest.mark.parametrize("args", [
    *[{"query": query, "candidate_size": 30} for query in INVALID_QUERIES],
    {"query": BAYESIAN},
    *[{"query": BAYESIAN, "size": 2, "candidate_size": n} for n in (0, 1, 101)],
    {"query": BAYESIAN, "candidate_size": 30, "rerank": RERANK},
    *[{"query": query, "candidate_size": 30} for query in
      [LEXICAL, VECTOR, *[{method: [LEXICAL, VECTOR]} for method in ("rrf", "mm", "l2")]]],
])
def test_opaque_query_and_budget_errors_remain_server_bad_requests(args):
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(400, json={"message": "Invalid query contract"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with LambdaDB(**OPTIONS, client=http) as sdk:
            with pytest.raises(errors.BadRequestError) as caught:
                sdk.collection("items").query(**args, retries=None)
    assert caught.value.status_code == 400
    assert calls[0]["query"] == args["query"]
    assert calls[0].get("candidateSize") == args.get("candidate_size")
    assert len(calls) == 1


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("explicit_options", [False, True])
@pytest.mark.parametrize("use_model", [False, True])
def test_native_and_legacy_create_update_serialization(legacy, explicit_options, use_model):
    embedding = {**EMBEDDING, **({"dimensions": 512, "similarity": "dot_product"} if explicit_options else {})}
    vector = {"type": "vector", "embedding": embedding, **({"managedEmbedding": True} if legacy else {})}
    configs = {"vector": models.IndexConfigsVector.model_validate(vector) if use_model else vector}
    create = models.CreateCollectionRequest(collection_name="items", index_configs=configs)
    update = models.UpdateCollectionRequestBody(index_configs=configs)
    assert create.model_dump(mode="json", by_alias=True) == {"collectionName": "items", "indexConfigs": {"vector": vector}}
    assert update.model_dump(mode="json", by_alias=True) == {"indexConfigs": {"vector": vector}}
    parsed = models.IndexConfigsVector.model_validate({
        "type": "vector", "managedEmbedding": True,
        "embedding": {**EMBEDDING, "dimensions": 1536, "similarity": "cosine"},
    })
    assert parsed.managed_embedding is True
    assert parsed.embedding.dimensions == 1536
    assert parsed.embedding.similarity is models.Similarity.COSINE


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("field,value", [("dimensions", 512), ("similarity", "cosine")])
def test_native_conflicts_preserve_validation_order(legacy, field, value):
    config = {"type": "vector", "embedding": EMBEDDING, field: value}
    if legacy:
        config["managedEmbedding"] = True
    with pytest.raises(ValidationError, match=f"Top-level {field} (is|are) not allowed"):
        models.IndexConfigsVector.model_validate(config)


def test_false_still_rejects_embedding_before_missing_dimensions():
    with pytest.raises(ValidationError, match="embedding is not allowed when managedEmbedding=false"):
        models.IndexConfigsVector.model_validate({"type": "vector", "managedEmbedding": False, "embedding": EMBEDDING})


def test_caller_vector_default_unchanged():
    assert models.IndexConfigsVector(type=models.TypeVector.VECTOR, dimensions=2).model_dump(mode="json", by_alias=True) == {
        "type": "vector", "dimensions": 2, "similarity": "cosine",
    }


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("operation", ["create", "update"])
@pytest.mark.parametrize("legacy", [False, True])
def test_native_create_update_http(async_mode, operation, legacy):
    vector = {"type": "vector", "embedding": EMBEDDING, **({"managedEmbedding": True} if legacy else {})}
    calls = []

    def handler(request):
        calls.append(request.method)
        expected = {"indexConfigs": {"vector": vector}}
        if operation == "create":
            expected["collectionName"] = "items"
        assert json.loads(request.content) == expected
        metadata = {
            "collectionName": "items", "projectName": "project",
            "description": "", "tags": {}, "defaultBranchName": "main",
            "snapshotRetentionInDays": 1, "createdAt": 1788336000123,
            "updatedAt": 1788336000123, "numDocs": 0, "numPartitions": 1,
            "indexConfigs": {"vector": {"type": "vector", "managedEmbedding": True,
                "embedding": {**EMBEDDING, "dimensions": 1536, "similarity": "cosine"}}},
        }
        return httpx.Response(201 if operation == "create" else 200, json={"collection": metadata})

    kwargs = dict(collection_name="items", index_configs={"vector": vector})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async with LambdaDB(**OPTIONS, async_client=http) as sdk:
                return await getattr(sdk.collections, operation + "_async")(**kwargs)

    if async_mode:
        response = asyncio.run(run())
    else:
        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            with LambdaDB(**OPTIONS, client=http) as sdk:
                response = getattr(sdk.collections, operation)(**kwargs)
    assert calls == ["POST" if operation == "create" else "PATCH"]
    if operation == "update":
        assert response.collection.index_configs["vector"].managed_embedding is True
        assert response.collection.index_configs["vector"].embedding.dimensions == 1536


def test_candidate_budget_model_alias_and_typed_dict():
    request: models.QueryCollectionRequestBodyTypedDict = {"query": BAYESIAN, "candidate_size": 30}
    named = models.QueryCollectionRequestBody.model_validate(request)
    wire = models.QueryCollectionRequestBody.model_validate({"query": BAYESIAN, "candidateSize": 30})
    assert named.model_dump(by_alias=True) == wire.model_dump(by_alias=True)
    assert wire.candidate_size == 30
