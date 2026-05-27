"""
Minimal unit tests for SDK public API surface (no network, no API key).
Run: poetry run pytest tests/ -v
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest


def test_runtime_version_matches_project_metadata() -> None:
    """Runtime version constants match pyproject metadata."""
    from lambdadb import __version__

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    version_line = next(
        line for line in pyproject.read_text(encoding="utf-8").splitlines()
        if line.startswith("version = ")
    )
    project_version = version_line.split("=", 1)[1].strip().strip('"')

    assert __version__ == project_version


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


def test_sdk_close_closes_both_owned_clients() -> None:
    """close() closes both sync and async clients created by the SDK."""
    from lambdadb import LambdaDB

    client = LambdaDB(project_api_key="test-key")
    assert client.sdk_configuration.client is not None
    assert client.sdk_configuration.async_client is not None

    client.close()

    assert client.sdk_configuration.client is None
    assert client.sdk_configuration.async_client is None


def test_sdk_aclose_closes_both_owned_clients() -> None:
    """aclose() closes both sync and async clients created by the SDK."""
    from lambdadb import LambdaDB

    async def run() -> None:
        client = LambdaDB(project_api_key="test-key")
        assert client.sdk_configuration.client is not None
        assert client.sdk_configuration.async_client is not None

        await client.aclose()

        assert client.sdk_configuration.client is None
        assert client.sdk_configuration.async_client is None

    asyncio.run(run())


def test_sdk_use_after_close_raises_clear_error() -> None:
    """Using the SDK after close() raises a clear client-closed error."""
    from lambdadb import LambdaDB

    client = LambdaDB(project_api_key="test-key")
    client.close()

    with pytest.raises(ValueError, match="HTTP client is not available"):
        client.collections.list()


def test_sdk_use_after_aclose_raises_clear_error() -> None:
    """Using the SDK after aclose() raises a clear client-closed error."""
    from lambdadb import LambdaDB

    async def run() -> None:
        client = LambdaDB(project_api_key="test-key")
        await client.aclose()

        with pytest.raises(ValueError, match="HTTP client is not available"):
            await client.collections.list_async()

    asyncio.run(run())


def test_sdkconfiguration_defaults_are_valid() -> None:
    """SDKConfiguration dataclass defaults use concrete runtime values."""
    from lambdadb.sdkconfiguration import SDKConfiguration
    from lambdadb.types import UNSET

    class DummyLogger:
        def debug(self, *_args, **_kwargs) -> None:
            return None

    config = SDKConfiguration(
        client=None,
        client_supplied=True,
        async_client=None,
        async_client_supplied=True,
        debug_logger=DummyLogger(),
    )

    assert config.server_defaults == []
    assert config.retry_config is UNSET


def test_retry_retries_read_error_when_connection_retries_enabled() -> None:
    from lambdadb.utils.retries import BackoffStrategy, Retries, RetryConfig, retry

    attempts = 0

    def flaky() -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadError("bad file descriptor")
        return httpx.Response(202)

    result = retry(
        flaky,
        Retries(
            RetryConfig("backoff", BackoffStrategy(0, 0, 1, 1000), True),
            [],
        ),
    )

    assert result.status_code == 202
    assert attempts == 2


def test_retry_does_not_retry_read_error_when_connection_retries_disabled() -> None:
    from lambdadb.utils.retries import BackoffStrategy, Retries, RetryConfig, retry

    attempts = 0

    def flaky() -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadError("bad file descriptor")

    with pytest.raises(httpx.ReadError):
        retry(
            flaky,
            Retries(
                RetryConfig("backoff", BackoffStrategy(0, 0, 1, 1000), False),
                [],
            ),
        )

    assert attempts == 1


def test_retry_does_not_retry_protocol_errors() -> None:
    from lambdadb.utils.retries import BackoffStrategy, Retries, RetryConfig, retry

    attempts = 0

    def invalid_request() -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.UnsupportedProtocol("missing URL scheme")

    with pytest.raises(httpx.UnsupportedProtocol):
        retry(
            invalid_request,
            Retries(
                RetryConfig("backoff", BackoffStrategy(0, 0, 1, 1000), True),
                [],
            ),
        )

    assert attempts == 1


def test_retry_async_retries_read_error_when_connection_retries_enabled() -> None:
    from lambdadb.utils.retries import (
        BackoffStrategy,
        Retries,
        RetryConfig,
        retry_async,
    )

    async def run() -> None:
        attempts = 0

        async def flaky() -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise httpx.ReadError("bad file descriptor")
            return httpx.Response(202)

        result = await retry_async(
            flaky,
            Retries(
                RetryConfig("backoff", BackoffStrategy(0, 0, 1, 1000), True),
                [],
            ),
        )

        assert result.status_code == 202
        assert attempts == 2

    asyncio.run(run())


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


def test_managed_embedding_index_config_serializes_with_api_aliases() -> None:
    """Managed embedding vector configs parse and dump using API field names."""
    from lambdadb.models import (
        CreateCollectionRequest,
        EmbeddingConfig,
        IndexConfigsVector,
        Provider,
        Similarity,
        TypeVector,
    )

    req = CreateCollectionRequest(
        collection_name="articles",
        index_configs={
            "bodyEmbedding": IndexConfigsVector(
                type=TypeVector.VECTOR,
                managed_embedding=True,
                embedding=EmbeddingConfig(
                    provider=Provider.OPENAI,
                    model="text-embedding-3-small",
                    source_field="body",
                ),
            )
        },
    )

    assert req.index_configs is not None
    vector_config = req.index_configs["bodyEmbedding"]
    assert isinstance(vector_config, IndexConfigsVector)
    assert vector_config.managed_embedding is True
    assert vector_config.embedding is not None
    assert vector_config.embedding.similarity is Similarity.COSINE

    assert req.model_dump(by_alias=True)["indexConfigs"]["bodyEmbedding"] == {
        "type": "vector",
        "managedEmbedding": True,
        "embedding": {
            "provider": "openai",
            "model": "text-embedding-3-small",
            "sourceField": "body",
            "similarity": "cosine",
        },
    }


def test_managed_embedding_index_config_accepts_plain_dict_input() -> None:
    """Managed embedding vector configs also work as plain request dictionaries."""
    from lambdadb.models import CreateCollectionRequest, IndexConfigsVector

    req = CreateCollectionRequest.model_validate(
        {
            "collectionName": "articles",
            "indexConfigs": {
                "bodyEmbedding": {
                    "type": "vector",
                    "managedEmbedding": True,
                    "embedding": {
                        "provider": "openai",
                        "model": "text-embedding-3-small",
                        "sourceField": "body",
                    },
                }
            },
        }
    )

    assert req.index_configs is not None
    assert isinstance(req.index_configs["bodyEmbedding"], IndexConfigsVector)
    assert req.model_dump(by_alias=True, mode="json")["indexConfigs"][
        "bodyEmbedding"
    ] == {
        "type": "vector",
        "managedEmbedding": True,
        "embedding": {
            "provider": "openai",
            "model": "text-embedding-3-small",
            "sourceField": "body",
            "similarity": "cosine",
        },
    }


def test_collection_response_parses_managed_embedding_index_config() -> None:
    """CollectionResponse accepts managed embedding metadata returned by the API."""
    from lambdadb.models import CollectionResponse, IndexConfigsVector

    resp = CollectionResponse.model_validate(
        {
            "projectName": "p",
            "collectionName": "c",
            "indexConfigs": {
                "bodyEmbedding": {
                    "type": "vector",
                    "managedEmbedding": True,
                    "embedding": {
                        "provider": "openai",
                        "model": "text-embedding-3-small",
                        "sourceField": "body",
                        "dimensions": 1536,
                        "similarity": "cosine",
                    },
                }
            },
            "numPartitions": 1,
            "numDocs": 0,
            "collectionStatus": "ACTIVE",
            "createdAt": 1000000,
            "updatedAt": 2000000,
            "dataUpdatedAt": 3000000,
        }
    )

    vector_config = resp.index_configs["bodyEmbedding"]
    assert isinstance(vector_config, IndexConfigsVector)
    assert vector_config.managed_embedding is True
    assert vector_config.embedding is not None
    assert vector_config.embedding.source_field == "body"
    assert vector_config.embedding.dimensions == 1536
    assert (
        resp.model_dump(by_alias=True)["indexConfigs"]["bodyEmbedding"]["embedding"][
            "sourceField"
        ]
        == "body"
    )


def test_unmanaged_vector_index_config_requires_dimensions_and_defaults_similarity() -> None:
    """Unmanaged vector configs keep existing dimensions + default similarity behavior."""
    from lambdadb.models import CreateCollectionRequest, IndexConfigsVector, Similarity

    req = CreateCollectionRequest.model_validate(
        {
            "collectionName": "articles",
            "indexConfigs": {
                "bodyEmbedding": {
                    "type": "vector",
                    "dimensions": 1536,
                }
            },
        }
    )

    assert req.index_configs is not None
    vector_config = req.index_configs["bodyEmbedding"]
    assert isinstance(vector_config, IndexConfigsVector)
    assert vector_config.managed_embedding is None
    assert vector_config.dimensions == 1536
    assert vector_config.similarity is Similarity.COSINE


def test_vector_index_config_rejects_embedding_without_managed_embedding() -> None:
    """embedding requires managedEmbedding=true."""
    from pydantic import ValidationError
    from lambdadb.models import CreateCollectionRequest

    with pytest.raises(ValidationError, match="managedEmbedding=true is required"):
        CreateCollectionRequest.model_validate(
            {
                "collectionName": "articles",
                "indexConfigs": {
                    "bodyEmbedding": {
                        "type": "vector",
                        "embedding": {
                            "provider": "openai",
                            "model": "text-embedding-3-small",
                            "sourceField": "body",
                        },
                    }
                },
            }
        )


def test_vector_index_config_rejects_managed_embedding_without_embedding() -> None:
    """embedding is required when managedEmbedding=true."""
    from pydantic import ValidationError
    from lambdadb.models import CreateCollectionRequest

    with pytest.raises(ValidationError, match="embedding is required"):
        CreateCollectionRequest.model_validate(
            {
                "collectionName": "articles",
                "indexConfigs": {
                    "bodyEmbedding": {
                        "type": "vector",
                        "managedEmbedding": True,
                    }
                },
            }
        )


def test_vector_index_config_rejects_top_level_managed_vector_fields() -> None:
    """Managed embedding vectors cannot use top-level vector parameters."""
    from pydantic import ValidationError
    from lambdadb.models import CreateCollectionRequest

    with pytest.raises(ValidationError, match="Top-level dimensions are not allowed"):
        CreateCollectionRequest.model_validate(
            {
                "collectionName": "articles",
                "indexConfigs": {
                    "bodyEmbedding": {
                        "type": "vector",
                        "managedEmbedding": True,
                        "dimensions": 1536,
                        "embedding": {
                            "provider": "openai",
                            "model": "text-embedding-3-small",
                            "sourceField": "body",
                        },
                    }
                },
            }
        )

    with pytest.raises(ValidationError, match="Top-level similarity is not allowed"):
        CreateCollectionRequest.model_validate(
            {
                "collectionName": "articles",
                "indexConfigs": {
                    "bodyEmbedding": {
                        "type": "vector",
                        "managedEmbedding": True,
                        "similarity": "cosine",
                        "embedding": {
                            "provider": "openai",
                            "model": "text-embedding-3-small",
                            "sourceField": "body",
                        },
                    }
                },
            }
        )


def test_vector_index_config_rejects_unmanaged_embedding_fields() -> None:
    """Unmanaged vectors require dimensions and cannot include embedding."""
    from pydantic import ValidationError
    from lambdadb.models import CreateCollectionRequest

    with pytest.raises(ValidationError, match="embedding is not allowed"):
        CreateCollectionRequest.model_validate(
            {
                "collectionName": "articles",
                "indexConfigs": {
                    "bodyEmbedding": {
                        "type": "vector",
                        "managedEmbedding": False,
                        "dimensions": 1536,
                        "embedding": {
                            "provider": "openai",
                            "model": "text-embedding-3-small",
                            "sourceField": "body",
                        },
                    }
                },
            }
        )

    with pytest.raises(ValidationError, match="Dimensions is required field"):
        CreateCollectionRequest.model_validate(
            {
                "collectionName": "articles",
                "indexConfigs": {
                    "bodyEmbedding": {
                        "type": "vector",
                        "managedEmbedding": False,
                    }
                },
            }
        )

    with pytest.raises(ValidationError, match="Dimensions must be between 1 and 4096"):
        CreateCollectionRequest.model_validate(
            {
                "collectionName": "articles",
                "indexConfigs": {
                    "bodyEmbedding": {
                        "type": "vector",
                        "managedEmbedding": False,
                        "dimensions": 4097,
                    }
                },
            }
        )

    with pytest.raises(ValidationError, match="Dimensions must be between 1 and 4096"):
        CreateCollectionRequest.model_validate(
            {
                "collectionName": "articles",
                "indexConfigs": {
                    "bodyEmbedding": {
                        "type": "vector",
                        "managedEmbedding": False,
                        "dimensions": 0,
                    }
                },
            }
        )


def test_get_collection_response_model_dump_preserves_values() -> None:
    """GetCollectionResponse.model_dump keeps parsed collection values."""
    from lambdadb.models import GetCollectionResponse

    resp = GetCollectionResponse.model_validate(
        {
            "collection": {
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
        }
    )

    assert resp.collection.project_name == "p"
    assert resp.collection.collection_name == "c"
    assert resp.model_dump()["collection"]["projectName"] == "p"
    assert resp.model_dump()["collection"]["collectionName"] == "c"
    assert resp.model_dump(by_alias=True)["collection"]["projectName"] == "p"


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


def test_list_docs_extended_request_body_serializes_api_aliases() -> None:
    """Extended list body uses API aliases for filter, fields, partitionFilter, and includeVectors."""
    from lambdadb.models import ListDocsExtendedRequestBody

    body = ListDocsExtendedRequestBody.model_validate(
        {
            "size": 10,
            "pageToken": "page-1",
            "filter": {"queryString": {"query": "category:docs"}},
            "partitionFilter": {"field": "tenant", "in": ["acme"]},
            "fields": {"include": ["id", "title"]},
            "includeVectors": True,
        }
    )

    assert body.model_dump(by_alias=True, mode="json", exclude_none=True) == {
        "size": 10,
        "pageToken": "page-1",
        "filter": {"queryString": {"query": "category:docs"}},
        "partitionFilter": {"field": "tenant", "in": ["acme"]},
        "fields": {"include": ["id", "title"]},
        "includeVectors": True,
    }
