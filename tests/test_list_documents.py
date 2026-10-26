"""List document-body convenience access without changing response serialization."""

import asyncio

import httpx
import pytest

from lambdadb import LambdaDB, models


@pytest.mark.parametrize("items,expected", [
    ([], []),
    ([{"collection": "items", "doc": {"id": "one"}}], [{"id": "one"}]),
    ([{"id": "one"}], [{"id": "one"}]),
    ([{"collection": "items", "doc": {"id": "one"}}, {"id": "two", "doc": None}],
     [{"id": "one"}, {"id": "two", "doc": None}]),
])
def test_list_documents_accepts_envelopes_and_legacy_plain_documents(items, expected):
    response = models.ListDocsResponse(total=len(items), results=items, is_docs_inline=True)
    before = response.model_dump(mode="json", by_alias=True)
    assert response.documents == expected
    assert response.model_dump(mode="json", by_alias=True) == before
    assert "documents" not in before


@pytest.mark.parametrize("async_mode", [False, True])
def test_list_documents_after_download_preserves_page_token(async_mode):
    def handler(request):
        if request.url.host == "files.example":
            assert "x-api-key" not in request.headers
            return httpx.Response(200, json=[{"collection": "items", "doc": {"id": "one"}}])
        return httpx.Response(200, json={"total": 1, "docs": [], "isDocsInline": False,
            "docsUrl": "https://files.example/docs", "nextPageToken": "opaque+/="})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async with LambdaDB(async_client=http, project_api_key="test-key") as sdk:
                return await sdk.collection("items").docs.list_async()

    if async_mode:
        response = asyncio.run(run())
    else:
        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            with LambdaDB(client=http, project_api_key="test-key") as sdk:
                response = sdk.collection("items").docs.list()
    assert response.documents == [{"id": "one"}]
    assert response.results == [{"collection": "items", "doc": {"id": "one"}}]
    assert response.next_page_token == "opaque+/="
