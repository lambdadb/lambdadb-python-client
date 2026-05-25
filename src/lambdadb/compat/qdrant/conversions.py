"""Conversion helpers for the Qdrant compatibility client."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union

from lambdadb import models as lambdadb_models

from . import models
from .errors import QdrantCompatValidationError, UnsupportedQdrantFeatureError

DEFAULT_VECTOR_NAME = "_qdrant_vector"
ID_FIELD = "id"
ORIGINAL_ID_FIELD = "_qdrant_id"
RESERVED_PREFIX = "_qdrant_"
_PAYLOAD_SCHEMA_TYPE_ALIASES = {
    "keyword": "keyword",
    "integer": "long",
    "int": "long",
    "long": "long",
    "float": "double",
    "double": "double",
    "bool": "boolean",
    "boolean": "boolean",
    "datetime": "datetime",
    "text": "text",
    "uuid": "keyword",
}


def vector_field_name(name: Optional[str] = None) -> str:
    if not name:
        return DEFAULT_VECTOR_NAME
    safe = str(name).replace(".", "_")
    return f"{DEFAULT_VECTOR_NAME}_{safe}"


def point_from_any(point: Union[models.PointStruct, Mapping[str, Any]]) -> models.PointStruct:
    if isinstance(point, models.PointStruct):
        return point
    if isinstance(point, Mapping):
        return models.PointStruct.model_validate(dict(point))
    if hasattr(point, "id") and hasattr(point, "vector"):
        return models.PointStruct(
            id=getattr(point, "id"),
            vector=getattr(point, "vector"),
            payload=getattr(point, "payload", None),
        )
    raise QdrantCompatValidationError(f"Unsupported point type: {type(point)!r}")


def points_from_any(points: Iterable[Union[models.PointStruct, Mapping[str, Any]]]) -> List[models.PointStruct]:
    return [point_from_any(point) for point in points]


def _validate_payload(payload: Mapping[str, Any]) -> None:
    for key in payload:
        validate_payload_field_name(key)


def validate_payload_field_name(key: str) -> None:
    if key.startswith(RESERVED_PREFIX):
        raise QdrantCompatValidationError(f"Payload field {key!r} uses reserved prefix {RESERVED_PREFIX!r}")
    if key == ID_FIELD:
        raise QdrantCompatValidationError("Payload field 'id' conflicts with the Qdrant point id")


def point_to_doc(point: Union[models.PointStruct, Mapping[str, Any]]) -> Dict[str, Any]:
    item = point_from_any(point)
    payload = dict(item.payload or {})
    _validate_payload(payload)
    doc: Dict[str, Any] = {ID_FIELD: str(item.id), ORIGINAL_ID_FIELD: item.id, **payload}
    if isinstance(item.vector, list):
        doc[DEFAULT_VECTOR_NAME] = item.vector
        return doc
    if isinstance(item.vector, dict):
        for name, vector in item.vector.items():
            if isinstance(vector, dict) and "indices" in vector and "values" in vector:
                raise UnsupportedQdrantFeatureError("Sparse vectors are not supported in v1 Qdrant compatibility upsert")
            if isinstance(vector, models.SparseVector):
                raise UnsupportedQdrantFeatureError("Sparse vectors are not supported in v1 Qdrant compatibility upsert")
            doc[vector_field_name(name)] = vector
        return doc
    raise QdrantCompatValidationError("Point vector must be a dense vector list or named vector dict")


def points_to_docs(points: Iterable[Union[models.PointStruct, Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    return [point_to_doc(point) for point in points]


def _payload_from_doc(doc: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in doc.items()
        if key != ID_FIELD and not key.startswith(RESERVED_PREFIX)
    }


def _vector_from_doc(doc: Mapping[str, Any], with_vectors: bool = False) -> Optional[Any]:
    if not with_vectors:
        return None
    named: Dict[str, Any] = {}
    default = None
    for key, value in doc.items():
        if key == DEFAULT_VECTOR_NAME:
            default = value
        elif key.startswith(f"{DEFAULT_VECTOR_NAME}_"):
            named[key[len(DEFAULT_VECTOR_NAME) + 1 :]] = value
    if named:
        if default is not None:
            named[""] = default
        return named
    return default


def doc_id(doc: Mapping[str, Any]) -> Union[int, str]:
    return doc.get(ORIGINAL_ID_FIELD, doc.get(ID_FIELD, ""))


def doc_to_record(doc: Mapping[str, Any], with_payload: bool = True, with_vectors: bool = False) -> models.Record:
    return models.Record(
        id=doc_id(doc),
        payload=_payload_from_doc(doc) if with_payload else None,
        vector=_vector_from_doc(doc, with_vectors),
    )


def result_to_scored_point(result: Any, with_payload: bool = True, with_vectors: bool = False) -> models.ScoredPoint:
    doc = getattr(result, "doc", result)
    score = getattr(result, "score", None)
    if not isinstance(doc, Mapping):
        raise QdrantCompatValidationError("LambdaDB query result doc must be a mapping")
    return models.ScoredPoint(
        id=doc_id(doc),
        score=score,
        payload=_payload_from_doc(doc) if with_payload else None,
        vector=_vector_from_doc(doc, with_vectors),
    )


def vector_config_to_index_configs(
    vectors_config: Union[models.VectorParams, Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    if _is_vector_params(vectors_config):
        vectors_config = _vector_params_from_any(vectors_config)
        return {
            DEFAULT_VECTOR_NAME: {
                "type": lambdadb_models.TypeVector.VECTOR.value,
                "dimensions": vectors_config.size,
                "similarity": distance_to_similarity(vectors_config.distance),
            }
        }
    if isinstance(vectors_config, Mapping):
        if "size" in vectors_config:
            params = _vector_params_from_any(vectors_config)
            return vector_config_to_index_configs(params)
        index_configs: Dict[str, Dict[str, Any]] = {}
        for name, raw_params in vectors_config.items():
            params = _vector_params_from_any(raw_params)
            index_configs[vector_field_name(str(name))] = {
                "type": lambdadb_models.TypeVector.VECTOR.value,
                "dimensions": params.size,
                "similarity": distance_to_similarity(params.distance),
            }
        return index_configs
    raise QdrantCompatValidationError("vectors_config must be VectorParams or a mapping of vector names")


def payload_schema_to_index_configs(payload_schema: Optional[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not payload_schema:
        return {}
    index_configs: Dict[str, Dict[str, Any]] = {}
    for field_name, raw_schema in payload_schema.items():
        validate_payload_field_name(field_name)
        schema_type = _payload_schema_type(raw_schema)
        index_configs[field_name] = {"type": schema_type}
    return index_configs


def merge_index_configs(*configs: Mapping[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for config in configs:
        for field_name, index_config in config.items():
            if field_name in merged and merged[field_name] != index_config:
                raise QdrantCompatValidationError(f"Conflicting index config for field {field_name!r}")
            merged[field_name] = dict(index_config)
    return merged


def _payload_schema_type(raw_schema: Any) -> str:
    if isinstance(raw_schema, models.PayloadSchemaType):
        raw_type = raw_schema.value
    elif isinstance(raw_schema, str):
        raw_type = raw_schema
    elif isinstance(raw_schema, Mapping):
        if "type" not in raw_schema:
            raise QdrantCompatValidationError("Payload schema mapping must include a 'type' field")
        raw_type = str(raw_schema["type"])
    else:
        raw_type_obj = getattr(raw_schema, "type", None)
        if raw_type_obj is None:
            raise QdrantCompatValidationError(f"Unsupported payload schema value: {raw_schema!r}")
        raw_type = str(getattr(raw_type_obj, "value", raw_type_obj))

    normalized = raw_type.lower()
    if normalized == models.PayloadSchemaType.GEO.value:
        raise UnsupportedQdrantFeatureError("Geo payload indexes are not supported by LambdaDB Qdrant compatibility")
    if normalized not in _PAYLOAD_SCHEMA_TYPE_ALIASES:
        raise UnsupportedQdrantFeatureError(f"Unsupported Qdrant payload schema type: {raw_type!r}")
    return _PAYLOAD_SCHEMA_TYPE_ALIASES[normalized]


def distance_to_similarity(distance: Union[models.Distance, str]) -> str:
    distance_value = getattr(distance, "value", distance)
    dist = distance if isinstance(distance, models.Distance) else models.Distance(distance_value)
    if dist is models.Distance.COSINE:
        return lambdadb_models.Similarity.COSINE.value
    if dist is models.Distance.EUCLID:
        return lambdadb_models.Similarity.EUCLIDEAN.value
    if dist is models.Distance.DOT:
        return lambdadb_models.Similarity.DOT_PRODUCT.value
    raise UnsupportedQdrantFeatureError(f"Qdrant distance {dist.value!r} is not supported")


def query_vector_and_field(query: Any, using: Optional[str] = None) -> Tuple[List[float], str]:
    if isinstance(query, list):
        return query, vector_field_name(using)
    if isinstance(query, tuple) and len(query) == 2:
        name, vector = query
        if not isinstance(vector, list):
            raise UnsupportedQdrantFeatureError("Only dense vector lists are supported in v1")
        return vector, vector_field_name(str(name))
    if isinstance(query, dict):
        if "nearest" in query:
            return query_vector_and_field(query["nearest"], using=using)
        if "vector" in query:
            vector = query["vector"]
            if isinstance(vector, dict):
                if "name" in vector and "vector" in vector:
                    named_vector = vector["vector"]
                    if not isinstance(named_vector, list):
                        raise UnsupportedQdrantFeatureError("Only dense vector lists are supported in v1")
                    return named_vector, vector_field_name(vector["name"])
            if not isinstance(vector, list):
                raise UnsupportedQdrantFeatureError("Only dense vector lists are supported in v1")
            return vector, vector_field_name(using)
    raise UnsupportedQdrantFeatureError("Only dense vector query_points/search inputs are supported in v1")


def _is_vector_params(value: Any) -> bool:
    return isinstance(value, models.VectorParams) or (
        hasattr(value, "size") and hasattr(value, "distance")
    )


def _vector_params_from_any(value: Any) -> models.VectorParams:
    if isinstance(value, models.VectorParams):
        return value
    if isinstance(value, Mapping):
        return models.VectorParams.model_validate(dict(value))
    if _is_vector_params(value):
        return models.VectorParams(
            size=getattr(value, "size"),
            distance=getattr(value, "distance"),
        )
    raise QdrantCompatValidationError(f"Unsupported vector params value: {value!r}")
