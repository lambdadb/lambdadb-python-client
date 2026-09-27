"""Keyword facet request and response models."""
from typing import List, Optional
from typing_extensions import NotRequired, TypedDict
from pydantic import ConfigDict, Field
from lambdadb.types import BaseModel


class FacetRequestTypedDict(TypedDict):
    size: NotRequired[int]


class FacetRequest(BaseModel):
    """Number of buckets to return, from 1 to 100 (default 10)."""
    model_config = ConfigDict(extra="forbid")
    size: Optional[int] = Field(default=None, ge=1, le=100)


class FacetBucketTypedDict(TypedDict):
    value: str
    count: int


class FacetBucket(BaseModel):
    value: str
    count: int


class FacetResultTypedDict(TypedDict):
    buckets: List[FacetBucketTypedDict]


class FacetResult(BaseModel):
    buckets: List[FacetBucket]
