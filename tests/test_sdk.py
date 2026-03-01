"""
Minimal unit tests for SDK public API surface (no network, no API key).
Run: poetry run pytest tests/ -v
"""
from __future__ import annotations

import pytest


def test_imports() -> None:
    """Core imports work."""
    from lambdadb import LambdaDB
    from lambdadb import (
        RequestOptions,
        ListDocsResponse,
        QueryCollectionResponse,
        FetchDocsResponse,
    )
    from lambdadb.collection import Collection, CollectionDocs, RequestOptions as RO

    assert LambdaDB is not None
    assert RequestOptions is RO
    assert ListDocsResponse is not None
    assert QueryCollectionResponse is not None
    assert FetchDocsResponse is not None
    assert Collection is not None
    assert CollectionDocs is not None


def test_client_collection_docs_has_convenience_methods() -> None:
    """CollectionDocs exposes list_pages, iter_all, bulk_upsert_docs."""
    from lambdadb import LambdaDB

    # Minimal client (no real requests in this test)
    client = LambdaDB(project_api_key="test-key")
    coll = client.collection("test_coll")
    docs = coll.docs

    assert hasattr(docs, "list_pages")
    assert hasattr(docs, "iter_all")
    assert hasattr(docs, "bulk_upsert_docs")
    assert hasattr(docs, "bulk_upsert_docs_async")
    assert callable(docs.list_pages)
    assert callable(docs.iter_all)
    assert callable(docs.bulk_upsert_docs)


def test_collections_has_list_pages_and_iter_all() -> None:
    """Collections exposes list_pages, iter_all and async variants."""
    from lambdadb import LambdaDB

    client = LambdaDB(project_api_key="test-key")
    collections = client.collections

    assert hasattr(collections, "list_pages")
    assert hasattr(collections, "list_pages_async")
    assert hasattr(collections, "iter_all")
    assert hasattr(collections, "iter_all_async")
    assert callable(collections.list_pages)
    assert callable(collections.iter_all)


def test_request_options_instantiation() -> None:
    """RequestOptions can be constructed with optional params."""
    from lambdadb import RequestOptions

    opts = RequestOptions(timeout_ms=5000)
    assert opts.timeout_ms == 5000

    opts2 = RequestOptions()
    assert opts2 is not None


def test_collection_response_has_datetime_properties() -> None:
    """CollectionResponse has created_at_dt, updated_at_dt, data_updated_at_dt."""
    from datetime import datetime, timezone
    from lambdadb.models import CollectionResponse

    # Build minimal valid response (API shape with aliases)
    data = {
        "projectName": "p",
        "collectionName": "c",
        "indexConfigs": {"f": {"type": "keyword"}},
        "numPartitions": 1,
        "numDocs": 0,
        "collectionStatus": "ACTIVE",
        "createdAt": 1000000,
        "updatedAt": 2000000,
        "dataUpdatedAt": 3000000,
    }
    resp = CollectionResponse.model_validate(data)

    assert hasattr(resp, "created_at_dt")
    assert hasattr(resp, "updated_at_dt")
    assert hasattr(resp, "data_updated_at_dt")

    assert isinstance(resp.created_at_dt, datetime)
    assert isinstance(resp.updated_at_dt, datetime)
    assert isinstance(resp.data_updated_at_dt, datetime)

    assert resp.created_at_dt.tzinfo is timezone.utc
    assert resp.created_at_dt == datetime.fromtimestamp(1000000, tz=timezone.utc)


def test_list_collections_response_has_next_page_token() -> None:
    """ListCollectionsResponse has collections and next_page_token."""
    from lambdadb.models import ListCollectionsResponse

    data = {"collections": [], "nextPageToken": None}
    resp = ListCollectionsResponse.model_validate(data)
    assert hasattr(resp, "collections")
    assert hasattr(resp, "next_page_token")
    assert resp.collections == []
    assert resp.next_page_token is None


def test_query_and_fetch_response_has_results_and_documents() -> None:
    """QueryCollectionResponse and FetchDocsResponse have .results and .documents."""
    from lambdadb.models import QueryCollectionResponse, FetchDocsResponse

    q = QueryCollectionResponse.model_validate(
        {"took": 0, "total": 0, "docs": [], "isDocsInline": True}
    )
    assert hasattr(q, "results")
    assert hasattr(q, "documents")
    assert q.results == []
    assert q.documents == []

    f = FetchDocsResponse.model_validate(
        {"total": 0, "took": 0, "docs": [], "isDocsInline": True}
    )
    assert hasattr(f, "results")
    assert hasattr(f, "documents")
    assert f.results == []
    assert f.documents == []


def test_list_docs_response_has_is_docs_inline_and_docs_url() -> None:
    """ListDocsResponse has .results, .is_docs_inline, and .docs_url (like query/fetch)."""
    from lambdadb.models import ListDocsResponse

    resp = ListDocsResponse.model_validate(
        {"total": 0, "docs": [], "isDocsInline": True}
    )
    assert hasattr(resp, "results")
    assert hasattr(resp, "is_docs_inline")
    assert hasattr(resp, "docs_url")
    assert resp.results == []
    assert resp.is_docs_inline is True
    assert resp.docs_url is None

    resp_with_url = ListDocsResponse.model_validate(
        {"total": 2, "docs": [], "isDocsInline": False, "docsUrl": "https://example.com/docs.json"}
    )
    assert resp_with_url.is_docs_inline is False
    assert resp_with_url.docs_url == "https://example.com/docs.json"
