"""Collection-scoped API: client.collection(name).docs.* and .query().
Aligns with REST: document operations under .docs, collection-level query at .query().
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Union

from lambdadb import models, utils
from lambdadb.docs import Docs
from lambdadb.collections import Collections
from lambdadb.sdkconfiguration import SDKConfiguration
from lambdadb.types import OptionalNullable, UNSET


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
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.ListDocsResponse:
        """List documents in this collection."""
        return self._docs.list_docs(
            collection_name=self._collection_name,
            size=size,
            page_token=page_token,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def list_async(
        self,
        *,
        size: Optional[int] = None,
        page_token: Optional[str] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.ListDocsResponse:
        """List documents in this collection (async)."""
        return await self._docs.list_docs_async(
            collection_name=self._collection_name,
            size=size,
            page_token=page_token,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    def upsert(
        self,
        *,
        docs: List[Dict[str, Any]],
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Upsert documents into this collection (max payload 6MB)."""
        return self._docs.upsert(
            collection_name=self._collection_name,
            docs=docs,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def upsert_async(
        self,
        *,
        docs: List[Dict[str, Any]],
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Upsert documents into this collection (async)."""
        return await self._docs.upsert_async(
            collection_name=self._collection_name,
            docs=docs,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    def get_bulk_upsert(
        self,
        *,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.GetBulkUpsertDocsResponse:
        """Request required info to upload documents (bulk)."""
        return self._docs.get_bulk_upsert(
            collection_name=self._collection_name,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def get_bulk_upsert_async(
        self,
        *,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.GetBulkUpsertDocsResponse:
        """Request required info to upload documents (bulk, async)."""
        return await self._docs.get_bulk_upsert_async(
            collection_name=self._collection_name,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    def bulk_upsert(
        self,
        *,
        object_key: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Bulk upsert documents (max object size 200MB)."""
        return self._docs.bulk_upsert(
            collection_name=self._collection_name,
            object_key=object_key,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def bulk_upsert_async(
        self,
        *,
        object_key: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Bulk upsert documents (async)."""
        return await self._docs.bulk_upsert_async(
            collection_name=self._collection_name,
            object_key=object_key,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    def update(
        self,
        *,
        docs: List[Dict[str, Any]],
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Update documents (each doc must have 'id'). Max payload 6MB."""
        return self._docs.update(
            collection_name=self._collection_name,
            docs=docs,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def update_async(
        self,
        *,
        docs: List[Dict[str, Any]],
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Update documents (async)."""
        return await self._docs.update_async(
            collection_name=self._collection_name,
            docs=docs,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    def delete(
        self,
        *,
        ids: Optional[List[str]] = None,
        filter_: Optional[Dict[str, Any]] = None,
        partition_filter: Optional[
            Union[models.PartitionFilter, models.PartitionFilterTypedDict]
        ] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Delete documents by IDs or query filter."""
        return self._docs.delete(
            collection_name=self._collection_name,
            ids=ids,
            filter_=filter_,
            partition_filter=partition_filter,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def delete_async(
        self,
        *,
        ids: Optional[List[str]] = None,
        filter_: Optional[Dict[str, Any]] = None,
        partition_filter: Optional[
            Union[models.PartitionFilter, models.PartitionFilterTypedDict]
        ] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.MessageResponse:
        """Delete documents by IDs or query filter (async)."""
        return await self._docs.delete_async(
            collection_name=self._collection_name,
            ids=ids,
            filter_=filter_,
            partition_filter=partition_filter,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
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
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.FetchDocsResponse:
        """Fetch documents by IDs (max 100)."""
        return self._docs.fetch(
            collection_name=self._collection_name,
            ids=ids,
            consistent_read=consistent_read,
            include_vectors=include_vectors,
            fields=fields,
            partition_filter=partition_filter,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
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
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.FetchDocsResponse:
        """Fetch documents by IDs (async)."""
        return await self._docs.fetch_async(
            collection_name=self._collection_name,
            ids=ids,
            consistent_read=consistent_read,
            include_vectors=include_vectors,
            fields=fields,
            partition_filter=partition_filter,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
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
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.QueryCollectionResponse:
        """Search this collection with a query (vector/keyword/hybrid)."""
        return self._collections.query(
            collection_name=self._collection_name,
            query=query,
            size=size,
            consistent_read=consistent_read,
            include_vectors=include_vectors,
            sort=sort,
            fields=fields,
            partition_filter=partition_filter,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
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
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> models.QueryCollectionResponse:
        """Search this collection (async)."""
        return await self._collections.query_async(
            collection_name=self._collection_name,
            query=query,
            size=size,
            consistent_read=consistent_read,
            include_vectors=include_vectors,
            sort=sort,
            fields=fields,
            partition_filter=partition_filter,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )
