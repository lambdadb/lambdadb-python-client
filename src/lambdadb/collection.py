"""Collection-scoped API: client.collection(name).docs.* and .query().
Aligns with REST: document operations under .docs, collection-level query at .query().
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, Iterator, List, Mapping, Optional, Union

from lambdadb import models, utils
from lambdadb.docs import Docs
from lambdadb.httpclient import AsyncHttpClient, HttpClient
from lambdadb.requestoptions import RequestOptions, merge_options as _merge_options
from lambdadb.collections import Collections
from lambdadb.sdkconfiguration import SDKConfiguration
from lambdadb.types import OptionalNullable, UNSET
from lambdadb.versioning import Aliases, Branches, CollectionVersioning, Tags

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


def _resolve_list_docs_response(
    response: models.ListDocsResponse,
    client: Any,
    timeout_sec: Optional[float],
) -> models.ListDocsResponse:
    """If response has docs_url and not is_docs_inline, fetch from URL and return response with results populated."""
    if response.is_docs_inline or not response.docs_url:
        return response
    body = _fetch_bytes_from_presigned_url(response.docs_url, client, timeout_sec)
    data = json.loads(body)
    if not isinstance(data, list):
        raise RuntimeError("Expected JSON array from docs_url")
    return models.ListDocsResponse(
        total=response.total,
        results=data,
        next_page_token=response.next_page_token,
        is_docs_inline=response.is_docs_inline,
        docs_url=response.docs_url,
    )


async def _resolve_list_docs_response_async(
    response: models.ListDocsResponse,
    async_client: Any,
    timeout_sec: Optional[float],
) -> models.ListDocsResponse:
    if response.is_docs_inline or not response.docs_url:
        return response
    body = await _fetch_bytes_from_presigned_url_async(
        response.docs_url, async_client, timeout_sec
    )
    data = json.loads(body)
    if not isinstance(data, list):
        raise RuntimeError("Expected JSON array from docs_url")
    return models.ListDocsResponse(
        total=response.total,
        results=data,
        next_page_token=response.next_page_token,
        is_docs_inline=response.is_docs_inline,
        docs_url=response.docs_url,
    )


def _doc_from_item(item: Any) -> Dict[str, Any]:
    """Normalize list_docs item: return item['doc'] if present else item."""
    if isinstance(item, dict) and "doc" in item:
        return item["doc"]
    return item if isinstance(item, dict) else {}


def _bulk_upload_headers(info: models.GetBulkUpsertDocsResponse) -> Dict[str, str]:
    """Return signed upload headers plus the contract-required content type."""
    headers = dict(info.headers)
    if not any(name.lower() == "content-type" for name in headers):
        headers["Content-Type"] = info.type.value
    return headers


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
        filter_: Optional[Dict[str, Any]] = None,
        partition_filter: Optional[
            Union[models.PartitionFilter, models.PartitionFilterTypedDict]
        ] = None,
        fields: Optional[
            Union[models.FieldsSelectorUnion, models.FieldsSelectorUnionTypedDict]
        ] = None,
        include_vectors: Optional[bool] = False,
        ref: Optional[Union[models.Ref, Mapping[str, Any]]] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.ListDocsResponse:
        """List documents, optionally from a Branch, Tag, or Alias ``ref``.

        A missing ref raises ``ResourceNotFoundError``. A dangling Alias raises
        ``BadRequestError`` until it is retargeted to an existing Branch or Tag.
        """
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        if filter_ is not None or partition_filter is not None or fields is not None:
            response = self._docs.list_docs_extended(
                collection_name=self._collection_name,
                size=size,
                page_token=page_token,
                filter_=filter_,
                partition_filter=partition_filter,
                fields=fields,
                include_vectors=include_vectors,
                ref=ref,
                retries=r,
                server_url=s,
                timeout_ms=t,
                http_headers=h,
            )
        else:
            response = self._docs.list_docs(
                collection_name=self._collection_name,
                size=size,
                page_token=page_token,
                include_vectors=include_vectors,
                ref=ref,
                retries=r,
                server_url=s,
                timeout_ms=t,
                http_headers=h,
            )
        client = self._docs.sdk_configuration.client
        if client is not None:
            timeout_sec = (t / 1000.0) if t is not None else (self._docs.sdk_configuration.timeout_ms / 1000.0 if self._docs.sdk_configuration.timeout_ms else None)
            response = _resolve_list_docs_response(response, client, timeout_sec)
        return response

    def list_pages(
        self,
        *,
        size: int = 100,
        page_token: Optional[str] = None,
        filter_: Optional[Dict[str, Any]] = None,
        partition_filter: Optional[
            Union[models.PartitionFilter, models.PartitionFilterTypedDict]
        ] = None,
        fields: Optional[
            Union[models.FieldsSelectorUnion, models.FieldsSelectorUnionTypedDict]
        ] = None,
        include_vectors: Optional[bool] = False,
        ref: Optional[Union[models.Ref, Mapping[str, Any]]] = None,
        options: Optional[RequestOptions] = None,
    ) -> Iterator[List[Dict[str, Any]]]:
        """Iterate pages while retaining the selected ``ref`` on every request."""
        r, s, t, h = _merge_options(options, UNSET, None, None, None)
        current_page_token = page_token
        buffer: List[Dict[str, Any]] = []
        while True:
            need = size - len(buffer)
            if need <= 0:
                page = buffer[:size]
                buffer = buffer[size:]
                yield page
                if not buffer and current_page_token is None:
                    return
                continue
            resp = self.list(
                size=min(need, _LIST_DOCS_MAX_SIZE),
                page_token=current_page_token,
                filter_=filter_,
                partition_filter=partition_filter,
                fields=fields,
                include_vectors=include_vectors,
                ref=ref,
                retries=r,
                server_url=s,
                timeout_ms=t,
                http_headers=h,
            )
            for item in resp.results:
                buffer.append(_doc_from_item(item))
            current_page_token = resp.next_page_token
            if len(buffer) >= size or current_page_token is None:
                page = buffer[:size]
                buffer = buffer[size:]
                yield page
                if current_page_token is None:
                    if buffer:
                        yield buffer
                    return

    def iter_all(
        self,
        *,
        page_size: int = 100,
        ref: Optional[Union[models.Ref, Mapping[str, Any]]] = None,
        options: Optional[RequestOptions] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Iterate all documents while retaining the selected ``ref``."""
        for page in self.list_pages(size=page_size, options=options, ref=ref):
            for doc in page:
                yield doc

    async def list_async(
        self,
        *,
        size: Optional[int] = None,
        page_token: Optional[str] = None,
        filter_: Optional[Dict[str, Any]] = None,
        partition_filter: Optional[
            Union[models.PartitionFilter, models.PartitionFilterTypedDict]
        ] = None,
        fields: Optional[
            Union[models.FieldsSelectorUnion, models.FieldsSelectorUnionTypedDict]
        ] = None,
        include_vectors: Optional[bool] = False,
        ref: Optional[Union[models.Ref, Mapping[str, Any]]] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.ListDocsResponse:
        """List documents asynchronously from an optional ``ref``.

        Presigned result payloads are fetched automatically.
        A missing ref raises ``ResourceNotFoundError``. A dangling Alias raises
        ``BadRequestError`` until it is retargeted to an existing Branch or Tag.
        """
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        if filter_ is not None or partition_filter is not None or fields is not None:
            response = await self._docs.list_docs_extended_async(
                collection_name=self._collection_name,
                size=size,
                page_token=page_token,
                filter_=filter_,
                partition_filter=partition_filter,
                fields=fields,
                include_vectors=include_vectors,
                ref=ref,
                retries=r,
                server_url=s,
                timeout_ms=t,
                http_headers=h,
            )
        else:
            response = await self._docs.list_docs_async(
                collection_name=self._collection_name,
                size=size,
                page_token=page_token,
                include_vectors=include_vectors,
                ref=ref,
                retries=r,
                server_url=s,
                timeout_ms=t,
                http_headers=h,
            )
        async_client = self._docs.sdk_configuration.async_client
        if async_client is not None:
            timeout_sec = (t / 1000.0) if t is not None else (self._docs.sdk_configuration.timeout_ms / 1000.0 if self._docs.sdk_configuration.timeout_ms else None)
            response = await _resolve_list_docs_response_async(response, async_client, timeout_sec)
        return response

    async def list_pages_async(
        self,
        *,
        size: int = 100,
        page_token: Optional[str] = None,
        filter_: Optional[Dict[str, Any]] = None,
        partition_filter: Optional[
            Union[models.PartitionFilter, models.PartitionFilterTypedDict]
        ] = None,
        fields: Optional[
            Union[models.FieldsSelectorUnion, models.FieldsSelectorUnionTypedDict]
        ] = None,
        include_vectors: Optional[bool] = False,
        ref: Optional[Union[models.Ref, Mapping[str, Any]]] = None,
        options: Optional[RequestOptions] = None,
    ) -> AsyncIterator[List[Dict[str, Any]]]:
        """Asynchronously iterate document pages while preserving the selected ref."""
        current_page_token = page_token
        buffer: List[Dict[str, Any]] = []
        while True:
            need = size - len(buffer)
            if need <= 0:
                page = buffer[:size]
                buffer = buffer[size:]
                yield page
                if not buffer and current_page_token is None:
                    return
                continue
            response = await self.list_async(
                size=min(need, _LIST_DOCS_MAX_SIZE),
                page_token=current_page_token,
                filter_=filter_,
                partition_filter=partition_filter,
                fields=fields,
                include_vectors=include_vectors,
                ref=ref,
                options=options,
            )
            buffer.extend(_doc_from_item(item) for item in response.results)
            current_page_token = response.next_page_token
            if len(buffer) >= size or current_page_token is None:
                page = buffer[:size]
                buffer = buffer[size:]
                yield page
                if current_page_token is None:
                    if buffer:
                        yield buffer
                    return

    async def iter_all_async(
        self,
        *,
        page_size: int = 100,
        ref: Optional[Union[models.Ref, Mapping[str, Any]]] = None,
        options: Optional[RequestOptions] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Asynchronously iterate all documents while preserving the selected ref."""
        async for page in self.list_pages_async(
            size=page_size, ref=ref, options=options
        ):
            for document in page:
                yield document

    def upsert(
        self,
        *,
        docs: List[Dict[str, Any]],
        branch: Optional[str] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Upsert documents into ``branch`` (default: ``main``)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return self._docs.upsert(
            collection_name=self._collection_name,
            docs=docs,
            branch=branch,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    async def upsert_async(
        self,
        *,
        docs: List[Dict[str, Any]],
        branch: Optional[str] = None,
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
            branch=branch,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    def get_bulk_upsert(
        self,
        *,
        branch: Optional[str] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.GetBulkUpsertDocsResponse:
        """Request signed bulk-upload info for ``branch`` (default: ``main``)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return self._docs.get_bulk_upsert(
            collection_name=self._collection_name,
            branch=branch,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    async def get_bulk_upsert_async(
        self,
        *,
        branch: Optional[str] = None,
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
            branch=branch,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    def bulk_upsert(
        self,
        *,
        object_key: str,
        branch: Optional[str] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Complete a bulk upsert on the same ``branch`` used for upload info."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return self._docs.bulk_upsert(
            collection_name=self._collection_name,
            object_key=object_key,
            branch=branch,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    async def bulk_upsert_async(
        self,
        *,
        object_key: str,
        branch: Optional[str] = None,
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
            branch=branch,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    def bulk_upsert_docs(
        self,
        *,
        docs: Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]],
        branch: Optional[str] = None,
        transfer_client: Optional[HttpClient] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Upload and complete bulk upsert on one branch.

        Signed headers are forwarded unchanged. ``transfer_client`` can isolate
        object-storage traffic from the LambdaDB API client.
        """
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        info = self._docs.get_bulk_upsert(
            collection_name=self._collection_name,
            branch=branch,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )
        payload = docs if isinstance(docs, dict) else {"docs": docs}
        body = json.dumps(payload).encode("utf-8")
        size_limit = info.size_limit_bytes
        if len(body) > size_limit:
            raise ValueError(
                f"Documents payload size {len(body)} bytes exceeds limit {size_limit} bytes"
            )
        config = self._docs.sdk_configuration
        client = transfer_client or config.client
        if client is None:
            raise ValueError("HTTP client is required for bulk_upsert_docs")
        timeout_sec = (t / 1000.0) if t is not None else (config.timeout_ms / 1000.0 if config.timeout_ms else None)
        req = client.build_request(
            info.http_method.value,
            info.url,
            content=body,
            headers=_bulk_upload_headers(info),
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
            branch=branch,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    async def bulk_upsert_docs_async(
        self,
        *,
        docs: Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]],
        branch: Optional[str] = None,
        transfer_client: Optional[AsyncHttpClient] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """One-step bulk upsert (async): gets presigned URL, uploads documents to S3, then triggers bulk_upsert.
        Accepts either docs=[...] or docs={"docs":[...]}."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        info = await self._docs.get_bulk_upsert_async(
            collection_name=self._collection_name,
            branch=branch,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )
        payload = docs if isinstance(docs, dict) else {"docs": docs}
        body = json.dumps(payload).encode("utf-8")
        size_limit = info.size_limit_bytes
        if len(body) > size_limit:
            raise ValueError(
                f"Documents payload size {len(body)} bytes exceeds limit {size_limit} bytes"
            )
        config = self._docs.sdk_configuration
        async_client = transfer_client or config.async_client
        if async_client is None:
            raise ValueError("Async HTTP client is required for bulk_upsert_docs_async")
        timeout_sec = (t / 1000.0) if t is not None else (config.timeout_ms / 1000.0 if config.timeout_ms else None)
        req = async_client.build_request(
            info.http_method.value,
            info.url,
            content=body,
            headers=_bulk_upload_headers(info),
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
            branch=branch,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    def update(
        self,
        *,
        docs: List[Dict[str, Any]],
        branch: Optional[str] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Update documents in ``branch`` (default: ``main``)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return self._docs.update(
            collection_name=self._collection_name,
            docs=docs,
            branch=branch,
            retries=r,
            server_url=s,
            timeout_ms=t,
            http_headers=h,
        )

    async def update_async(
        self,
        *,
        docs: List[Dict[str, Any]],
        branch: Optional[str] = None,
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
            branch=branch,
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
        branch: Optional[str] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Delete documents from ``branch`` (default: ``main``)."""
        effective_filter = query_filter if query_filter is not None else filter_
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return self._docs.delete(
            collection_name=self._collection_name,
            ids=ids,
            filter_=effective_filter,
            partition_filter=partition_filter,
            branch=branch,
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
        branch: Optional[str] = None,
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
            branch=branch,
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
        ref: Optional[Union[models.Ref, Mapping[str, Any]]] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.FetchDocsResponse:
        """Fetch documents by ID from an optional Branch, Tag, or Alias ``ref``.

        A missing ref raises ``ResourceNotFoundError``. A dangling Alias raises
        ``BadRequestError`` until it is retargeted to an existing Branch or Tag.
        """
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        response = self._docs.fetch(
            collection_name=self._collection_name,
            ids=ids,
            consistent_read=consistent_read,
            include_vectors=include_vectors,
            fields=fields,
            partition_filter=partition_filter,
            ref=ref,
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
        ref: Optional[Union[models.Ref, Mapping[str, Any]]] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.FetchDocsResponse:
        """Fetch documents asynchronously from an optional ``ref``.

        Presigned result payloads are fetched automatically.
        A missing ref raises ``ResourceNotFoundError``. A dangling Alias raises
        ``BadRequestError`` until it is retargeted to an existing Branch or Tag.
        """
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        response = await self._docs.fetch_async(
            collection_name=self._collection_name,
            ids=ids,
            consistent_read=consistent_read,
            include_vectors=include_vectors,
            fields=fields,
            partition_filter=partition_filter,
            ref=ref,
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

    versioning: CollectionVersioning
    branches: Branches
    tags: Tags
    aliases: Aliases

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
        self.versioning = CollectionVersioning(
            sdk_configuration, collection_name, parent_ref=parent_ref
        )
        self.branches = self.versioning.branches
        self.tags = self.versioning.tags
        self.aliases = self.versioning.aliases

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
        ref: Optional[Union[models.Ref, Mapping[str, Any]]] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.QueryCollectionResponse:
        """Search an optional Branch, Tag, or Alias ``ref``.

        A missing ref raises ``ResourceNotFoundError``. A dangling Alias raises
        ``BadRequestError`` until it is retargeted to an existing Branch or Tag.
        """
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
            ref=ref,
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
        ref: Optional[Union[models.Ref, Mapping[str, Any]]] = None,
        options: Optional[RequestOptions] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.QueryCollectionResponse:
        """Search an optional ``ref`` asynchronously.

        Presigned result payloads are fetched automatically.
        A missing ref raises ``ResourceNotFoundError``. A dangling Alias raises
        ``BadRequestError`` until it is retargeted to an existing Branch or Tag.
        """
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
            ref=ref,
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
