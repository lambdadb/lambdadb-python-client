"""Single ref reads, branch schema updates, and paged ref listings at the wire boundary."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx
import pytest
from pydantic import ValidationError

from lambdadb import LambdaDB, errors, models

INDEX_CONFIGS: Dict[str, Any] = {
    "title": {"type": "text", "analyzers": ["english"], "description": "Book title"},
    "category": {"type": "keyword"},
}
BASE = "/projects/project/collections/catalog"


def _branch(name: str, *, empty: bool = False) -> Dict[str, Any]:
    snapshot = {"snapshotId": "snapshot-1", "snapshotCommittedAt": 1788335940000}
    return {
        "name": name,
        "parentBranch": None if name == "main" else {"branchId": "main-id", "name": "main"},
        "headSnapshot": None if empty else snapshot,
        "parentSnapshot": None if empty or name == "main" else snapshot,
        "numDocs": 0 if empty else 1000,
        "dataUpdatedAt": None if empty else 1788335940000,
        "indexConfigs": INDEX_CONFIGS,
        "createdAt": 1788336000000,
        "futureField": "ignored",
    }


def _tag(name: str) -> Dict[str, Any]:
    return {
        "name": name,
        "snapshotId": "snapshot-1",
        "snapshotCommittedAt": 1788335940000,
        "numDocs": 1000,
        "dataUpdatedAt": 1788335940000,
        "indexConfigs": INDEX_CONFIGS,
        "createdAt": 1788336000000,
    }


def _alias(name: str, *, dangling: bool = False) -> Dict[str, Any]:
    return {
        "aliasId": "alias-id",
        "aliasName": name,
        "targetKind": "BRANCH",
        "targetName": "main",
        "targetId": "main-branch-id",
        "aliasRevision": 1,
        "dangling": dangling,
        "indexConfigs": None if dangling else INDEX_CONFIGS,
        "createdAt": 1788336000000,
    }


_ENTRY = {"branches": _branch, "tags": _tag, "aliases": _alias}
_SINGULAR = {"branches": "branch", "tags": "tag", "aliases": "alias"}


def _handler(requests: List[httpx.Request]):
    """Serve single reads, branch updates, and three-page listings."""

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        parts = request.url.path[len(BASE) + 1 :].split("/")
        plural = parts[0]
        if len(parts) == 1:
            token = request.url.params.get("pageToken")
            if token == "malformed":
                return httpx.Response(400, json={"message": "Invalid pageToken"})
            page = {None: 0, "page-2": 1, "page+/=3": 2}[token]
            body: Dict[str, Any] = {plural: [_ENTRY[plural](f"item-{page}")]}
            if page < 2:
                body["nextPageToken"] = ["page-2", "page+/=3"][page]
            return httpx.Response(200, json=body)
        name = parts[1]
        if name == "missing":
            return httpx.Response(404, json={"message": "not found"})
        if request.method == "PATCH":
            if name == "conflict":
                return httpx.Response(409, json={"message": "catalog changed"})
            if name == "release-1":
                return httpx.Response(400, json={"message": "not a branch"})
            entry = _branch(name)
            entry["indexConfigs"] = json.loads(request.content)["indexConfigs"]
            return httpx.Response(200, json={"branch": entry})
        if name in {"empty", "dangling"}:
            entry = _ENTRY[plural](name, **{name if name == "empty" else "dangling": True})
        else:
            entry = _ENTRY[plural](name)
        return httpx.Response(200, json={_SINGULAR[plural]: entry})

    return handle


def _sync_client(requests: List[httpx.Request]) -> LambdaDB:
    return LambdaDB(
        project_api_key="secret",
        base_url="https://api.example",
        project_name="project",
        client=httpx.Client(transport=httpx.MockTransport(_handler(requests))),
    )


def _async_client(requests: List[httpx.Request]) -> LambdaDB:
    return LambdaDB(
        project_api_key="secret",
        base_url="https://api.example",
        project_name="project",
        async_client=httpx.AsyncClient(transport=httpx.MockTransport(_handler(requests))),
    )


def _assert_single_reads(requests: List[httpx.Request], results: Dict[str, Any]) -> None:
    assert [(request.method, request.url.path, request.url.query, request.content)
            for request in requests] == [
        ("GET", f"{BASE}/branches/candidate", b"", b""),
        ("GET", f"{BASE}/branches/empty", b"", b""),
        ("GET", f"{BASE}/tags/release-1", b"", b""),
        ("GET", f"{BASE}/aliases/latest", b"", b""),
        ("GET", f"{BASE}/aliases/dangling", b"", b""),
    ]
    branch = results["branch"].branch
    assert isinstance(branch.index_configs["title"], models.IndexConfigsText)
    assert branch.index_configs["title"].description == "Book title"
    assert branch.num_docs == 1000
    assert branch.data_updated_at == 1788335940000
    assert branch.data_updated_at_dt is not None
    assert branch.data_updated_at_dt.timestamp() == 1788335940

    empty = results["empty"].branch
    assert empty.num_docs == 0
    assert empty.data_updated_at is None
    assert empty.data_updated_at_dt is None
    assert set(empty.index_configs) == {"title", "category"}

    tag = results["tag"].tag
    assert tag.num_docs == 1000
    assert tag.data_updated_at_dt.timestamp() == 1788335940
    assert isinstance(tag.index_configs["category"], models.IndexConfigs)

    alias = results["alias"].alias
    assert alias.dangling is False
    assert alias.index_configs is not None
    assert set(alias.index_configs) == {"title", "category"}

    dangling = results["dangling"].alias
    assert dangling.dangling is True
    assert dangling.index_configs is None


def test_single_ref_reads_sync() -> None:
    requests: List[httpx.Request] = []
    collection = _sync_client(requests).collection("catalog")
    results = {
        "branch": collection.branches.get("candidate"),
        "empty": collection.branches.get("empty"),
        "tag": collection.tags.get("release-1"),
        "alias": collection.aliases.get("latest"),
        "dangling": collection.aliases.get("dangling"),
    }
    _assert_single_reads(requests, results)

    for refs in (collection.branches, collection.tags, collection.aliases):
        with pytest.raises(errors.ResourceNotFoundError):
            refs.get("missing")
        with pytest.raises(ValidationError):
            refs.get("x")
    assert len(requests) == 8


def test_single_ref_reads_async() -> None:
    requests: List[httpx.Request] = []

    async def run() -> Dict[str, Any]:
        collection = _async_client(requests).collection("catalog")
        results = {
            "branch": await collection.branches.get_async("candidate"),
            "empty": await collection.branches.get_async("empty"),
            "tag": await collection.tags.get_async("release-1"),
            "alias": await collection.aliases.get_async("latest"),
            "dangling": await collection.aliases.get_async("dangling"),
        }
        with pytest.raises(errors.ResourceNotFoundError):
            await collection.tags.get_async("missing")
        return results

    results = asyncio.run(run())
    assert len(requests) == 6
    _assert_single_reads(requests[:5], results)


def test_ref_details_require_the_nullable_fields_to_be_present() -> None:
    for model, body, nullable in (
        (models.BranchDetails, _branch("empty", empty=True), "dataUpdatedAt"),
        (models.AliasDetails, _alias("dangling", dangling=True), "indexConfigs"),
    ):
        assert body[nullable] is None
        model.model_validate(body)
        with pytest.raises(ValidationError, match=nullable):
            model.model_validate({k: v for k, v in body.items() if k != nullable})

    for field in ("numDocs", "dataUpdatedAt", "indexConfigs"):
        with pytest.raises(ValidationError, match=field):
            models.TagDetails.model_validate(
                {k: v for k, v in _tag("release-1").items() if k != field}
            )
    with pytest.raises(ValidationError, match="dataUpdatedAt"):
        models.TagDetails.model_validate({**_tag("release-1"), "dataUpdatedAt": None})


def test_branch_update_sends_only_index_configs_sync_and_async() -> None:
    requests: List[httpx.Request] = []
    collection = _sync_client(requests).collection("catalog")

    returned = collection.branches.get("candidate").branch.index_configs
    added = {**INDEX_CONFIGS, "year": {"type": "long"}}
    updated = collection.branches.update("candidate", index_configs=added)
    collection.branches.update("candidate", index_configs=returned)
    collection.branches.update(
        "main",
        index_configs={
            "category": models.IndexConfigs(type=models.Type.KEYWORD),
        },
    )

    assert [(r.method, r.url.path, r.url.query) for r in requests[1:]] == [
        ("PATCH", f"{BASE}/branches/candidate", b""),
        ("PATCH", f"{BASE}/branches/candidate", b""),
        ("PATCH", f"{BASE}/branches/main", b""),
    ]
    assert json.loads(requests[1].content) == {"indexConfigs": added}
    assert json.loads(requests[2].content) == {"indexConfigs": INDEX_CONFIGS}
    assert json.loads(requests[3].content) == {
        "indexConfigs": {"category": {"type": "keyword"}}
    }
    assert set(updated.branch.index_configs) == {"title", "category", "year"}

    with pytest.raises(ValidationError):
        collection.branches.update("candidate", index_configs={})
    with pytest.raises(ValidationError):
        collection.branches.update("x", index_configs=added)
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        models.UpdateBranchRequestBody.model_validate(
            {"indexConfigs": INDEX_CONFIGS, "description": "not a branch field"}
        )
    with pytest.raises(ValidationError):
        models.UpdateBranchRequestBody.model_validate({})
    assert len(requests) == 4

    with pytest.raises(errors.CatalogConflictError, match="catalog changed"):
        collection.branches.update("conflict", index_configs=added)
    with pytest.raises(errors.BadRequestError, match="not a branch"):
        collection.branches.update("release-1", index_configs=added)
    with pytest.raises(errors.ResourceNotFoundError):
        collection.branches.update("missing", index_configs=added)

    async_requests: List[httpx.Request] = []

    async def run() -> models.BranchResponse:
        async_collection = _async_client(async_requests).collection("catalog")
        with pytest.raises(errors.CatalogConflictError):
            await async_collection.branches.update_async("conflict", index_configs=added)
        return await async_collection.branches.update_async(
            "candidate", index_configs=added
        )

    assert set(asyncio.run(run()).branch.index_configs) == {"title", "category", "year"}
    assert async_requests[1].method == "PATCH"
    assert async_requests[1].url.path == f"{BASE}/branches/candidate"
    assert json.loads(async_requests[1].content) == {"indexConfigs": added}


@pytest.mark.parametrize("plural", ["branches", "tags", "aliases"])
def test_ref_listing_parameters_and_pagination_sync(plural: str) -> None:
    requests: List[httpx.Request] = []
    refs = getattr(_sync_client(requests).collection("catalog"), plural)

    first = refs.list()
    assert requests[0].url.path == f"{BASE}/{plural}"
    assert requests[0].url.query == b""
    assert first.next_page_token == "page-2"
    assert len(getattr(first, plural)) == 1

    refs.list(size=None, page_token=None)
    assert requests[1].url.query == b""

    last = refs.list(size=5, page_token="page+/=3")
    assert dict(requests[2].url.params) == {"size": "5", "pageToken": "page+/=3"}
    assert last.next_page_token is None

    refs.list(size=100)
    assert dict(requests[3].url.params) == {"size": "100"}
    refs.list(page_token="page-2")
    assert dict(requests[4].url.params) == {"pageToken": "page-2"}

    for invalid in ({"page_token": ""}, {"size": 0}, {"size": 101}):
        with pytest.raises(ValidationError):
            refs.list(**invalid)
    assert len(requests) == 5

    with pytest.raises(errors.BadRequestError, match="Invalid pageToken"):
        refs.list(page_token="malformed")

    requests.clear()
    pages = list(refs.list_pages(size=1))
    assert [len(page) for page in pages] == [1, 1, 1]
    assert [dict(request.url.params) for request in requests] == [
        {"size": "1"},
        {"size": "1", "pageToken": "page-2"},
        {"size": "1", "pageToken": "page+/=3"},
    ]

    requests.clear()
    items = list(refs.iter_all())
    name = "alias_name" if plural == "aliases" else "name"
    assert [getattr(item, name) for item in items] == ["item-0", "item-1", "item-2"]
    assert [request.url.params.get("pageToken") for request in requests] == [
        None,
        "page-2",
        "page+/=3",
    ]
    assert all(request.url.params["size"] == "100" for request in requests)


@pytest.mark.parametrize("plural", ["branches", "tags", "aliases"])
def test_ref_listing_parameters_and_pagination_async(plural: str) -> None:
    requests: List[httpx.Request] = []

    async def run() -> None:
        refs = getattr(_async_client(requests).collection("catalog"), plural)
        first = await refs.list_async()
        assert requests[0].url.query == b""
        assert first.next_page_token == "page-2"
        await refs.list_async(size=5, page_token="page-2")
        assert dict(requests[1].url.params) == {"size": "5", "pageToken": "page-2"}
        with pytest.raises(ValidationError):
            await refs.list_async(page_token="")
        assert len(requests) == 2

        requests.clear()
        pages = [page async for page in refs.list_pages_async(size=2)]
        assert [len(page) for page in pages] == [1, 1, 1]
        assert [dict(request.url.params) for request in requests] == [
            {"size": "2"},
            {"size": "2", "pageToken": "page-2"},
            {"size": "2", "pageToken": "page+/=3"},
        ]

        requests.clear()
        items = [item async for item in refs.iter_all_async(page_size=7)]
        assert len(items) == 3
        assert [request.url.params.get("pageToken") for request in requests] == [
            None,
            "page-2",
            "page+/=3",
        ]

    asyncio.run(run())


def test_collection_listing_omits_unset_parameters_and_maps_400() -> None:
    requests: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        token: Optional[str] = request.url.params.get("pageToken")
        if token == "malformed":
            return httpx.Response(400, json={"message": "Invalid pageToken"})
        return httpx.Response(200, json={"collections": []})

    options = {
        "project_api_key": "secret",
        "base_url": "https://api.example",
        "project_name": "project",
    }
    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        client = LambdaDB(**options, client=transport)
        assert client.collections.list().next_page_token is None
        client.collections.list(size=None, page_token=None)
        client.collections.list(size=20, page_token="next")
        assert list(client.collections.iter_all()) == []
        with pytest.raises(ValidationError):
            client.collections.list(page_token="")
        assert len(requests) == 4
        with pytest.raises(errors.BadRequestError, match="Invalid pageToken"):
            client.collections.list(page_token="malformed", retries=None)

    assert requests[0].url.query == b""
    assert requests[1].url.query == b""
    assert dict(requests[2].url.params) == {"size": "20", "pageToken": "next"}
    assert dict(requests[3].url.params) == {"size": "100"}

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
            client = LambdaDB(**options, async_client=transport)
            await client.collections.list_async()
            with pytest.raises(ValidationError):
                await client.collections.list_async(page_token="")
            with pytest.raises(errors.BadRequestError, match="Invalid pageToken"):
                await client.collections.list_async(page_token="malformed", retries=None)

    requests.clear()
    asyncio.run(run())
    assert requests[0].url.query == b""
    assert len(requests) == 2


def test_collection_index_configs_update_matches_the_branch_update_body() -> None:
    bodies: List[Dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        if "/branches/" in request.url.path:
            return httpx.Response(200, json={"branch": _branch("main")})
        return httpx.Response(
            200,
            json={
                "collection": {
                    "projectName": "project",
                    "collectionName": "catalog",
                    "indexConfigs": INDEX_CONFIGS,
                    "numPartitions": 1,
                    "numDocs": 0,
                    "description": "",
                    "tags": {},
                    "defaultBranchName": "main",
                    "snapshotRetentionInDays": 30,
                    "createdAt": 1788336000000,
                    "updatedAt": 1788336000000,
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        client = LambdaDB(project_api_key="secret", client=transport)
        # The deprecated collection path keeps working and sends the same schema.
        client.collections.update(collection_name="catalog", index_configs=INDEX_CONFIGS)
        client.collection("catalog").branches.update("main", index_configs=INDEX_CONFIGS)

    assert bodies == [{"indexConfigs": INDEX_CONFIGS}, {"indexConfigs": INDEX_CONFIGS}]
