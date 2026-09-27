"""Facet wire contract and high-level result hydration, without live services."""
import asyncio
import json
import httpx
import pytest
from lambdadb import LambdaDB, models


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("download", [False, True])
def test_facets_preserved_through_query(async_mode, download):
    calls = []
    def handler(request):
        calls.append(request.method)
        if request.method == "GET":
            assert "x-api-key" not in request.headers
            return httpx.Response(200, json=[{"collection": "items", "doc": {"id": "1"}}])
        body = json.loads(request.content)
        assert body["size"] == (1 if download else 0)
        assert body["facets"]["tags"]["size"] == 3
        assert "query" not in body
        return httpx.Response(200, json={
            "took": 1, "total": 1 if download else 0, "docs": [],
            "isDocsInline": not download,
            "docsUrl": "https://files.example/docs" if download else None,
            "facets": {"tags": {"buckets": [{"value": "한글", "count": 2147483648}]}},
        })
    options = dict(base_url="https://api.example", project_name="project", project_api_key="test-key")
    args = dict(size=1 if download else 0, facets={"tags": {"size": 3}}, retries=None)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
            client = LambdaDB(**options, async_client=transport)
            return await client.collection("items").query_async(**args)
    if async_mode:
        response = asyncio.run(run())
    else:
        with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
            response = LambdaDB(**options, client=transport).collection("items").query(**args)
    assert response.facets["tags"].buckets[0].count == 2147483648
    assert response.facets["tags"].buckets[0].value == "한글"
    assert len(response.results) == (1 if download else 0)
    assert calls == (["POST", "GET"] if download else ["POST"])


def test_optional_facets_remain_optional_and_models_are_exported():
    request = models.QueryCollectionRequestBody(query={"queryString": {"query": "*:*"}})
    assert "facets" not in request.model_dump(by_alias=True)
    response = models.QueryCollectionResponse.model_validate({"took": 0, "total": 0, "docs": [], "isDocsInline": True})
    assert response.facets is None
    assert models.FacetRequest(size=10).size == 10
    assert models.FacetResult(buckets=[models.FacetBucket(value="x", count=1)]).buckets[0].value == "x"
