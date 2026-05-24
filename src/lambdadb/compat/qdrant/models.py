"""Small Qdrant model subset used by the compatibility client."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class CompatModel(BaseModel):
    """Permissive model base matching Qdrant client's practical construction style."""

    model_config = ConfigDict(extra="allow", populate_by_name=True, arbitrary_types_allowed=True)


class Distance(str, Enum):
    COSINE = "Cosine"
    EUCLID = "Euclid"
    DOT = "Dot"
    MANHATTAN = "Manhattan"


class UpdateStatus(str, Enum):
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"


class VectorParams(CompatModel):
    size: int
    distance: Distance = Distance.COSINE


class PayloadSchemaType(str, Enum):
    KEYWORD = "keyword"
    INTEGER = "integer"
    FLOAT = "float"
    BOOL = "bool"
    DATETIME = "datetime"
    TEXT = "text"
    UUID = "uuid"
    GEO = "geo"


class SparseVector(CompatModel):
    indices: List[int]
    values: List[float]


class PointStruct(CompatModel):
    id: Union[int, str]
    vector: Union[List[float], Dict[str, Union[List[float], SparseVector, Dict[str, Any]]]]
    payload: Optional[Dict[str, Any]] = None


class MatchValue(CompatModel):
    value: Any


class MatchAny(CompatModel):
    any: List[Any]


class MatchExcept(CompatModel):
    except_: List[Any] = Field(alias="except")


class MatchText(CompatModel):
    text: str


class Range(CompatModel):
    gt: Optional[Any] = None
    gte: Optional[Any] = None
    lt: Optional[Any] = None
    lte: Optional[Any] = None


class FieldCondition(CompatModel):
    key: str
    match: Optional[Union[MatchValue, MatchAny, MatchExcept, MatchText, Dict[str, Any]]] = None
    range: Optional[Union[Range, Dict[str, Any]]] = None


class HasIdCondition(CompatModel):
    has_id: List[Union[int, str]]


Condition = Union[FieldCondition, HasIdCondition, Dict[str, Any]]


class Filter(CompatModel):
    must: Optional[List[Condition]] = None
    should: Optional[List[Condition]] = None
    must_not: Optional[List[Condition]] = None


class SearchParams(CompatModel):
    hnsw_ef: Optional[int] = None
    exact: Optional[bool] = None


class ScoredPoint(CompatModel):
    id: Union[int, str]
    version: Optional[int] = None
    score: Optional[float] = None
    payload: Optional[Dict[str, Any]] = None
    vector: Optional[Any] = None


class Record(CompatModel):
    id: Union[int, str]
    payload: Optional[Dict[str, Any]] = None
    vector: Optional[Any] = None


class QueryResponse(CompatModel):
    points: List[ScoredPoint]


class UpdateResult(CompatModel):
    operation_id: Optional[Union[int, str]] = None
    status: UpdateStatus = UpdateStatus.COMPLETED


class CountResult(CompatModel):
    count: int
