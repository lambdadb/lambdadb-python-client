"""Qdrant-style compatibility client backed by LambdaDB."""

from __future__ import annotations

import warnings
from types import SimpleNamespace
from time import monotonic, sleep
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union, cast

from lambdadb import LambdaDB
from lambdadb import errors as lambdadb_errors
from lambdadb.types import OptionalNullable, UNSET
from lambdadb.utils.retries import RetryConfig

from . import models
from .conversions import (
    DEFAULT_VECTOR_NAME,
    doc_to_record,
    merge_index_configs,
    payload_schema_to_index_configs,
    points_to_docs,
    query_vector_and_field,
    result_to_scored_point,
    vector_config_to_index_configs,
)
from .errors import QdrantCompatError, QdrantCompatValidationError, UnsupportedQdrantFeatureError
from .filters import filter_to_lambdadb


class QdrantCompatClient:
    """Qdrant-style client for the common LambdaDB migration subset."""

    def __init__(
        self,
        lambdadb_client: Optional[Any] = None,
        *,
        project_api_key: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        url: Optional[str] = None,
        project_name: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        timeout: Optional[Union[int, float]] = None,
        retry_config: OptionalNullable[RetryConfig] = UNSET,
        path: Optional[str] = None,
        location: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        https: Optional[bool] = None,
        prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        if path is not None or location == ":memory:":
            raise UnsupportedQdrantFeatureError("Qdrant local mode is not supported by LambdaDB compatibility client")
        if lambdadb_client is not None and hasattr(lambdadb_client, "collection"):
            self._client = lambdadb_client
            return

        if kwargs:
            warnings.warn(
                f"Ignoring unsupported Qdrant client options: {', '.join(sorted(kwargs))}",
                RuntimeWarning,
                stacklevel=2,
            )

        resolved_base_url = base_url or url
        if resolved_base_url is None and host is not None:
            scheme = "https" if https is not False else "http"
            resolved_base_url = f"{scheme}://{host}"
            if port is not None:
                resolved_base_url = f"{resolved_base_url}:{port}"
            if prefix:
                resolved_base_url = f"{resolved_base_url.rstrip('/')}/{prefix.lstrip('/')}"
        if resolved_base_url and ("localhost" in resolved_base_url or "127.0.0.1" in resolved_base_url):
            warnings.warn(
                "The Qdrant compatibility client interprets url as LambdaDB base_url, not a Qdrant server URL.",
                RuntimeWarning,
                stacklevel=2,
            )
        effective_timeout_ms = timeout_ms
        if effective_timeout_ms is None and timeout is not None:
            effective_timeout_ms = int(float(timeout) * 1000)
        self._client = LambdaDB(
            project_api_key=project_api_key or api_key,
            base_url=resolved_base_url,
            project_name=project_name,
            timeout_ms=effective_timeout_ms,
            retry_config=retry_config,
        )

    def collection_exists(self, collection_name: str, **kwargs: Any) -> bool:
        self._warn_ignored(kwargs)
        try:
            self._client.collections.get(collection_name=collection_name)
            return True
        except lambdadb_errors.ResourceNotFoundError:
            return False

    def get_collection(self, collection_name: str, **kwargs: Any) -> Any:
        self._warn_ignored(kwargs)
        collection = self._current_collection(collection_name)
        index_configs = self._current_index_configs(collection)
        vectors = self._qdrant_vectors_config(index_configs)
        return SimpleNamespace(
            config=SimpleNamespace(
                params=SimpleNamespace(
                    vectors=vectors,
                    sparse_vectors={},
                )
            ),
            collection_name=collection_name,
        )

    def create_collection(
        self,
        collection_name: str,
        vectors_config: Optional[Union[models.VectorParams, Mapping[str, Any]]] = None,
        **kwargs: Any,
    ) -> bool:
        payload_schema = self._pop_payload_schema(kwargs)
        self._reject_result_changing(kwargs, allowed={"timeout", "init_from"})
        if vectors_config is None:
            raise QdrantCompatValidationError("vectors_config is required")
        index_configs = merge_index_configs(
            vector_config_to_index_configs(vectors_config),
            payload_schema_to_index_configs(payload_schema),
        )
        self._client.collections.create(
            collection_name=collection_name,
            index_configs=cast(Any, index_configs),
        )
        self._wait_for_collection_active(collection_name, timeout_seconds=kwargs.get("timeout"))
        return True

    def recreate_collection(self, collection_name: str, **kwargs: Any) -> bool:
        if self.collection_exists(collection_name):
            self.delete_collection(collection_name)
        return self.create_collection(collection_name=collection_name, **kwargs)

    def delete_collection(self, collection_name: str, **kwargs: Any) -> bool:
        self._warn_ignored(kwargs)
        self._client.collections.delete(collection_name=collection_name)
        return True

    def create_payload_index(
        self,
        collection_name: str,
        field_name: str,
        field_schema: Any,
        wait: Optional[bool] = None,
        **kwargs: Any,
    ) -> bool:
        timeout = kwargs.pop("timeout", None)
        if wait is False:
            warnings.warn("wait=False is accepted but LambdaDB index updates follow LambdaDB semantics", RuntimeWarning, stacklevel=2)
        self._warn_ignored(kwargs)
        collection = self._current_collection(collection_name)
        existing_index_configs = self._current_index_configs(collection)
        payload_index_config = payload_schema_to_index_configs({field_name: field_schema})
        if all(existing_index_configs.get(field) == config for field, config in payload_index_config.items()):
            return True
        num_docs = getattr(collection, "num_docs", 0) or 0
        if num_docs > 0:
            raise UnsupportedQdrantFeatureError(
                "create_payload_index is only supported for empty LambdaDB collections. "
                "LambdaDB applies newly added index configs only to documents written after the change; "
                "declare payload_schema during create_collection or reingest documents after adding the index."
            )
        self._client.collections.update(
            collection_name=collection_name,
            index_configs=cast(Any, merge_index_configs(existing_index_configs, payload_index_config)),
        )
        self._wait_for_collection_active(collection_name, timeout_seconds=timeout)
        return True

    def upsert(
        self,
        collection_name: str,
        points: Iterable[Union[models.PointStruct, Mapping[str, Any]]],
        wait: Optional[bool] = None,
        **kwargs: Any,
    ) -> models.UpdateResult:
        self._warn_ignored(kwargs)
        if wait is False:
            warnings.warn("wait=False is accepted but LambdaDB write visibility follows LambdaDB semantics", RuntimeWarning, stacklevel=2)
        self._client.collection(collection_name).docs.upsert(docs=points_to_docs(points))
        return models.UpdateResult(status=models.UpdateStatus.COMPLETED)

    def upload_points(
        self,
        collection_name: str,
        points: Iterable[Union[models.PointStruct, Mapping[str, Any]]],
        batch_size: int = 64,
        wait: Optional[bool] = None,
        parallel: Optional[int] = None,
        max_retries: Optional[int] = None,
        shard_key_selector: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        if wait is False:
            warnings.warn("wait=False is accepted but LambdaDB write visibility follows LambdaDB semantics", RuntimeWarning, stacklevel=2)
        if shard_key_selector is not None:
            raise UnsupportedQdrantFeatureError("Qdrant shard key routing is not supported in v1")
        self._warn_ignored(kwargs)
        batch: List[Union[models.PointStruct, Mapping[str, Any]]] = []
        for point in points:
            batch.append(point)
            if len(batch) >= batch_size:
                self.upsert(collection_name=collection_name, points=batch)
                batch = []
        if batch:
            self.upsert(collection_name=collection_name, points=batch)

    def upload_collection(
        self,
        collection_name: str,
        vectors: Iterable[Any],
        ids: Optional[Iterable[Union[int, str]]] = None,
        payload: Optional[Iterable[Optional[Dict[str, Any]]]] = None,
        batch_size: int = 64,
        parallel: Optional[int] = None,
        max_retries: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        self._warn_ignored(kwargs)
        vector_list = list(vectors)
        id_list = list(ids) if ids is not None else list(range(len(vector_list)))
        payload_list = list(payload) if payload is not None else [None] * len(vector_list)
        if not (len(vector_list) == len(id_list) == len(payload_list)):
            raise QdrantCompatValidationError("vectors, ids, and payload must have the same length")
        points = [
            models.PointStruct(id=point_id, vector=vector, payload=point_payload)
            for point_id, vector, point_payload in zip(id_list, vector_list, payload_list)
        ]
        self.upload_points(collection_name=collection_name, points=points, batch_size=batch_size)

    def retrieve(
        self,
        collection_name: str,
        ids: List[Union[int, str]],
        with_payload: bool = True,
        with_vectors: bool = False,
        **kwargs: Any,
    ) -> List[models.Record]:
        self._warn_ignored(kwargs)
        response = self._client.collection(collection_name).docs.fetch(
            ids=[str(item) for item in ids],
            consistent_read=True,
            include_vectors=with_vectors,
        )
        return [
            doc_to_record(cast(Mapping[str, Any], item.doc if hasattr(item, "doc") else item), with_payload=with_payload, with_vectors=with_vectors)
            for item in response.results
        ]

    def delete(
        self,
        collection_name: str,
        points_selector: Optional[Any] = None,
        wait: Optional[bool] = None,
        **kwargs: Any,
    ) -> models.UpdateResult:
        self._warn_ignored(kwargs)
        ids = self._ids_from_selector(points_selector)
        if ids is None:
            raise UnsupportedQdrantFeatureError("Only delete by point IDs is supported in v1")
        if wait is False:
            warnings.warn("wait=False is accepted but LambdaDB write visibility follows LambdaDB semantics", RuntimeWarning, stacklevel=2)
        self._client.collection(collection_name).docs.delete(ids=[str(item) for item in ids])
        return models.UpdateResult(status=models.UpdateStatus.COMPLETED)

    def query_points(
        self,
        collection_name: str,
        query: Any,
        query_filter: Optional[Union[models.Filter, Dict[str, Any]]] = None,
        limit: int = 10,
        with_payload: bool = True,
        with_vectors: bool = False,
        using: Optional[str] = None,
        search_params: Optional[models.SearchParams] = None,
        offset: int = 0,
        score_threshold: Optional[float] = None,
        consistency: Optional[Any] = None,
        shard_key_selector: Optional[Any] = None,
        **kwargs: Any,
    ) -> models.QueryResponse:
        self._warn_ignored(kwargs)
        if offset:
            raise UnsupportedQdrantFeatureError("Query offset is not supported in v1")
        if score_threshold is not None:
            raise UnsupportedQdrantFeatureError("Query score_threshold is not supported in v1")
        if consistency is not None:
            warnings.warn("Qdrant consistency is ignored; LambdaDB query_points uses consistent_read=True", RuntimeWarning, stacklevel=2)
        if shard_key_selector is not None:
            raise UnsupportedQdrantFeatureError("Qdrant shard key routing is not supported in v1")
        if search_params is not None:
            warnings.warn("Qdrant search_params are ignored by the LambdaDB compatibility client", RuntimeWarning, stacklevel=2)
        vector, field = query_vector_and_field(query, using=using)
        knn: Dict[str, Any] = {
            "field": field,
            "k": limit,
            "queryVector": vector,
        }
        converted_filter = filter_to_lambdadb(query_filter)
        if converted_filter:
            knn["filter"] = converted_filter
        response = self._client.collection(collection_name).query(
            query={"knn": knn},
            size=limit,
            consistent_read=True,
            include_vectors=with_vectors,
        )
        return models.QueryResponse(
            points=[
                result_to_scored_point(result, with_payload=with_payload, with_vectors=with_vectors)
                for result in response.results
            ]
        )

    def search(
        self,
        collection_name: str,
        query_vector: Any,
        query_filter: Optional[Union[models.Filter, Dict[str, Any]]] = None,
        limit: int = 10,
        with_payload: bool = True,
        with_vectors: bool = False,
        **kwargs: Any,
    ) -> List[models.ScoredPoint]:
        return self.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=with_payload,
            with_vectors=with_vectors,
            **kwargs,
        ).points

    def scroll(
        self,
        collection_name: str,
        scroll_filter: Optional[Union[models.Filter, Dict[str, Any]]] = None,
        limit: int = 10,
        with_payload: bool = True,
        with_vectors: bool = False,
        **kwargs: Any,
    ) -> Tuple[List[models.Record], Optional[str]]:
        self._warn_ignored(kwargs)
        if scroll_filter is not None:
            raise UnsupportedQdrantFeatureError("Filtered scroll is not supported in v1")
        if with_vectors:
            raise UnsupportedQdrantFeatureError("Scroll with vectors is not supported in v1")
        docs: List[Dict[str, Any]] = next(
            self._client.collection(collection_name).docs.list_pages(size=limit),
            [],
        )
        return [doc_to_record(doc, with_payload=with_payload, with_vectors=False) for doc in docs], None

    def count(
        self,
        collection_name: str,
        count_filter: Optional[Union[models.Filter, Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> models.CountResult:
        self._warn_ignored(kwargs)
        if count_filter is not None:
            raise UnsupportedQdrantFeatureError("Filtered count is not supported in v1")
        response = self._client.collections.get(collection_name=collection_name)
        return models.CountResult(count=response.collection.num_docs)

    @staticmethod
    def _ids_from_selector(points_selector: Optional[Any]) -> Optional[List[Union[int, str]]]:
        if points_selector is None:
            return None
        if isinstance(points_selector, list):
            return points_selector
        if isinstance(points_selector, dict):
            if "points" in points_selector:
                return list(points_selector["points"])
            if "ids" in points_selector:
                return list(points_selector["ids"])
        if hasattr(points_selector, "points"):
            return list(cast(Any, points_selector).points)
        return None

    def _wait_for_collection_active(
        self,
        collection_name: str,
        timeout_seconds: Optional[Union[int, float]],
    ) -> None:
        deadline = monotonic() + float(timeout_seconds or 60)
        last_status: Optional[str] = None
        while True:
            response = self._client.collections.get(collection_name=collection_name)
            collection = getattr(response, "collection", None)
            status = getattr(collection, "collection_status", None)
            status_value = getattr(status, "value", status)
            if status_value is None or status_value == "ACTIVE":
                return
            last_status = str(status_value)
            if monotonic() >= deadline:
                raise QdrantCompatError(
                    f"Collection {collection_name!r} did not become ACTIVE "
                    f"within {float(timeout_seconds or 60):g}s; last status={last_status}"
                )
            sleep(0.5)

    def _current_collection(self, collection_name: str) -> Any:
        response = self._client.collections.get(collection_name=collection_name)
        return getattr(response, "collection", None)

    def _current_index_configs(self, collection: Any) -> Dict[str, Dict[str, Any]]:
        index_configs = getattr(collection, "index_configs", None) or {}
        return {str(field_name): self._plain_index_config(index_config) for field_name, index_config in index_configs.items()}

    def _qdrant_vectors_config(self, index_configs: Mapping[str, Mapping[str, Any]]) -> Any:
        unnamed_vector = None
        named_vectors: Dict[str, models.VectorParams] = {}
        for field_name, index_config in index_configs.items():
            if index_config.get("type") != "vector":
                continue
            vector_params = models.VectorParams(
                size=cast(int, index_config.get("dimensions")),
                distance=self._similarity_to_distance(index_config.get("similarity")),
            )
            if field_name == DEFAULT_VECTOR_NAME:
                unnamed_vector = vector_params
            elif field_name.startswith(f"{DEFAULT_VECTOR_NAME}_"):
                named_vectors[field_name[len(DEFAULT_VECTOR_NAME) + 1 :]] = vector_params
        if unnamed_vector is not None and not named_vectors:
            return unnamed_vector
        if unnamed_vector is not None:
            named_vectors[""] = unnamed_vector
        return named_vectors

    @staticmethod
    def _similarity_to_distance(similarity: Any) -> models.Distance:
        similarity_value = getattr(similarity, "value", similarity) or "cosine"
        if similarity_value == "cosine":
            return models.Distance.COSINE
        if similarity_value == "euclidean":
            return models.Distance.EUCLID
        if similarity_value == "dot_product":
            return models.Distance.DOT
        raise UnsupportedQdrantFeatureError(f"LambdaDB similarity {similarity_value!r} cannot be represented as a Qdrant distance")

    @staticmethod
    def _plain_index_config(index_config: Any) -> Dict[str, Any]:
        if hasattr(index_config, "model_dump"):
            return cast(Dict[str, Any], index_config.model_dump(mode="json", by_alias=True, exclude_none=True))
        if isinstance(index_config, Mapping):
            return {
                str(key): getattr(value, "value", value)
                for key, value in index_config.items()
                if value is not None
            }
        return cast(Dict[str, Any], index_config)

    @staticmethod
    def _pop_payload_schema(kwargs: Dict[str, Any]) -> Optional[Mapping[str, Any]]:
        schema_keys = ["payload_schema", "payload_indexes", "payload_index_configs"]
        present = [key for key in schema_keys if key in kwargs and kwargs[key] is not None]
        if len(present) > 1:
            raise QdrantCompatValidationError(f"Use only one payload schema option, got: {', '.join(present)}")
        if not present:
            return None
        raw_schema = kwargs.pop(present[0])
        if not isinstance(raw_schema, Mapping):
            raise QdrantCompatValidationError("payload_schema must be a mapping of payload field names to schema types")
        return raw_schema

    @staticmethod
    def _warn_ignored(kwargs: Mapping[str, Any]) -> None:
        effective_kwargs = {key: value for key, value in kwargs.items() if value is not None}
        if effective_kwargs:
            warnings.warn(
                f"Ignoring unsupported Qdrant options: {', '.join(sorted(effective_kwargs))}",
                RuntimeWarning,
                stacklevel=3,
            )

    @staticmethod
    def _reject_result_changing(kwargs: Mapping[str, Any], allowed: Optional[set] = None) -> None:
        allowed = allowed or set()
        unsupported = sorted(key for key, value in kwargs.items() if value is not None and key not in allowed)
        if unsupported:
            raise UnsupportedQdrantFeatureError(
                f"Unsupported Qdrant collection options: {', '.join(unsupported)}"
            )


QdrantClient = QdrantCompatClient
