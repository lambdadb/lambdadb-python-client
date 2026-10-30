"""Opt-in Bayesian/native smoke, including lambdadb OpenAPI 1c3e7d4 (Cohere).

Verify deployment separately before enabling LAMBDADB_RUN_BAYESIAN_SMOKE.
Only uniquely named collections created by this test are removed.
"""

import asyncio
import base64
import math
import os
import struct
import time
import uuid
import zlib

import pytest

from lambdadb import LambdaDB, errors

pytestmark = pytest.mark.integration

EMBEDDING = {"provider": "openai", "model": "text-embedding-3-small", "sourceField": "body"}
LEXICAL = {"queryString": {"query": "body:restore"}}
VECTOR = {"knn": {"field": "vector", "queryVector": ([1, 0] + [0.0] * 62), "k": 30}}
RERANK = {"provider": "typesafe", "model": "jev-1.13.0",
          "queryText": "How do I restore a previous version?", "fields": ["body"]}
# Provider timeouts, rate limits and outages are transient under shared load; with
# onFailure "returnOriginal" they arrive as a fallback naming the reason. Retry only
# those, a bounded number of times. Credential, invalid-response and any other
# fallback fails at once, and a fallback never counts as applied reranking.
TRANSIENT_RERANK_REASONS = {"timeout", "rateLimit", "unavailable"}
RERANK_ATTEMPTS = 3


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


def _rerank_query(collection, label, **kwargs):
    request = {**kwargs, "rerank": {**kwargs["rerank"], "onFailure": "returnOriginal"}}
    for attempt in range(1, RERANK_ATTEMPTS + 1):
        response = collection.query(**request)
        if response.rerank is None or response.rerank.status != "fallback":
            return response
        reason = response.rerank.reason
        # Documented fallback shape: retrieval order without rerank scores or criteria.
        if (response.rerank.scored_count != 0 or response.rerank.criteria_version is not None
                or len(response.results) > request["size"]
                or any(hit.retrieval_score is not None for hit in response.results)):
            pytest.fail(f"{label} fallback with reason {reason} on attempt {attempt}/{RERANK_ATTEMPTS} "
                        "does not match the documented shape", pytrace=False)
        if reason not in TRANSIENT_RERANK_REASONS or attempt == RERANK_ATTEMPTS:
            pytest.fail(f"{label} fell back with reason {reason} on attempt {attempt}/{RERANK_ATTEMPTS}",
                        pytrace=False)
        print(f"{label} fell back with reason {reason}; retrying ({attempt + 1}/{RERANK_ATTEMPTS})")
        time.sleep(attempt * 5)


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
        stage = "accept raw query vector on native field"
        raw = coll.query(query={"knn": {"field": "vector", "queryVector": vector, "k": 1000}},
                         size=1000, consistent_read=True, retries=None)
        assert raw.documents[0]["id"] == "one"
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
        print(f"Unindexed native source, rerank, raw query vector and write semantics passed: nested={nested}")
    except Exception as error:
        pytest.fail(f"{stage}: {type(error).__name__}; HTTP {getattr(error, 'status_code', 'n/a')}", pytrace=False)


def _png_data_uri(rgb, size=32):
    row = b"\x00" + bytes(rgb) * size
    chunk = lambda kind, data: (struct.pack(">I", len(data)) + kind + data
                                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(row * size)) + chunk(b"IEND", b""))
    return "data:image/png;base64," + base64.b64encode(png).decode()


def test_cohere_sources_query_inputs_direct_vectors_and_rerank(live_sdk):
    sdk, names = live_sdk
    name = f"python-cohere-{uuid.uuid4().hex[:12]}"
    names.append(name)
    multimodal = {"provider": "cohere", "model": "embed-v5.0-fast", "dimensions": 256,
                  "sources": [{"field": "title", "type": "text"}, {"field": "photos", "type": "image"}]}
    text = {"provider": "cohere", "model": "embed-v5.0-pro", "sources": [{"field": "title", "type": "text"}]}
    red, blue = _png_data_uri((220, 20, 20)), _png_data_uri((20, 20, 220))
    direct = [0.0] * 255 + [1.0]
    stage = "reject provider-specific embedding settings"
    try:
        for invalid in ({**multimodal, "dimensions": 300},
                        {**text, "provider": "openai", "model": "text-embedding-3-small",
                         "sources": multimodal["sources"]}):
            with pytest.raises(errors.BadRequestError):
                sdk.collections.create(collection_name=name, retries=None, index_configs={
                    "v": {"type": "vector", "embedding": invalid}})
        stage = "create Cohere source mappings"
        sdk.collections.create(collection_name=name, retries=None, index_configs={
            "mm": {"type": "vector", "embedding": multimodal},
            "text": {"type": "vector", "embedding": text},
        })
        configs = sdk.collections.get(collection_name=name).collection.index_configs
        assert configs["mm"].embedding.model_dump(mode="json", by_alias=True)["sources"] == multimodal["sources"]
        assert configs["mm"].embedding.source_field is None
        assert (configs["mm"].embedding.dimensions, configs["text"].embedding.dimensions) == (256, 2048)
        coll = sdk.collection(name)
        stage = "generate text/image embeddings and accept a direct vector"
        coll.docs.upsert(retries=None, docs=[
            {"id": "red", "title": "Red running shoes", "photos": [red]},
            {"id": "blue", "title": "Blue rain jacket", "photos": [blue]},
            {"id": "plain", "title": "Leather wallet", "photos": []},
            {"id": "direct", "title": "Wool scarf", "mm": direct},
        ])
        fetched = _wait_query(coll, 4, size=4, consistent_read=True, include_vectors=True)
        vectors = {doc["id"]: doc for doc in fetched.documents}
        assert all(len(doc["mm"]) == 256 and len(doc["text"]) == 2048 for doc in vectors.values())
        assert all(math.isfinite(value) for doc in vectors.values() for value in doc["mm"] + doc["text"])
        assert vectors["direct"]["mm"] == pytest.approx(direct)
        stage = "query with text, mixed inputs and a raw vector"
        by_text = coll.query(query={"knn": {"field": "text", "queryText": "rain jacket", "k": 4}},
                             size=1, consistent_read=True, retries=None)
        assert by_text.documents[0]["id"] == "blue"
        mixed = coll.query(size=1, consistent_read=True, retries=None, query={"knn": {
            "field": "mm", "k": 4,
            "queryInputs": [{"type": "text", "value": "red shoes"}, {"type": "image", "value": red}]}})
        assert mixed.documents[0]["id"] == "red"
        raw = coll.query(query={"knn": {"field": "mm", "queryVector": direct, "k": 4}},
                         size=1, consistent_read=True, retries=None)
        assert raw.documents[0]["id"] == "direct"
        stage = "Cohere reranking"
        for model in ("rerank-v5.0-pro", "rerank-v5.0-fast"):
            response = _rerank_query(coll, f"Cohere {model}",
                                     query={"knn": {"field": "text", "queryText": "shoes", "k": 4}},
                                     size=2, consistent_read=True, retries=None,
                                     rerank={"provider": "cohere", "model": model, "queryText": "running shoes",
                                             "fields": ["title"]})
            assert response.rerank.status == "applied"
            assert response.rerank.criteria_version == "cohere-relevance-v1"
            assert response.rerank.candidate_count == response.rerank.scored_count == 4
            assert response.documents[0]["id"] == "red"
            assert all(0 <= hit.score <= 1 and hit.retrieval_score is not None for hit in response.results)
        stage = "bulk upsert with caller-supplied native vectors"
        coll.docs.bulk_upsert_docs(retries=None, docs=[
            {"id": "bulk", "title": "Canvas tote bag", "mm": [1.0] + [0.0] * 255, "text": [1.0] + [0.0] * 2047},
        ])
        deadline = time.monotonic() + 180
        while not coll.docs.fetch(ids=["bulk"], consistent_read=True, retries=None).documents:
            if time.monotonic() > deadline:
                pytest.fail("Timed out waiting for bulk upsert visibility")
            time.sleep(2)
        bulk = coll.docs.fetch(ids=["bulk"], consistent_read=True, include_vectors=True, retries=None).documents[0]
        assert bulk["mm"] == pytest.approx([1.0] + [0.0] * 255)
        print("Cohere sources, image/text embeddings, queryInputs, direct vectors, bulk and rerank passed")
    except Exception as error:
        pytest.fail(f"{stage}: {type(error).__name__}; HTTP {getattr(error, 'status_code', 'n/a')}", pytrace=False)
