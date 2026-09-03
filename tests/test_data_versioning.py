"""Data Versioning contract tests pinned to docs revision 63e07d6b."""

from __future__ import annotations

import asyncio
import inspect
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Tuple, Union

import httpx
import pytest
from pydantic import ValidationError

from lambdadb import AliasTarget, LambdaDB, Ref, RefSource
from lambdadb import errors, models


def _response(
    request: httpx.Request, status: int, body: Dict[str, Any]
) -> httpx.Response:
    return httpx.Response(status, json=body, request=request)


def _collection_body(name: str = "catalog") -> Dict[str, Any]:
    return {
        "projectName": "project",
        "collectionName": name,
        "indexConfigs": {"title": {"type": "text", "analyzers": ["english"]}},
        "description": "Product catalog",
        "tags": {"environment": "test"},
        "numPartitions": 1,
        "numDocs": 0,
        "defaultBranchName": "main",
        "snapshotRetentionInDays": 14,
        "createdAt": 1788336000123,
        "updatedAt": 1788336000456,
        "dataUpdatedAt": 1788336000789,
    }


def _text_index(analyzer: models.Analyzer) -> Dict[
    str,
    Union[
        models.IndexConfigsText,
        models.IndexConfigsVector,
        models.IndexConfigs,
        models.IndexConfigsObject,
    ],
]:
    return {
        "title": models.IndexConfigsText(
            type=models.TypeText.TEXT, analyzers=[analyzer]
        )
    }


def test_ref_validation_and_millisecond_round_trip() -> None:
    ref = Ref.alias("production-read")
    assert ref.model_dump(mode="json") == {
        "kind": "alias",
        "name": "production-read",
    }

    source = RefSource.branch("main", as_of=1788336000123)
    assert (
        source.model_dump(mode="json", by_alias=True, exclude_none=True)["asOf"]
        == 1788336000123
    )

    details = models.RefDetails.model_validate(
        {"name": "main", "snapshotId": "snapshot-1", "createdAt": 1788336000123}
    )
    assert details.model_dump(by_alias=True)["createdAt"] == 1788336000123
    assert details.created_at_dt == datetime.fromtimestamp(
        1788336000.123, tz=timezone.utc
    )

    with pytest.raises(ValidationError, match="as_of is only valid"):
        models.RefSource.model_validate({"kind": "tag", "name": "release-1", "asOf": 1})
    assert RefSource.branch("main", as_of=-1).as_of == -1
    with pytest.raises(ValidationError):
        Ref.branch("x")
    with pytest.raises(ValidationError):
        models.AliasTarget.model_validate({"kind": "alias", "name": "other-alias"})
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Ref.model_validate({"kind": "branch", "name": "main", "asOf": 1})


def test_list_page_token_stays_opaque_while_ref_name_is_validated() -> None:
    request = models.ListDocsRequest(
        collection_name="catalog",
        page_token="x+/=.",
        ref_kind=models.RefKind.ALIAS,
        ref_name="production-read",
    )
    assert request.page_token == "x+/=."

    with pytest.raises(ValidationError):
        models.ListDocsRequest(
            collection_name="catalog",
            ref_kind=models.RefKind.BRANCH,
            ref_name="x",
        )


def test_collection_metadata_and_create_delete_status_contract() -> None:
    requests: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            payload = json.loads(request.content)
            return _response(
                request,
                201,
                {
                    "collection": {
                        "collectionName": payload["collectionName"],
                        "description": payload["description"],
                        "tags": payload["tags"],
                        "defaultBranchName": "main",
                        "snapshotRetentionInDays": payload["snapshotRetentionInDays"],
                        "createdAt": 1788336000123,
                    }
                },
            )
        if request.method == "PATCH":
            return _response(request, 200, {"collection": _collection_body()})
        return _response(request, 200, {"message": "Collection deleted"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        client = LambdaDB(
            project_api_key="secret",
            base_url="https://api.example",
            project_name="project",
            client=transport,
        )
        created = client.collections.create(
            collection_name="catalog",
            index_configs=_text_index(models.Analyzer.ENGLISH),
            description="Product catalog",
            tags={"environment": "test"},
            snapshot_retention_in_days=14,
        )
        updated = client.collections.update(
            collection_name="catalog", tags={}, snapshot_retention_in_days=14
        )
        deleted = client.collections.delete(collection_name="catalog")

    create_body = json.loads(requests[0].content)
    assert create_body["description"] == "Product catalog"
    assert create_body["tags"] == {"environment": "test"}
    assert created.collection.default_branch_name == "main"
    assert created.collection.created_at == 1788336000123
    assert json.loads(requests[1].content) == {
        "tags": {},
        "snapshotRetentionInDays": 14,
    }
    assert updated.collection.snapshot_retention_in_days == 14
    assert deleted.message == "Collection deleted"

    with pytest.raises(ValidationError, match="at least one collection field"):
        models.UpdateCollectionRequestBody()
    with pytest.raises(ValidationError):
        models.CreatedCollection.model_validate(
            {
                "collectionName": "catalog",
                "description": "",
                "tags": {},
                "defaultBranchName": "develop",
                "snapshotRetentionInDays": 30,
                "createdAt": 1788336000123,
            }
        )
    with pytest.raises(ValidationError):
        models.BulkUpsertDocsRequestBody.model_validate(
            {"objectKey": "object", "type": None}
        )


def test_collection_metadata_and_status_contract_async() -> None:
    requests: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            payload = json.loads(request.content)
            return _response(
                request,
                201,
                {
                    "collection": {
                        "collectionName": payload["collectionName"],
                        "description": payload["description"],
                        "tags": payload["tags"],
                        "defaultBranchName": "main",
                        "snapshotRetentionInDays": payload["snapshotRetentionInDays"],
                        "createdAt": 1788336000123,
                    }
                },
            )
        if request.method == "PATCH":
            return _response(request, 200, {"collection": _collection_body()})
        return _response(request, 200, {"message": "Collection deleted"})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as transport:
            client = LambdaDB(
                project_api_key="secret",
                base_url="https://api.example",
                project_name="project",
                async_client=transport,
            )
            created = await client.collections.create_async(
                collection_name="catalog",
                index_configs=_text_index(models.Analyzer.ENGLISH),
                description="Product catalog",
                tags={"environment": "test"},
                snapshot_retention_in_days=14,
            )
            updated = await client.collections.update_async(
                collection_name="catalog", tags={}, snapshot_retention_in_days=14
            )
            deleted = await client.collections.delete_async(collection_name="catalog")
            assert created.collection.default_branch_name == "main"
            assert updated.collection.snapshot_retention_in_days == 14
            assert deleted.message == "Collection deleted"

    asyncio.run(run())
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/projects/project/collections"),
        ("PATCH", "/projects/project/collections/catalog"),
        ("DELETE", "/projects/project/collections/catalog"),
    ]
    assert json.loads(requests[1].content) == {
        "tags": {},
        "snapshotRetentionInDays": 14,
    }


def test_lifecycle_sync_paths_bodies_and_error_mapping() -> None:
    requests: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path.endswith("/branches") and request.method == "POST":
            body = json.loads(request.content)
            if body["branchName"] == "duplicate":
                return _response(request, 409, {"message": "already exists"})
            return _response(
                request,
                201,
                {
                    "branch": {
                        "name": body["branchName"],
                        "snapshotId": None,
                        "createdAt": 1788336000001,
                    }
                },
            )
        if path.endswith("/branches"):
            return _response(request, 200, {"branches": []})
        if "/branches/" in path:
            if path.endswith("/missing"):
                return _response(request, 404, {"message": "not found"})
            return _response(request, 200, {"message": "Ref deleted"})
        if path.endswith("/tags") and request.method == "POST":
            body = json.loads(request.content)
            return _response(
                request,
                201,
                {
                    "tag": {
                        "name": body["tagName"],
                        "snapshotId": "s1",
                        "createdAt": 1788336000002,
                    }
                },
            )
        if path.endswith("/tags"):
            return _response(request, 200, {"tags": []})
        if "/tags/" in path:
            return _response(request, 200, {"message": "Ref deleted"})
        if path.endswith("/aliases") and request.method == "POST":
            body = json.loads(request.content)
            return _response(
                request,
                201,
                {"alias": _alias_body(body["aliasName"], body["target"], 0)},
            )
        if path.endswith("/aliases"):
            return _response(
                request,
                200,
                {
                    "aliases": [
                        _alias_body(
                            "production-read",
                            {"kind": "tag", "name": "release-1"},
                            1,
                            dangling=True,
                        )
                    ]
                },
            )
        if "/aliases/" in path and request.method == "PATCH":
            body = json.loads(request.content)
            return _response(
                request,
                200,
                {"alias": _alias_body(path.rsplit("/", 1)[1], body["target"], 2)},
            )
        return _response(request, 200, {"message": "Ref deleted"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        client = LambdaDB(
            project_api_key="secret",
            base_url="https://api.example",
            project_name="project",
            client=transport,
        )
        collection = client.collection("catalog")
        branch = collection.branches.create(
            "experiment", source=RefSource.branch("main", as_of=1788336000123)
        )
        tag = collection.tags.create("release-1", source=RefSource.branch("experiment"))
        alias = collection.aliases.create(
            "production-read", target=AliasTarget.tag("release-1")
        )
        retargeted = collection.aliases.retarget(
            "production-read", target=AliasTarget.branch("main")
        )
        aliases = collection.aliases.list()
        collection.branches.delete("experiment")

        with pytest.raises(errors.ResourceAlreadyExistsError):
            collection.branches.create("duplicate")
        with pytest.raises(errors.ResourceNotFoundError):
            collection.branches.delete("missing")

    assert requests[0].url.path.endswith("/collections/catalog/branches")
    assert json.loads(requests[0].content)["source"]["asOf"] == 1788336000123
    assert branch.branch.created_at == 1788336000001
    assert tag.tag.snapshot_id == "s1"
    assert alias.alias.target_kind.value == "TAG"
    assert retargeted.alias.target_kind.value == "BRANCH"
    assert aliases.aliases[0].dangling is True


def test_all_lifecycle_endpoints_work_async() -> None:
    requests: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path.endswith("/branches") and request.method == "POST":
            body = json.loads(request.content)
            if body["branchName"] == "duplicate":
                return _response(request, 409, {"message": "already exists"})
            return _response(
                request,
                201,
                {
                    "branch": {
                        "name": body["branchName"],
                        "snapshotId": "snapshot-1",
                        "createdAt": 1788336000001,
                    }
                },
            )
        if path.endswith("/branches"):
            return _response(request, 200, {"branches": []})
        if "/branches/" in path:
            return _response(request, 200, {"message": "Ref deleted"})
        if path.endswith("/tags") and request.method == "POST":
            body = json.loads(request.content)
            return _response(
                request,
                201,
                {
                    "tag": {
                        "name": body["tagName"],
                        "snapshotId": "snapshot-1",
                        "createdAt": 1788336000002,
                    }
                },
            )
        if path.endswith("/tags"):
            return _response(request, 200, {"tags": []})
        if "/tags/" in path:
            return _response(request, 200, {"message": "Ref deleted"})
        if path.endswith("/aliases") and request.method == "POST":
            body = json.loads(request.content)
            return _response(
                request,
                201,
                {"alias": _alias_body(body["aliasName"], body["target"], 0)},
            )
        if path.endswith("/aliases"):
            return _response(request, 200, {"aliases": []})
        if request.method == "PATCH":
            body = json.loads(request.content)
            return _response(
                request,
                200,
                {"alias": _alias_body("production-read", body["target"], 1)},
            )
        return _response(request, 200, {"message": "Ref deleted"})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as transport:
            client = LambdaDB(
                project_api_key="secret",
                base_url="https://api.example",
                project_name="project",
                async_client=transport,
            )
            collection = client.collection("catalog")
            await collection.branches.create_async(
                "experiment", source=RefSource.tag("release-1")
            )
            await collection.branches.list_async()
            await collection.branches.delete_async("experiment")
            await collection.tags.create_async(
                "release-1", source=RefSource.branch("main")
            )
            await collection.tags.list_async()
            await collection.tags.delete_async("release-1")
            await collection.aliases.create_async(
                "production-read", target=AliasTarget.tag("release-1")
            )
            await collection.aliases.list_async()
            await collection.aliases.retarget_async(
                "production-read", target=AliasTarget.branch("main")
            )
            await collection.aliases.delete_async("production-read")
            with pytest.raises(errors.ResourceAlreadyExistsError):
                await collection.branches.create_async("duplicate")

    asyncio.run(run())
    assert [(request.method, request.url.path) for request in requests[:10]] == [
        ("POST", "/projects/project/collections/catalog/branches"),
        ("GET", "/projects/project/collections/catalog/branches"),
        ("DELETE", "/projects/project/collections/catalog/branches/experiment"),
        ("POST", "/projects/project/collections/catalog/tags"),
        ("GET", "/projects/project/collections/catalog/tags"),
        ("DELETE", "/projects/project/collections/catalog/tags/release-1"),
        ("POST", "/projects/project/collections/catalog/aliases"),
        ("GET", "/projects/project/collections/catalog/aliases"),
        ("PATCH", "/projects/project/collections/catalog/aliases/production-read"),
        ("DELETE", "/projects/project/collections/catalog/aliases/production-read"),
    ]
    assert json.loads(requests[0].content)["source"] == {
        "kind": "tag",
        "name": "release-1",
    }


def _alias_body(
    name: str,
    target: Dict[str, str],
    revision: int,
    *,
    dangling: bool = False,
) -> Dict[str, Any]:
    return {
        "aliasId": "alias-id",
        "aliasName": name,
        "targetKind": target["kind"].upper(),
        "targetName": target["name"],
        "targetId": "target-id",
        "aliasRevision": revision,
        "dangling": dangling,
        "createdAt": 1788336000003,
    }


def test_read_refs_and_write_branches_reach_correct_locations() -> None:
    requests: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path.endswith("/query"):
            return _response(
                request, 200, {"took": 1, "total": 0, "docs": [], "isDocsInline": True}
            )
        if path.endswith("/fetch"):
            return _response(
                request, 200, {"took": 1, "total": 0, "docs": [], "isDocsInline": True}
            )
        if path.endswith("/docs"):
            return _response(
                request, 200, {"total": 0, "docs": [], "isDocsInline": True}
            )
        if path.endswith("/docs/list"):
            return _response(
                request, 200, {"total": 0, "docs": [], "isDocsInline": True}
            )
        return _response(request, 202, {"message": "accepted"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        client = LambdaDB(
            project_api_key="secret",
            base_url="https://api.example",
            project_name="project",
            client=transport,
        )
        collection = client.collection("catalog")
        collection.query(query={"matchAll": {}}, ref=Ref.tag("release-1"))
        collection.docs.fetch(ids=["1"], ref=Ref.alias("production-read"))
        collection.docs.list(ref=Ref.branch("experiment"))
        collection.docs.list(
            filter_={"term": {"active": True}}, ref=Ref.tag("release-1")
        )
        collection.docs.upsert(docs=[{"id": "1"}], branch="experiment")
        collection.docs.update(docs=[{"id": "1", "title": "new"}], branch="experiment")
        collection.docs.delete(ids=["1"], branch="experiment")

    bodies = [json.loads(request.content) for request in requests if request.content]
    assert bodies[0]["ref"] == {"kind": "tag", "name": "release-1"}
    assert bodies[1]["ref"] == {"kind": "alias", "name": "production-read"}
    assert dict(requests[2].url.params) == {
        "includeVectors": "false",
        "refKind": "branch",
        "refName": "experiment",
    }
    assert bodies[2]["ref"] == {"kind": "tag", "name": "release-1"}
    assert [body["branch"] for body in bodies[3:]] == ["experiment"] * 3


def test_consistent_read_rejects_tag_and_alias_before_network() -> None:
    requests: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise AssertionError("network should not be called")

    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        client = LambdaDB(project_api_key="secret", client=transport)
        collection = client.collection("catalog")
        with pytest.raises(ValueError, match="direct branch ref"):
            collection.query(
                query={"matchAll": {}},
                consistent_read=True,
                ref=Ref.tag("release-1"),
            )
        with pytest.raises(ValueError, match="direct branch ref"):
            collection.docs.fetch(
                ids=["1"],
                consistent_read=True,
                ref=Ref.alias("production-read"),
            )

    assert not requests


def test_list_pages_and_iter_all_preserve_ref_on_every_page_sync_and_async() -> None:
    sync_requests: List[httpx.Request] = []
    async_requests: List[httpx.Request] = []

    def page_response(
        request: httpx.Request, sink: List[httpx.Request]
    ) -> httpx.Response:
        sink.append(request)
        token = request.url.params.get("pageToken")
        number = "2" if token else "1"
        body: Dict[str, Any] = {
            "total": 2,
            "docs": [{"collection": "catalog", "doc": {"id": number}}],
            "isDocsInline": True,
        }
        if not token:
            body["nextPageToken"] = "x+/=."
        return _response(request, 200, body)

    sync_transport = httpx.MockTransport(
        lambda request: page_response(request, sync_requests)
    )
    async_transport = httpx.MockTransport(
        lambda request: page_response(request, async_requests)
    )

    async def run() -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(transport=async_transport) as async_client:
            client = LambdaDB(
                project_api_key="secret",
                base_url="https://api.example",
                project_name="project",
                async_client=async_client,
            )
            return [
                doc
                async for doc in client.collection("catalog").docs.iter_all_async(
                    page_size=2, ref=Ref.alias("production-read")
                )
            ]

    with httpx.Client(transport=sync_transport) as transport:
        client = LambdaDB(
            project_api_key="secret",
            base_url="https://api.example",
            project_name="project",
            client=transport,
        )
        pages = list(
            client.collection("catalog").docs.list_pages(
                size=2, ref=Ref.tag("release-1")
            )
        )
        all_docs = list(
            client.collection("catalog").docs.iter_all(
                page_size=2, ref=Ref.branch("experiment")
            )
        )
    async_docs = asyncio.run(run())

    assert pages == [[{"id": "1"}, {"id": "2"}]]
    assert all_docs == [{"id": "1"}, {"id": "2"}]
    assert async_docs == [{"id": "1"}, {"id": "2"}]
    assert [
        (r.url.params["refKind"], r.url.params["refName"]) for r in sync_requests[:2]
    ] == [("tag", "release-1")] * 2
    assert [
        (r.url.params["refKind"], r.url.params["refName"]) for r in sync_requests[2:]
    ] == [("branch", "experiment")] * 2
    assert [
        (r.url.params["refKind"], r.url.params["refName"]) for r in async_requests
    ] == [("alias", "production-read")] * 2
    assert [r.url.params.get("pageToken") for r in sync_requests] == [
        None,
        "x+/=.",
        None,
        "x+/=.",
    ]
    assert [r.url.params.get("pageToken") for r in async_requests] == [
        None,
        "x+/=.",
    ]


def test_filtered_list_pages_preserve_body_ref_on_every_page() -> None:
    requests: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = json.loads(request.content)
        body: Dict[str, Any] = {
            "total": 2,
            "docs": [
                {
                    "collection": "catalog",
                    "doc": {"id": "2" if payload.get("pageToken") else "1"},
                }
            ],
            "isDocsInline": True,
        }
        if "pageToken" not in payload:
            body["nextPageToken"] = "opaque-next"
        return _response(request, 200, body)

    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        client = LambdaDB(project_api_key="secret", client=transport)
        pages = list(
            client.collection("catalog").docs.list_pages(
                size=2,
                filter_={"term": {"active": True}},
                ref=Ref.tag("release-1"),
            )
        )

    assert pages == [[{"id": "1"}, {"id": "2"}]]
    assert [json.loads(request.content)["ref"] for request in requests] == [
        {"kind": "tag", "name": "release-1"},
        {"kind": "tag", "name": "release-1"},
    ]


def test_bulk_upload_forwards_signed_headers_uses_transfer_client_and_same_branch() -> (
    None
):
    api_requests: List[httpx.Request] = []
    transfer_requests: List[httpx.Request] = []

    def api_handler(request: httpx.Request) -> httpx.Response:
        api_requests.append(request)
        if request.method == "GET":
            return _response(
                request,
                200,
                {
                    "url": "https://storage.example/upload",
                    "type": "application/json",
                    "httpMethod": "PUT",
                    "objectKey": "objects/data.json",
                    "sizeLimitBytes": 10000,
                    "headers": {"x-amz-checksum-sha256": "signed-value"},
                },
            )
        return _response(request, 202, {"message": "accepted"})

    def transfer_handler(request: httpx.Request) -> httpx.Response:
        transfer_requests.append(request)
        return _response(request, 200, {})

    with (
        httpx.Client(transport=httpx.MockTransport(api_handler)) as api_client,
        httpx.Client(
            transport=httpx.MockTransport(transfer_handler)
        ) as transfer_client,
    ):
        client = LambdaDB(
            project_api_key="secret",
            base_url="https://api.example",
            project_name="project",
            client=api_client,
        )
        client.collection("catalog").docs.bulk_upsert_docs(
            docs=[{"id": "1"}], branch="experiment", transfer_client=transfer_client
        )

    assert len(api_requests) == 2
    assert api_requests[0].url.params["branch"] == "experiment"
    assert json.loads(api_requests[1].content)["branch"] == "experiment"
    assert len(transfer_requests) == 1
    assert transfer_requests[0].url.host == "storage.example"
    assert transfer_requests[0].headers["x-amz-checksum-sha256"] == "signed-value"
    assert transfer_requests[0].headers["content-type"] == "application/json"


def test_bulk_upload_respects_zero_size_limit_without_transfer_or_completion() -> None:
    api_requests: List[httpx.Request] = []
    transfer_requests: List[httpx.Request] = []

    def api_handler(request: httpx.Request) -> httpx.Response:
        api_requests.append(request)
        return _response(
            request,
            200,
            {
                "url": "https://storage.example/upload",
                "type": "application/json",
                "httpMethod": "PUT",
                "objectKey": "objects/data.json",
                "sizeLimitBytes": 0,
                "headers": {},
            },
        )

    def transfer_handler(request: httpx.Request) -> httpx.Response:
        transfer_requests.append(request)
        return _response(request, 200, {})

    with (
        httpx.Client(transport=httpx.MockTransport(api_handler)) as api_client,
        httpx.Client(
            transport=httpx.MockTransport(transfer_handler)
        ) as transfer_client,
    ):
        client = LambdaDB(project_api_key="secret", client=api_client)
        with pytest.raises(ValueError, match="exceeds limit 0 bytes"):
            client.collection("catalog").docs.bulk_upsert_docs(
                docs=[{"id": "1"}], transfer_client=transfer_client
            )

    assert len(api_requests) == 1
    assert not transfer_requests

    api_requests.clear()

    async def run() -> None:
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(api_handler)) as api_client,
            httpx.AsyncClient(
                transport=httpx.MockTransport(transfer_handler)
            ) as transfer_client,
        ):
            client = LambdaDB(project_api_key="secret", async_client=api_client)
            with pytest.raises(ValueError, match="exceeds limit 0 bytes"):
                await client.collection("catalog").docs.bulk_upsert_docs_async(
                    docs=[{"id": "1"}], transfer_client=transfer_client
                )

    asyncio.run(run())
    assert len(api_requests) == 1
    assert not transfer_requests


def test_async_lifecycle_read_and_bulk_upload_match_sync_behavior() -> None:
    api_requests: List[httpx.Request] = []
    transfer_requests: List[httpx.Request] = []

    def api_handler(request: httpx.Request) -> httpx.Response:
        api_requests.append(request)
        path = request.url.path
        if path.endswith("/branches"):
            body = json.loads(request.content)
            return _response(
                request,
                201,
                {
                    "branch": {
                        "name": body["branchName"],
                        "snapshotId": None,
                        "createdAt": 1788336000001,
                    }
                },
            )
        if path.endswith("/query"):
            return _response(
                request, 200, {"took": 1, "total": 0, "docs": [], "isDocsInline": True}
            )
        if path.endswith("/bulk-upsert") and request.method == "GET":
            return _response(
                request,
                200,
                {
                    "url": "https://storage.example/upload",
                    "type": "application/json",
                    "httpMethod": "PUT",
                    "objectKey": "objects/data.json",
                    "sizeLimitBytes": 10000,
                    "headers": {"x-amz-meta-token": "signed"},
                },
            )
        return _response(request, 202, {"message": "accepted"})

    def transfer_handler(request: httpx.Request) -> httpx.Response:
        transfer_requests.append(request)
        return _response(request, 200, {})

    async def run() -> None:
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(api_handler)) as api_client,
            httpx.AsyncClient(
                transport=httpx.MockTransport(transfer_handler)
            ) as transfer_client,
        ):
            client = LambdaDB(
                project_api_key="secret",
                base_url="https://api.example",
                project_name="project",
                async_client=api_client,
            )
            collection = client.collection("catalog")
            await collection.branches.create_async("experiment")
            await collection.query_async(
                query={"matchAll": {}}, ref=Ref.tag("release-1")
            )
            await collection.docs.bulk_upsert_docs_async(
                docs=[{"id": "1"}], branch="experiment", transfer_client=transfer_client
            )

    asyncio.run(run())

    assert json.loads(api_requests[1].content)["ref"] == {
        "kind": "tag",
        "name": "release-1",
    }
    assert api_requests[2].url.params["branch"] == "experiment"
    assert json.loads(api_requests[3].content)["branch"] == "experiment"
    assert transfer_requests[0].headers["x-amz-meta-token"] == "signed"


def test_sync_async_public_signatures_stay_aligned() -> None:
    client = LambdaDB(project_api_key="secret")
    collection = client.collection("catalog")
    pairs: List[Tuple[Callable[..., Any], Callable[..., Any]]] = [
        (client.collections.create, client.collections.create_async),
        (client.collections.update, client.collections.update_async),
        (client.collections.delete, client.collections.delete_async),
        (collection.query, collection.query_async),
        (collection.docs.list, collection.docs.list_async),
        (collection.docs.list_pages, collection.docs.list_pages_async),
        (collection.docs.iter_all, collection.docs.iter_all_async),
        (collection.docs.upsert, collection.docs.upsert_async),
        (collection.docs.update, collection.docs.update_async),
        (collection.docs.delete, collection.docs.delete_async),
        (collection.docs.fetch, collection.docs.fetch_async),
        (collection.docs.get_bulk_upsert, collection.docs.get_bulk_upsert_async),
        (collection.docs.bulk_upsert, collection.docs.bulk_upsert_async),
        (collection.docs.bulk_upsert_docs, collection.docs.bulk_upsert_docs_async),
        (collection.branches.create, collection.branches.create_async),
        (collection.branches.list, collection.branches.list_async),
        (collection.branches.delete, collection.branches.delete_async),
        (collection.tags.create, collection.tags.create_async),
        (collection.tags.list, collection.tags.list_async),
        (collection.tags.delete, collection.tags.delete_async),
        (collection.aliases.create, collection.aliases.create_async),
        (collection.aliases.list, collection.aliases.list_async),
        (collection.aliases.retarget, collection.aliases.retarget_async),
        (collection.aliases.delete, collection.aliases.delete_async),
    ]
    for sync_method, async_method in pairs:
        assert list(inspect.signature(sync_method).parameters) == list(
            inspect.signature(async_method).parameters
        )
