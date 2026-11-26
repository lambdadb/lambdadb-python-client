"""Branch rollback and sorted or consistent document listing at the wire boundary."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

import httpx
import pytest
from pydantic import ValidationError

from lambdadb import LambdaDB, Ref, RequestOptions, errors, models, utils

BASE = "/projects/project/collections/catalog"
ROLLBACK_PATH = f"{BASE}/branches/main/rollback"
SNAPSHOT = {"snapshotId": "rollback-snapshot-id", "snapshotCommittedAt": 1788336000000}
Handler = Callable[[httpx.Request], httpx.Response]
RETRIES = utils.RetryConfig("backoff", utils.BackoffStrategy(1, 1, 1.0, 1000), True)


def _run(handler: Handler, call: Callable[[Any], Any], *, async_mode: bool, **sdk: Any) -> Any:
    """Call ``call(collection)`` on a client whose transport is ``handler``."""
    options = {"project_api_key": "secret", "base_url": "https://api.example", "project_name": "project", **sdk}
    if not async_mode:
        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            return call(LambdaDB(client=http, **options).collection("catalog"))

    async def run() -> Any:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await call(LambdaDB(async_client=http, **options).collection("catalog"))

    return asyncio.run(run())


def _rollback(async_mode: bool, **kwargs: Any) -> Callable[[Any], Any]:
    def call(collection: Any) -> Any:
        method = collection.branches.rollback_async if async_mode else collection.branches.rollback
        return method("main", **kwargs)

    return call


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("head", [SNAPSHOT, None])
def test_rollback_posts_the_tag_and_parses_the_nullable_head(async_mode: bool, head: Any) -> None:
    requests: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"branchId": "main-branch-id", "headSnapshot": head})

    result = _run(handler, _rollback(async_mode, tag="release-42"), async_mode=async_mode)

    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert requests[0].url.path == ROLLBACK_PATH
    assert json.loads(requests[0].content) == {"tag": "release-42"}
    assert isinstance(result, models.RollbackBranchResponse)
    assert result.branch_id == "main-branch-id"
    if head is None:
        assert result.head_snapshot is None
    else:
        assert result.head_snapshot.snapshot_id == "rollback-snapshot-id"
        assert result.head_snapshot.snapshot_committed_at_dt == datetime.fromtimestamp(
            1788336000, tz=timezone.utc
        )


def test_rollback_response_requires_head_snapshot_to_be_present() -> None:
    models.RollbackBranchResponse.model_validate({"branchId": "b", "headSnapshot": None})
    with pytest.raises(ValidationError, match="headSnapshot"):
        models.RollbackBranchResponse.model_validate({"branchId": "b"})

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"branchId": "main-branch-id"})

    with pytest.raises(errors.ResponseValidationError):
        _run(handler, _rollback(False, tag="release-42"), async_mode=False)


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "status,error",
    [
        (409, errors.CatalogConflictError),
        (429, errors.TooManyRequestsError),
        (503, errors.ServiceUnavailableError),
        (504, errors.GatewayTimeoutError),
    ],
)
@pytest.mark.parametrize("configured", ["default", "client", "options"])
def test_rollback_is_never_retried(async_mode: bool, status: int, error: type, configured: str) -> None:
    requests: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) > 1:
            return httpx.Response(200, json={"branchId": "main-branch-id", "headSnapshot": None})
        return httpx.Response(status, json={"message": "try later"}, headers={"Retry-After": "0"})

    kwargs: Dict[str, Any] = {"tag": "release-42"}
    sdk: Dict[str, Any] = {}
    if configured == "options":
        kwargs["options"] = RequestOptions(retries=RETRIES)
    elif configured == "client":
        sdk["retry_config"] = RETRIES

    with pytest.raises(error):
        _run(handler, _rollback(async_mode, **kwargs), async_mode=async_mode, **sdk)
    assert len(requests) == 1


@pytest.mark.parametrize("async_mode", [False, True])
def test_rollback_does_not_retry_connection_errors(async_mode: bool) -> None:
    requests: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise httpx.ConnectError("connection reset", request=request)

    with pytest.raises(httpx.ConnectError):
        _run(handler, _rollback(async_mode, tag="release-42"), async_mode=async_mode)
    assert len(requests) == 1


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "branch,tag",
    [("main", "x"), ("main", "has space"), ("main", "a" * 53), ("no/slash", "release-42"), ("m", "release-42")],
)
def test_rollback_validates_names_before_any_request(async_mode: bool, branch: str, tag: str) -> None:
    requests: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"branchId": "b", "headSnapshot": None})

    def call(collection: Any) -> Any:
        method = collection.branches.rollback_async if async_mode else collection.branches.rollback
        return method(branch, tag=tag)

    with pytest.raises(ValidationError):
        _run(handler, call, async_mode=async_mode)
    assert requests == []


def test_rollback_request_body_is_strict() -> None:
    assert models.RollbackBranchRequestBody(tag="release-42").model_dump(by_alias=True) == {"tag": "release-42"}
    with pytest.raises(ValidationError):
        models.RollbackBranchRequestBody.model_validate({"tag": "release-42", "asOf": 1})
    with pytest.raises(ValidationError):
        models.RollbackBranchRequestBody.model_validate({})


def _list_handler(requests: List[httpx.Request], pages: int = 1, per_page: int = 1) -> Handler:
    """Serve ``pages`` pages of ``per_page`` documents, chained by page tokens."""

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        index = len(requests) - 1
        body: Dict[str, Any] = {
            "total": per_page,
            "docs": [{"collection": "catalog", "doc": {"id": f"{index}-{i}"}} for i in range(per_page)],
            "isDocsInline": True,
        }
        if index + 1 < pages:
            body["nextPageToken"] = f"token-{index + 1}"
        return httpx.Response(200, json=body)

    return handler


def _list(async_mode: bool, **kwargs: Any) -> Callable[[Any], Any]:
    def call(collection: Any) -> Any:
        method = collection.docs.list_async if async_mode else collection.docs.list
        return method(**kwargs)

    return call


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"sort": [{"category": "asc"}, {"price": "desc"}]}, {"sort": [{"category": "asc"}, {"price": "desc"}]}),
        ({"consistent_read": True}, {"consistentRead": True}),
        (
            {"sort": [{"category": "asc"}], "consistent_read": True, "ref": Ref.alias("production-read")},
            {"sort": [{"category": "asc"}], "consistentRead": True, "ref": {"kind": "alias", "name": "production-read"}},
        ),
        ({"sort": [{"category": "desc"}], "ref": Ref.tag("release-1")}, {"sort": [{"category": "desc"}], "ref": {"kind": "tag", "name": "release-1"}}),
        ({"filter_": {"term": {"active": True}}}, {"filter": {"term": {"active": True}}}),
    ],
)
def test_sort_and_consistent_read_use_the_extended_list(async_mode: bool, kwargs: Dict[str, Any], expected: Dict[str, Any]) -> None:
    requests: List[httpx.Request] = []
    _run(_list_handler(requests), _list(async_mode, size=10, **kwargs), async_mode=async_mode)

    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert requests[0].url.path == f"{BASE}/docs/list"
    # An unset sort and an unset or false consistent_read are not sent.
    assert json.loads(requests[0].content) == {"size": 10, "includeVectors": False, **expected}


@pytest.mark.parametrize("async_mode", [False, True])
def test_list_without_extended_options_still_uses_get(async_mode: bool) -> None:
    requests: List[httpx.Request] = []
    _run(_list_handler(requests), _list(async_mode, sort=None, consistent_read=False), async_mode=async_mode)

    assert [request.method for request in requests] == ["GET"]
    assert "consistentRead" not in requests[0].url.params


@pytest.mark.parametrize("async_mode", [False, True])
def test_consistent_list_rejects_a_tag_ref_before_any_request(async_mode: bool) -> None:
    requests: List[httpx.Request] = []
    with pytest.raises(ValueError, match="not a tag"):
        _run(
            _list_handler(requests),
            _list(async_mode, consistent_read=True, ref=Ref.tag("release-1")),
            async_mode=async_mode,
        )
    assert requests == []
    with pytest.raises(ValidationError, match="not a tag"):
        models.ListDocsExtendedRequestBody(consistent_read=True, ref=Ref.tag("release-1"))


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "sort",
    [
        [],
        [{"a": "asc"}, {"b": "asc"}, {"c": "asc"}, {"d": "asc"}, {"e": "asc"}],
        [{"category": "asc", "price": "desc"}],
        [{}],
        [{"category": "ASC"}],
        [{"category": "ascending"}],
        [{" ": "asc"}],
        [{"nested.": "asc"}],
    ],
)
def test_invalid_sort_is_rejected_before_any_request(async_mode: bool, sort: Any) -> None:
    requests: List[httpx.Request] = []
    with pytest.raises(ValidationError):
        _run(_list_handler(requests), _list(async_mode, sort=sort), async_mode=async_mode)
    assert requests == []


def test_valid_sort_shapes_are_accepted() -> None:
    sort = [{"category": "asc"}, {"price": "desc"}, {"meta.createdAt": "asc"}, {"rank": "desc"}]
    body = models.ListDocsExtendedRequestBody(sort=sort)
    assert body.model_dump(by_alias=True) == {"includeVectors": False, "sort": sort}


@pytest.mark.parametrize("async_mode", [False, True])
def test_list_pages_repeat_the_same_request_on_every_page(async_mode: bool) -> None:
    requests: List[httpx.Request] = []
    # The server returns fewer documents than requested; the requested size must not shrink.
    handler = _list_handler(requests, pages=3, per_page=2)
    args: Dict[str, Any] = {
        "size": 3,
        "sort": [{"category": "asc"}],
        "consistent_read": True,
        "ref": Ref.branch("experiment"),
    }

    def call(collection: Any) -> Any:
        if not async_mode:
            return list(collection.docs.list_pages(**args))

        async def collect() -> Any:
            return [page async for page in collection.docs.list_pages_async(**args)]

        return collect()

    pages = _run(handler, call, async_mode=async_mode)

    assert [len(page) for page in pages] == [3, 3]
    bodies = [json.loads(request.content) for request in requests]
    assert [body.pop("pageToken", None) for body in bodies] == [None, "token-1", "token-2"]
    assert bodies == [
        {
            "size": 3,
            "includeVectors": False,
            "sort": [{"category": "asc"}],
            "consistentRead": True,
            "ref": {"kind": "branch", "name": "experiment"},
        }
    ] * 3
