"""Collection-scoped API: client.collection(name).docs.* and .query().
Aligns with REST: document operations under .docs, collection-level query at .query().
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Mapping, Optional, Union

from lambdadb import models, utils
from lambdadb.docs import Docs
from lambdadb.collections import Collections
from lambdadb.sdkconfiguration import SDKConfiguration
from lambdadb.types import OptionalNullable, UNSET

# API max page size for list_docs
_LIST_DOCS_MAX_SIZE = 100


def _doc_from_item(item: Any) -> Dict[str, Any]:
    """Normalize list_docs item: return item['doc'] if present else item."""
    if isinstance(item, dict) and "doc" in item:
        return item["doc"]
    return item if isinstance(item, dict) else {}


@dataclass
class RequestOptions:
    """Advanced options for a single request. Pass as options= to any docs method."""

    retries: OptionalNullable[utils.RetryConfig] = UNSET
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
        """Fetch documents by IDs (max 100). For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return self._docs.fetch(
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
        """Fetch documents by IDs (async). For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return await self._docs.fetch_async(
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
        """Search this collection with a query (vector/keyword/hybrid). For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return self._collections.query(
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
        """Search this collection (async). For advanced options use options=RequestOptions(...)."""
        r, s, t, h = _merge_options(options, retries, server_url, timeout_ms, http_headers)
        return await self._collections.query_async(
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
