"""Collection creation request and response models."""

from __future__ import annotations

from typing import Dict, Optional

import pydantic
from pydantic import ConfigDict, field_validator, model_serializer
from typing_extensions import Annotated, NotRequired, TypedDict

from .collectionresponse import CollectionResponse, CollectionResponseTypedDict
from .indexconfigs_union import IndexConfigsUnion, IndexConfigsUnionTypedDict
from .partitionconfig import PartitionConfig, PartitionConfigTypedDict
from ._collection_validators import validate_metadata_tags
from lambdadb.types import BaseModel, UNSET_SENTINEL


class CreateCollectionRequestTypedDict(TypedDict):
    collection_name: str
    index_configs: Dict[str, IndexConfigsUnionTypedDict]
    description: NotRequired[str]
    tags: NotRequired[Dict[str, str]]
    partition_config: NotRequired[PartitionConfigTypedDict]
    snapshot_retention_in_days: NotRequired[int]


class CreateCollectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection_name: Annotated[str, pydantic.Field(alias="collectionName")]
    index_configs: Annotated[
        Dict[str, IndexConfigsUnion],
        pydantic.Field(alias="indexConfigs", min_length=1),
    ]
    description: Annotated[Optional[str], pydantic.Field(max_length=255)] = None
    tags: Optional[Dict[str, str]] = None
    partition_config: Annotated[
        Optional[PartitionConfig], pydantic.Field(alias="partitionConfig")
    ] = None
    snapshot_retention_in_days: Annotated[
        Optional[int], pydantic.Field(alias="snapshotRetentionInDays", ge=1, le=31)
    ] = None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        return validate_metadata_tags(value)

    @model_serializer(mode="wrap")
    def serialize_model(self, handler):
        optional_fields = {
            "description",
            "tags",
            "partitionConfig",
            "snapshotRetentionInDays",
        }
        serialized = handler(self)
        result = {}
        for name, field in type(self).model_fields.items():
            key = field.alias or name
            value = self._get_serialized_value(serialized, name, field.alias)
            if value != UNSET_SENTINEL and (
                value is not None or key not in optional_fields
            ):
                result[key] = value
        return result


CreatedCollectionTypedDict = CollectionResponseTypedDict
CreatedCollection = CollectionResponse
"""Deprecated alias of :class:`CollectionResponse`.

Collection creation returns the same shape as a collection read.
"""


class CreateCollectionResponseTypedDict(TypedDict):
    collection: CollectionResponseTypedDict


class CreateCollectionResponse(BaseModel):
    collection: CollectionResponse
    """The created collection, in the same shape as a collection read."""
