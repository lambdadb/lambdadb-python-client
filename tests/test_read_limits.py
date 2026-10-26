"""Read limits and offloaded results from docs contract 94a7b71."""

import asyncio
import gzip
import json

import httpx
import pytest

from lambdadb import LambdaDB, Ref, errors


OPTIONS = dict(base_url="https://api.example", project_name="project", project_api_key="test-key")


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("high_level", [False, True])
@pytest.mark.parametrize("operation", ["fetch", "list", "list_filtered"])
def test_thousand_document_reads(async_mode, high_level, operation):
    ids = [str(i) for i in range(1000)]
    calls = []

    def handler(request):
        calls.append(request.method)
        if operation == "fetch":
            body = json.loads(request.content)
            assert body["ids"] == ids
            assert body["ref"] == {"kind": "tag", "name": "release-1"}
        elif operation == "list_filtered":
            body = json.loads(request.content)
            assert body["size"] == 1000
            assert body["filter"] == {"queryString": {"query": "*:*"}}
            assert body["ref"] == {"kind": "tag", "name": "release-1"}
        else:
            assert request.url.params["size"] == "1000"
            assert request.url.params["refKind"] == "tag"
            assert request.url.params["refName"] == "release-1"
        return httpx.Response(200, json={
            "took": 1, "total": 1000, "isDocsInline": True,
            "docs": [{"collection": "items", "doc": {"id": item}} for item in ids],
        })

    args = {"ref": Ref.tag("release-1"), "retries": None}
    args.update({"ids": ids} if operation == "fetch" else {"size": 1000})
    if operation == "list_filtered":
        args["filter_"] = {"queryString": {"query": "*:*"}}

    def call(sdk):
        api = sdk.collection("items").docs if high_level else sdk.collections.docs
        name = "fetch" if operation == "fetch" else (
            "list" if high_level else "list_docs_extended" if operation == "list_filtered" else "list_docs"
        )
        kwargs = args if high_level else {"collection_name": "items", **args}
        return getattr(api, name + ("_async" if async_mode else ""))(**kwargs)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async with LambdaDB(**OPTIONS, async_client=http) as sdk:
                return await call(sdk)

    if async_mode:
        result = asyncio.run(run())
    else:
        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            with LambdaDB(**OPTIONS, client=http) as sdk:
                result = call(sdk)
    documents = result.documents
    assert [item["id"] for item in documents] == ids
    assert calls == ["GET" if operation == "list" else "POST"]


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("filtered", [False, True])
def test_list_pages_use_thousand_document_requests_and_preserve_refs(async_mode, filtered):
    requests = []

    def handler(request):
        args = json.loads(request.content) if filtered else dict(request.url.params)
        start = int(args.get("pageToken", "0"))
        count = int(args["size"])
        requests.append((count, start))
        if filtered:
            assert args["ref"] == {"kind": "tag", "name": "release-1"}
            assert args["filter"] == {"queryString": {"query": "*:*"}}
        else:
            assert args["refKind"] == "tag"
            assert args["refName"] == "release-1"
        end = min(start + count, 1003)
        body = {"total": end - start, "isDocsInline": True,
                "docs": [{"collection": "items", "doc": {"id": str(i)}} for i in range(start, end)]}
        if end < 1003:
            body["nextPageToken"] = str(end)
        return httpx.Response(200, json=body)

    # A logical page may exceed the server's per-request limit.
    args = {"size": 1001, "ref": Ref.tag("release-1")}
    if filtered:
        args["filter_"] = {"queryString": {"query": "*:*"}}

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async with LambdaDB(**OPTIONS, async_client=http) as sdk:
                return [page async for page in sdk.collection("items").docs.list_pages_async(**args)]

    if async_mode:
        pages = asyncio.run(run())
    else:
        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            with LambdaDB(**OPTIONS, client=http) as sdk:
                pages = list(sdk.collection("items").docs.list_pages(**args))
    assert [len(page) for page in pages] == [1001, 2]
    assert [doc["id"] for page in pages for doc in page] == [str(i) for i in range(1003)]
    assert requests == [(1000, 0), (1, 1000), (1000, 1001)]


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("high_level", [False, True])
def test_thousand_reranked_results_through_gzip_docs_url(async_mode, high_level):
    documents = [{"collection": "items", "doc": {"id": str(i)},
                  "score": (1000 - i) / 1000, "retrievalScore": float(1000 - i)} for i in range(1000)]
    metadata = {"status": "applied", "provider": "typesafe", "model": "jev-1.13.0",
                "candidateCount": 1000, "scoredCount": 1000, "took": 1}
    calls = []

    def handler(request):
        calls.append(request.method)
        if request.method == "GET":
            assert str(request.url) == "https://files.example/docs?signature=opaque"
            assert "x-api-key" not in request.headers
            return httpx.Response(200, content=gzip.compress(json.dumps(documents).encode()),
                                  headers={"Content-Encoding": "gzip", "Content-Type": "application/json"})
        body = json.loads(request.content)
        assert body["size"] == body["rerank"]["candidateSize"] == body["query"]["knn"]["k"] == 1000
        assert body["rerank"]["fields"] == ["article.body"]
        return httpx.Response(200, json={
            "took": 2, "total": 1000, "docs": [], "isDocsInline": False, "maxScore": 1.0,
            "docsUrl": "https://files.example/docs?signature=opaque", "rerank": metadata,
        })

    args = {"query": {"knn": {"field": "vector", "queryVector": [1, 0], "k": 1000}},
            "size": 1000, "rerank": {"provider": "typesafe", "model": "jev-1.13.0",
                "queryText": "restore", "fields": ["article.body"], "candidateSize": 1000}}

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async with LambdaDB(**OPTIONS, async_client=http) as sdk:
                if high_level:
                    return await sdk.collection("items").query_async(**args)
                return await sdk.collections.query_async(collection_name="items", **args)

    if async_mode:
        response = asyncio.run(run())
    else:
        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            with LambdaDB(**OPTIONS, client=http) as sdk:
                response = sdk.collection("items").query(**args) if high_level else sdk.collections.query(collection_name="items", **args)
    assert response.total == 1000
    assert response.rerank.model_dump(mode="json", by_alias=True) == metadata
    assert [doc.model_dump(mode="json", by_alias=True) for doc in response.results] == (documents if high_level else [])
    assert calls == (["POST", "GET"] if high_level else ["POST"])


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("operation", ["fetch", "list"])
@pytest.mark.parametrize("status,error", [(400, errors.BadRequestError), (503, errors.ServiceUnavailableError)])
def test_read_limit_and_storage_errors_remain_server_errors(async_mode, operation, status, error):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"message": "Read rejected without partial results"})

    args = {"ids": [str(i) for i in range(1001)]} if operation == "fetch" else {"size": 1001}
    args["retries"] = None

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async with LambdaDB(**OPTIONS, async_client=http) as sdk:
                await getattr(sdk.collection("items").docs, operation + "_async")(**args)

    with pytest.raises(error) as caught:
        if async_mode:
            asyncio.run(run())
        else:
            with httpx.Client(transport=httpx.MockTransport(handler)) as http:
                with LambdaDB(**OPTIONS, client=http) as sdk:
                    getattr(sdk.collection("items").docs, operation)(**args)
    assert caught.value.status_code == status
    assert len(calls) == 1
