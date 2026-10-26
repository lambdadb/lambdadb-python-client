"""Opt-in Bayesian/native smoke, including docs contract 94a7b71.

Verify deployment separately before enabling LAMBDADB_RUN_BAYESIAN_SMOKE.
Only uniquely named collections created by this test are removed.
"""

import asyncio
import math
import os
import time
import uuid

import pytest

from lambdadb import LambdaDB, errors

pytestmark = pytest.mark.integration

EMBEDDING = {"provider": "openai", "model": "text-embedding-3-small", "sourceField": "body"}
LEXICAL = {"queryString": {"query": "body:restore"}}
VECTOR = {"knn": {"field": "vector", "queryVector": ([1, 0] + [0.0] * 62), "k": 30}}
RERANK = {"provider": "typesafe", "model": "jev-1.13.0",
          "queryText": "How do I restore a previous version?", "fields": ["body"]}


def _wait_query(collection, expected, **kwargs):
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        try:
            response = collection.query(**kwargs, retries=None)
            if len(response.results) == expected:
                return response
        except errors.LambdaDBError as error:
            if error.status_code not in (404, 429, 503):
                raise
        time.sleep(2)
    pytest.fail("Timed out waiting for query visibility")


def _delete_and_verify(sdk, name):
    for attempt in range(5):
        try:
            try:
                sdk.collections.delete(collection_name=name, retries=None)
            except errors.ResourceNotFoundError:
                pass
            try:
                sdk.collections.get(collection_name=name, retries=None)
            except errors.ResourceNotFoundError:
                print(f"Deleted {name}; absence verified (404)")
                return
        except errors.LambdaDBError as error:
            if error.status_code not in (429, 503):
                pytest.fail(f"Cleanup failed for {name}: HTTP {error.status_code}")
        if attempt < 4:
            time.sleep(2)
    pytest.fail(f"Cleanup absence unconfirmed for {name}")


@pytest.fixture
def live_sdk():
    if os.getenv("LAMBDADB_RUN_BAYESIAN_SMOKE") != "1":
        pytest.skip("set LAMBDADB_RUN_BAYESIAN_SMOKE=1 after verifying deployment")
    for name in ("LAMBDADB_BASE_URL", "LAMBDADB_PROJECT_NAME", "LAMBDADB_PROJECT_API_KEY"):
        if not os.getenv(name):
            pytest.fail(f"Missing {name}")
    names = []
    with LambdaDB(base_url=os.environ["LAMBDADB_BASE_URL"],
                  project_name=os.environ["LAMBDADB_PROJECT_NAME"],
                  project_api_key=os.environ["LAMBDADB_PROJECT_API_KEY"], timeout_ms=60_000) as sdk:
        try:
            yield sdk, names
        finally:
            failures = []
            for name in reversed(names):
                try:
                    _delete_and_verify(sdk, name)
                except BaseException:
                    failures.append(name)
            if failures:
                pytest.fail(f"Cleanup failed for temporary collections: {', '.join(failures)}")


def test_bayesian_and_rerank(live_sdk):
    sdk, names = live_sdk
    name = f"python-bayesian-{uuid.uuid4().hex[:12]}"
    names.append(name)
    stage = "create caller-vector collection"
    try:
        sdk.collections.create(collection_name=name, index_configs={
            "body": {"type": "text"}, "vector": {"type": "vector", "dimensions": 64},
        }, retries=None)
        coll = sdk.collection(name)
        coll.docs.upsert(docs=[
            {"id": "one", "body": "Restore a saved version using a branch.", "vector": ([1, 0] + [0.0] * 62)},
            {"id": "two", "body": "Restore a deleted document.", "vector": ([0.8, 0.2] + [0.0] * 62)},
            {"id": "three", "body": "Search a collection.", "vector": ([0.2, 0.8] + [0.0] * 62)},
        ], retries=None)
        query = {"bayesian": [LEXICAL, VECTOR]}
        args = dict(query=query, size=3, candidate_size=30, consistent_read=True)
        stage = "Bayesian retrieval"
        baseline = _wait_query(coll, 3, **args)
        assert all(math.isfinite(hit.score) and hit.retrieval_score is None for hit in baseline.results)
        assert baseline.rerank is None
        stage = "committed default read"
        committed = _wait_query(coll, 3, query=query, size=3, candidate_size=30)
        assert committed.documents == baseline.documents
        assert coll.query(**{**args, "size": 1}).documents == baseline.documents[:1]
        assert coll.query(**{**args, "query": {"bayesian": [{"bool": [LEXICAL]}, VECTOR]}}).documents == baseline.documents
        stage = "ordinary retrieval"
        for ordinary in [LEXICAL, VECTOR, *[{method: [LEXICAL, VECTOR]} for method in ("rrf", "mm", "l2")]]:
            response = coll.query(query=ordinary, size=3, consistent_read=True, retries=None)
            assert response.results
            assert all(math.isfinite(hit.score) for hit in response.results)
        stage = "server contract rejection"
        invalid_queries = [
            {"bayesian": [LEXICAL]}, {"bayesian": [LEXICAL, VECTOR, LEXICAL]},
            {"bayesian": [{**LEXICAL, "boost": 1}, VECTOR]},
            {"bayesian": [LEXICAL, {**VECTOR, "boost": 1}]},
            {"bayesian": [{"bool": [{"bool": [{**LEXICAL, "boost": 1}]}]}, VECTOR]},
            *[{"bayesian": [{method: [LEXICAL, VECTOR]}, VECTOR]} for method in ("bayesian", "rrf", "mm", "l2")],
            *[{"bayesian": [{"bool": [{"bool": [{method: [LEXICAL, VECTOR]}]}]}, VECTOR]}
              for method in ("bayesian", "rrf", "mm", "l2")],
        ]
        invalid = [*[{**args, "query": q} for q in invalid_queries],
                   *[{**args, "candidate_size": n} for n in (None, 0, 2, 1001)],
                   {**args, "rerank": RERANK},
                   *[{**args, "query": q} for q in [LEXICAL, VECTOR, *[{method: [LEXICAL, VECTOR]} for method in ("rrf", "mm", "l2")]]]]
        for request in invalid:
            with pytest.raises(errors.BadRequestError) as caught:
                coll.query(**request, retries=None)
            assert caught.value.status_code == 400
            time.sleep(0.15)
        print(f"Bayesian retrieval and {len(invalid)} server HTTP 400 checks passed")
        stage = "Bayesian native reranking"
        scores = {hit.doc["id"]: hit.score for hit in baseline.results}
        for async_mode in (False, True):
            request = dict(query=query, size=2, consistent_read=True, rerank={**RERANK, "candidateSize": 30}, retries=None)
            if async_mode:
                async def run():
                    async with LambdaDB(
                        base_url=os.environ["LAMBDADB_BASE_URL"],
                        project_name=os.environ["LAMBDADB_PROJECT_NAME"],
                        project_api_key=os.environ["LAMBDADB_PROJECT_API_KEY"],
                        timeout_ms=60_000,
                    ) as async_sdk:
                        return await async_sdk.collection(name).query_async(**request)
                response = asyncio.run(run())
            else:
                # Omit the rerank candidate budget to exercise its server default.
                response = coll.query(**{**request, "rerank": RERANK})
            assert response.rerank.status == "applied"
            assert response.rerank.candidate_count == response.rerank.scored_count == 3
            assert len(response.results) == 2
            for hit in response.results:
                assert math.isfinite(hit.score) and 0 <= hit.score <= 1
                assert hit.retrieval_score == pytest.approx(scores[hit.doc["id"]])
            print(f"Bayesian rerank applied: async={async_mode}, candidate/scored=3/3, retrievalScore preserved")
        stage = "expanded query and rerank count limits"
        for size in (101, 1000):
            expanded = {**args, "size": size, "candidate_size": 1000}
            assert len(coll.query(**expanded, retries=None).results) == 3
        expanded = {**args, "size": 1000, "candidate_size": None,
                    "rerank": {**RERANK, "candidateSize": 1000}}
        assert len(coll.query(**expanded, retries=None).results) == 3
        print("Query size and Bayesian/rerank candidate budgets of 1000 accepted; actual candidate set has 3 documents")
    except Exception as error:
        # SDK errors can contain response bodies and URLs; never print those in live logs.
        pytest.fail(f"{stage}: {type(error).__name__}; HTTP {getattr(error, 'status_code', 'n/a')}", pytrace=False)


@pytest.mark.parametrize("legacy", [False, True])
def test_native_embedding_create_update(live_sdk, legacy):
    sdk, names = live_sdk
    name = f"python-native-{uuid.uuid4().hex[:12]}"
    names.append(name)
    vector = {"type": "vector", "embedding": EMBEDDING, **({"managedEmbedding": True} if legacy else {})}
    stage = "native create"
    try:
        sdk.collections.create(collection_name=name, index_configs={"body": {"type": "text"}, "vector": vector}, retries=None)
        metadata = sdk.collections.get(collection_name=name).collection.index_configs["vector"]
        assert metadata.managed_embedding is True
        assert metadata.embedding.dimensions == 1536
        assert metadata.embedding.similarity == "cosine"
        stage = "native update"
        sdk.collections.update(collection_name=name, index_configs={
            "body": {"type": "text"}, "vector": {"type": "vector", "embedding": EMBEDDING},
        }, retries=None)
        coll = sdk.collection(name)
        stage = "document embedding generation"
        coll.docs.upsert(docs=[{"id": "one", "body": "Restore a saved collection version using a branch."}], retries=None)
        generated = _wait_query(coll, 1, query=LEXICAL, size=1, consistent_read=True, include_vectors=True)
        assert len(generated.documents[0]["vector"]) == 1536
        assert all(math.isfinite(value) for value in generated.documents[0]["vector"])
        stage = "query embedding generation and ordinary KNN"
        knn = {"knn": {"field": "vector", "queryText": "How do I restore a saved version?", "k": 30}}
        assert coll.query(query=knn, size=1, consistent_read=True, retries=None).documents[0]["id"] == "one"
        stage = "native Bayesian query"
        response = coll.query(query={"bayesian": [LEXICAL, knn]}, size=1, candidate_size=30, consistent_read=True, retries=None)
        assert response.documents[0]["id"] == "one"
        assert math.isfinite(response.results[0].score)
        print(f"Native create/update, actual document/query embeddings and KNN passed: legacy={legacy}")
    except Exception as error:
        pytest.fail(f"{stage}: {type(error).__name__}; HTTP {getattr(error, 'status_code', 'n/a')}", pytrace=False)


@pytest.mark.parametrize("nested", [False, True])
def test_unindexed_native_source_and_rerank_paths(live_sdk, nested):
    sdk, names = live_sdk
    name = f"python-stored-text-{uuid.uuid4().hex[:12]}"
    names.append(name)
    path = "article.body" if nested else "body"
    embedding = {**EMBEDDING, "sourceField": path}
    stage = "create vector-only schema"
    try:
        sdk.collections.create(collection_name=name, index_configs={
            "vector": {"type": "vector", "embedding": embedding},
        }, retries=None)
        coll = sdk.collection(name)
        text = "Restore a saved collection version using a branch."
        source = {"article": {"body": text}} if nested else {"body": text}
        stage = "generate embedding from unindexed stored text"
        coll.docs.upsert(docs=[{"id": "one", **source}], retries=None)
        result = _wait_query(coll, 1, size=1, consistent_read=True, include_vectors=True)
        vector = result.documents[0]["vector"]
        assert len(vector) == 1536
        assert all(math.isfinite(value) for value in vector)
        stage = "query text and rerank using unindexed path"
        query = {"knn": {"field": "vector", "queryText": "Restore a version", "k": 1000}}
        response = coll.query(query=query, size=101, consistent_read=True, retries=None,
            rerank={**RERANK, "fields": [path], "candidateSize": 1000})
        assert response.rerank.status == "applied"
        assert response.rerank.candidate_count == response.rerank.scored_count == 1
        assert response.documents[0]["id"] == "one"
        stage = "preserve server rejection of raw query vector on native field"
        with pytest.raises(errors.BadRequestError):
            coll.query(query={"knn": {"field": "vector", "queryVector": vector, "k": 1000}},
                       size=1000, consistent_read=True, retries=None)
        stage = "reject non-string unindexed embedding source"
        invalid = {"article": {"body": 42}} if nested else {"body": 42}
        with pytest.raises(errors.BadRequestError):
            coll.docs.upsert(docs=[{"id": "invalid", **invalid}], retries=None)
        stage = "preserve source and vector through sibling partial update"
        coll.docs.update(docs=[{"id": "one", "note": "unchanged source"}], retries=None)
        fetched = coll.docs.fetch(ids=["one"], consistent_read=True, include_vectors=True, retries=None)
        assert fetched.documents[0]["vector"] == vector
        stage = "full replacement omits source and old generated vector"
        coll.docs.upsert(docs=[{"id": "one", "note": "replacement"}], retries=None)
        fetched = coll.docs.fetch(ids=["one"], consistent_read=True, include_vectors=True, retries=None)
        assert "vector" not in fetched.documents[0]
        print(f"Unindexed native source, rerank, raw-vector rejection and write semantics passed: nested={nested}")
    except Exception as error:
        pytest.fail(f"{stage}: {type(error).__name__}; HTTP {getattr(error, 'status_code', 'n/a')}", pytrace=False)
