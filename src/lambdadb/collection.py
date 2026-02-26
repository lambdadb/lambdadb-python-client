"""Collection-scoped API: client.collection(name).docs.* and .query().
Aligns with REST: document operations under .docs, collection-level query at .query().
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Mapping, Optional, Union

from lambdadb import models, utils
from lambdadb.docs import Docs
from lambdadb.collections import Collections
from lambdadb.sdkconfiguration import SDKConfiguration
from lambdadb.types import OptionalNullable, UNSET

# API max page size for list_docs
_LIST_DOCS_MAX_SIZE = 100


def _fetch_bytes_from_presigned_url(
    url: str,
    client: Any,
    timeout_sec: Optional[float],
) -> bytes:
    """GET presigned URL and return response body. Raises RuntimeError on non-2xx."""
    req = client.build_request("GET", url, timeout=timeout_sec)
    res = client.send(req)
    if res.status_code < 200 or res.status_code >= 300:
        raise RuntimeError(
            f"Failed to fetch documents from presigned URL: HTTP {res.status_code} - {res.text}"
        )
    return res.content


async def _fetch_bytes_from_presigned_url_async(
    url: str,
    async_client: Any,
    timeout_sec: Optional[float],
) -> bytes:
    """GET presigned URL (async) and return response body. Raises RuntimeError on non-2xx."""
    req = async_client.build_request("GET", url, timeout=timeout_sec)
    res = await async_client.send(req)
    if res.status_code < 200 or res.status_code >= 300:
        raise RuntimeError(
            f"Failed to fetch documents from presigned URL: HTTP {res.status_code} - {res.text}"
        )
    return res.content


def _resolve_query_response(
    response: models.QueryCollectionResponse,
    client: Any,
    timeout_sec: Optional[float],
) -> models.QueryCollectionResponse:
    """If response has docs_url and not is_docs_inline, fetch from URL and return response with results populated."""
    if response.is_docs_inline or not response.docs_url:
        return response
    body = _fetch_bytes_from_presigned_url(response.docs_url, client, timeout_sec)
    data = json.loads(body)
    if not isinstance(data, list):
        raise RuntimeError("Expected JSON array from docs_url")
    parsed = [models.QueryCollectionDoc.model_validate(item) for item in data]
    return models.QueryCollectionResponse(
        took=response.took,
        total=response.total,
        results=parsed,
        is_docs_inline=response.is_docs_inline,
        max_score=response.max_score,
        docs_url=response.docs_url,
    )


def _resolve_fetch_response(
    response: models.FetchDocsResponse,
    client: Any,
    timeout_sec: Optional[float],
) -> models.FetchDocsResponse:
    """If response has docs_url and not is_docs_inline, fetch from URL and return response with results populated."""
    if response.is_docs_inline or not response.docs_url:
        return response
    body = _fetch_bytes_from_presigned_url(response.docs_url, client, timeout_sec)
    data = json.loads(body)
    if not isinstance(data, list):
        raise RuntimeError("Expected JSON array from docs_url")
    parsed = [models.FetchDocsDoc.model_validate(item) for item in data]
    return models.FetchDocsResponse(
        total=response.total,
        took=response.took,
        results=parsed,
        is_docs_inline=response.is_docs_inline,
        docs_url=response.docs_url,
    )


async def _resolve_query_response_async(
    response: models.QueryCollectionResponse,
    async_client: Any,
    timeout_sec: Optional[float],
) -> models.QueryCollectionResponse:
    if response.is_docs_inline or not response.docs_url:
        return response
    body = await _fetch_bytes_from_presigned_url_async(
        response.docs_url, async_client, timeout_sec
    )
    data = json.loads(body)
    if not isinstance(data, list):
        raise RuntimeError("Expected JSON array from docs_url")
    parsed = [models.QueryCollectionDoc.model_validate(item) for item in data]
    return models.QueryCollectionResponse(
        took=response.took,
        total=response.total,
        results=parsed,
        is_docs_inline=response.is_docs_inline,
        max_score=response.max_score,
        docs_url=response.docs_url,
    )


async def _resolve_fetch_response_async(
    response: models.FetchDocsResponse,
    async_client: Any,
    timeout_sec: Optional[float],
) -> models.FetchDocsResponse:
    if response.is_docs_inline or not response.docs_url:
        return response
    body = await _fetch_bytes_from_presigned_url_async(
        response.docs_url, async_client, timeout_sec
    )
    data = json.loads(body)
    if not isinstance(data, list):
        raise RuntimeError("Expected JSON array from docs_url")
    parsed = [models.FetchDocsDoc.model_validate(item) for item in data]
    return models.FetchDocsResponse(
        total=response.total,
        took=response.took,
        results=parsed,
        is_docs_inline=response.is_docs_inline,
        docs_url=response.docs_url,
    )


def _doc_from_item(item: Any) -> Dict[str, Any]:
    """Normalize list_docs item: return item['doc'] if present else item."""
    if isinstance(item, dict) and "doc" in item:
        return item["doc"]
    return item if isinstance(item, dict) else {}


@dataclass
class RequestOptions:
    """Advanced options for a single request. Pass as options= to any docs method."""

    retries: OptionalNullable[utils.RetryConfig] = field(default_factory=lambda: UNSET)
    server_url: Optional[str] = None
    timeout_ms: Optional[int] = None
    http_headers: Optional[Mapping[str, str]] = None


def _merge_options(
    options: Optional[RequestOptions],
    retries: OptionalNullable[utils.RetryConfig],
    server_url: Optional[str],
    timeout_ms: Optional[int],
    http_headers: Optional[Mapping[str, str]],
) -> tuple:
    """Merge options object with legacy kwargs; options take precedence when set."""
    if options is None:
        return retries, server_url, timeout_ms, http_headers
    r = options.retries if options.retries is not UNSET else retries
    s = options.server_url or server_url
    t = options.timeout_ms or timeout_ms
    h = options.http_headers or http_headers
    return r, s, t, h


class CollectionDocs:
    """Document operations scoped to a single collection.
    Use via client.collection(name).docs (e.g. .list(), .fetch(), .upsert()).
    """

    def __init__(self, docs: Docs, collection_name: str) -> None:
        self._docs = docs
        self._collection_name = collection_name

    def list(
        self,
        *,
        size: Optional[int] = None,
        page_token: Optional[str] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.ListDocsResponse:
        """List documents in this collection. For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return self._docs.list_docs(
            collection_name=self._collection_name,
            size=size,
            page_token=page_token,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    def list_pages(
        self,
        *,
        size: int = 100,
        options: Optional[RequestOptions] = None,
    ) -> Iterator[List[Dict[str, Any]]]:
        """Iterate pages of up to `size` documents each. Aggregates API responses so each
        yielded page has up to `size` documents (LambdaDB may return fewer per request due to payload limits).
        """
        r, s, t, h = _merge_options(options, UNSET, None, None, None)
        page_token: Optional[str] = None
        buffer: List[Dict[str, Any]] = []
        while True:
            need = size - len(buffer)
            if need <= 0:
                page = buffer[:size]
                buffer = buffer[size:]
                yield page
                if not buffer and page_token is None:
                    return
                continue
            resp = self._docs.list_docs(
                collection_name=self._collection_name,
                size=min(need, _LIST_DOCS_MAX_SIZE),
                page_token=page_token,
                retries=r,
                server_url=s,
                timeout_ms=t,
                http_headers=h,
            )
            for item in resp.results:
                buffer.append(_doc_from_item(item))
            page_token = resp.next_page_token
            if len(buffer) >= size or page_token is None:
                page = buffer[:size]
                buffer = buffer[size:]
                yield page
                if page_token is None:
                    if buffer:
                        yield buffer
                    return

    def iter_all(
        self,
        *,
        page_size: int = 100,
        options: Optional[RequestOptions] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Iterate over all documents in the collection. Handles pagination internally."""
        for page in self.list_pages(size=page_size, options=options):
            for doc in page:
                yield doc

    async def list_async(
        self,
        *,
        size: Optional[int] = None,
        page_token: Optional[str] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.ListDocsResponse:
        """List documents in this collection (async). For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return await self._docs.list_docs_async(
            collection_name=self._collection_name,
            size=size,
            page_token=page_token,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    def upsert(
        self,
        *,
        docs: List[Dict[str, Any]],
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Upsert documents into this collection (max payload 6MB). For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return self._docs.upsert(
            collection_name=self._collection_name,
            docs=docs,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    async def upsert_async(
        self,
        *,
        docs: List[Dict[str, Any]],
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Upsert documents into this collection (async). For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return await self._docs.upsert_async(
            collection_name=self._collection_name,
            docs=docs,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    def get_bulk_upsert(
        self,
        *,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.GetBulkUpsertDocsResponse:
        """Request required info to upload documents (bulk). For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return self._docs.get_bulk_upsert(
            collection_name=self._collection_name,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    async def get_bulk_upsert_async(
        self,
        *,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.GetBulkUpsertDocsResponse:
        """Request required info to upload documents (bulk, async). For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return await self._docs.get_bulk_upsert_async(
            collection_name=self._collection_name,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    def bulk_upsert(
        self,
        *,
        object_key: str,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Bulk upsert documents (max object size 200MB). For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return self._docs.bulk_upsert(
            collection_name=self._collection_name,
            object_key=object_key,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    async def bulk_upsert_async(
        self,
        *,
        object_key: str,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Bulk upsert documents (async). For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return await self._docs.bulk_upsert_async(
            collection_name=self._collection_name,
            object_key=object_key,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    def bulk_upsert_docs(
        self,
        *,
        docs: List[Dict[str, Any]],
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """One-step bulk upsert: gets presigned URL, uploads documents to S3, then triggers bulk_upsert.
        Use this instead of calling get_bulk_upsert + manual upload + bulk_upsert. Max payload 200MB."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        info = self._docs.get_bulk_upsert(
            collection_name=self._collection_name,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )
        body = json.dumps(docs).encode("utf-8")
        size_limit = info.size_limit_bytes or 209715200
        if len(body) > size_limit:
            raise ValueError(
                f"Documents payload size {len(body)} bytes exceeds limit {size_limit} bytes"
            )
        config = self._docs.sdk_configuration
        client = config.client
        if client is None:
            raise ValueError("HTTP client is required for bulk_upsert_docs")
        timeout_sec = (t / 1000.0) if t is not None else (config.timeout_ms / 1000.0 if config.timeout_ms else None)
        req = client.build_request(
            "PUT",
            info.url,
            content=body,
            headers={"Content-Type": "application/json"},
            timeout=timeout_sec,
        )
        upload_res = client.send(req)
        if upload_res.status_code < 200 or upload_res.status_code >= 300:
            raise RuntimeError(
                f"Bulk upload to S3 failed: HTTP {upload_res.status_code} - {upload_res.text}"
            )
        return self._docs.bulk_upsert(
            collection_name=self._collection_name,
            object_key=info.object_key,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    async def bulk_upsert_docs_async(
        self,
        *,
        docs: List[Dict[str, Any]],
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """One-step bulk upsert (async): gets presigned URL, uploads documents to S3, then triggers bulk_upsert."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        info = await self._docs.get_bulk_upsert_async(
            collection_name=self._collection_name,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )
        body = json.dumps(docs).encode("utf-8")
        size_limit = info.size_limit_bytes or 209715200
        if len(body) > size_limit:
            raise ValueError(
                f"Documents payload size {len(body)} bytes exceeds limit {size_limit} bytes"
            )
        config = self._docs.sdk_configuration
        async_client = config.async_client
        if async_client is None:
            raise ValueError("Async HTTP client is required for bulk_upsert_docs_async")
        timeout_sec = (t / 1000.0) if t is not None else (config.timeout_ms / 1000.0 if config.timeout_ms else None)
        req = async_client.build_request(
            "PUT",
            info.url,
            content=body,
            headers={"Content-Type": "application/json"},
            timeout=timeout_sec,
        )
        upload_res = await async_client.send(req)
        if upload_res.status_code < 200 or upload_res.status_code >= 300:
            raise RuntimeError(
                f"Bulk upload to S3 failed: HTTP {upload_res.status_code} - {upload_res.text}"
            )
        return await self._docs.bulk_upsert_async(
            collection_name=self._collection_name,
            object_key=info.object_key,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    def update(
        self,
        *,
        docs: List[Dict[str, Any]],
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Update documents (each doc must have 'id'). Max payload 6MB. For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return self._docs.update(
            collection_name=self._collection_name,
            docs=docs,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    async def update_async(
        self,
        *,
        docs: List[Dict[str, Any]],
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Update documents (async). For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return await self._docs.update_async(
            collection_name=self._collection_name,
            docs=docs,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    def delete(
        self,
        *,
        ids: Optional[List[str]] = None,
        query_filter: Optional[Dict[str, Any]] = None,
        filter_: Optional[Dict[str, Any]] = None,
        partition_filter: Optional[
            Union[models.PartitionFilter, models.PartitionFilterTypedDict]
        ] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Delete documents by IDs or query filter. Prefer query_filter= over filter_. For advanced options use options=RequestOptions(...)."""
        effective_filter = query_filter if query_filter is not None else filter_
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return self._docs.delete(
            collection_name=self._collection_name,
            ids=ids,
            filter_=effective_filter,
            partition_filter=partition_filter,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    async def delete_async(
        self,
        *,
        ids: Optional[List[str]] = None,
        query_filter: Optional[Dict[str, Any]] = None,
        filter_: Optional[Dict[str, Any]] = None,
        partition_filter: Optional[
            Union[models.PartitionFilter, models.PartitionFilterTypedDict]
        ] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Delete documents by IDs or query filter (async). Prefer query_filter= over filter_. For advanced options use options=RequestOptions(...)."""
        effective_filter = query_filter if query_filter is not None else filter_
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return await self._docs.delete_async(
            collection_name=self._collection_name,
            ids=ids,
            filter_=effective_filter,
            partition_filter=partition_filter,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    def fetch(
        self,
        *,
        ids: List[str],
        consistent_read: Optional[bool] = False,
        include_vectors: Optional[bool] = False,
        fields: Optional[
            Union[models.FieldsSelectorUnion, models.FieldsSelectorUnionTypedDict]
        ] = None,
        partition_filter: Optional[
            Union[models.PartitionFilter, models.PartitionFilterTypedDict]
        ] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.FetchDocsResponse:
        """Fetch documents by IDs (max 100). When is_docs_inline is false, the SDK automatically fetches documents from the presigned docs_url. For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        response = self._docs.fetch(
            collection_name=self._collection_name,
            ids=ids,
            consistent_read=consistent_read,
            include_vectors=include_vectors,
            fields=fields,
            partition_filter=partition_filter,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )
        client = self._docs.sdk_configuration.client
        if client is not None:
            timeout_sec = (t / 1000.0) if t is not None else (self._docs.sdk_configuration.timeout_ms / 1000.0 if self._docs.sdk_configuration.timeout_ms else None)
            response = _resolve_fetch_response(response, client, timeout_sec)
        return response

    async def fetch_async(
        self,
        *,
        ids: List[str],
        consistent_read: Optional[bool] = False,
        include_vectors: Optional[bool] = False,
        fields: Optional[
            Union[models.FieldsSelectorUnion, models.FieldsSelectorUnionTypedDict]
        ] = None,
        partition_filter: Optional[
            Union[models.PartitionFilter, models.PartitionFilterTypedDict]
        ] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.FetchDocsResponse:
        """Fetch documents by IDs (async). When is_docs_inline is false, the SDK automatically fetches documents from the presigned docs_url. For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        response = await self._docs.fetch_async(
            collection_name=self._collection_name,
            ids=ids,
            consistent_read=consistent_read,
            include_vectors=include_vectors,
            fields=fields,
            partition_filter=partition_filter,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )
        async_client = self._docs.sdk_configuration.async_client
        if async_client is not None:
            timeout_sec = (t / 1000.0) if t is not None else (self._docs.sdk_configuration.timeout_ms / 1000.0 if self._docs.sdk_configuration.timeout_ms else None)
            response = await _resolve_fetch_response_async(response, async_client, timeout_sec)
        return response


class Collection:
    """Handle for a single collection. Use client.collection(name) to obtain.
    - .docs: document operations (list, upsert, fetch, update, delete, bulk_upsert)
    - .query(): search the collection
    """

    def __init__(
        self,
        sdk_configuration: SDKConfiguration,
        collection_name: str,
        parent_ref: Optional[object] = None,
    ) -> None:
        self._sdk_configuration = sdk_configuration
        self._collection_name = collection_name
        self._parent_ref = parent_ref
        self._docs_instance = Docs(sdk_configuration, parent_ref=parent_ref)
        self.docs = CollectionDocs(self._docs_instance, collection_name)
        self._collections = Collections(sdk_configuration, parent_ref=parent_ref)

    def query(
        self,
        *,
        query: Dict[str, Any],
        size: Optional[int] = None,
        consistent_read: Optional[bool] = False,
        include_vectors: Optional[bool] = False,
        sort: Optional[List[Dict[str, Any]]] = None,
        fields: Optional[
            Union[models.FieldsSelectorUnion, models.FieldsSelectorUnionTypedDict]
        ] = None,
        partition_filter: Optional[
            Union[models.PartitionFilter, models.PartitionFilterTypedDict]
        ] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.QueryCollectionResponse:
        """Search this collection with a query (vector/keyword/hybrid). When is_docs_inline is false, the SDK automatically fetches documents from the presigned docs_url. For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        response = self._collections.query(
            collection_name=self._collection_name,
            query=query,
            size=size,
            consistent_read=consistent_read,
            include_vectors=include_vectors,
            sort=sort,
            fields=fields,
            partition_filter=partition_filter,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )
        client = self._sdk_configuration.client
        if client is not None:
            timeout_sec = (t / 1000.0) if t is not None else (self._sdk_configuration.timeout_ms / 1000.0 if self._sdk_configuration.timeout_ms else None)
            response = _resolve_query_response(response, client, timeout_sec)
        return response

    async def query_async(
        self,
        *,
        query: Dict[str, Any],
        size: Optional[int] = None,
        consistent_read: Optional[bool] = False,
        include_vectors: Optional[bool] = False,
        sort: Optional[List[Dict[str, Any]]] = None,
        fields: Optional[
            Union[models.FieldsSelectorUnion, models.FieldsSelectorUnionTypedDict]
        ] = None,
        partition_filter: Optional[
            Union[models.PartitionFilter, models.PartitionFilterTypedDict]
        ] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.QueryCollectionResponse:
        """Search this collection (async). When is_docs_inline is false, the SDK automatically fetches documents from the presigned docs_url. For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        response = await self._collections.query_async(
            collection_name=self._collection_name,
            query=query,
            size=size,
            consistent_read=consistent_read,
            include_vectors=include_vectors,
            sort=sort,
            fields=fields,
            partition_filter=partition_filter,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )
        async_client = self._sdk_configuration.async_client
        if async_client is not None:
            timeout_sec = (t / 1000.0) if t is not None else (self._sdk_configuration.timeout_ms / 1000.0 if self._sdk_configuration.timeout_ms else None)
            response = await _resolve_query_response_async(response, async_client, timeout_sec)
        return response
