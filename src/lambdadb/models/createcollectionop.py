"""Collection creation request and response models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Literal, Optional

import pydantic
from pydantic import field_validator, model_serializer
from typing_extensions import Annotated, NotRequired, TypedDict

from .indexconfigs_union import IndexConfigsUnion, IndexConfigsUnionTypedDict
from .partitionconfig import PartitionConfig, PartitionConfigTypedDict
from lambdadb.types import BaseModel, UNSET_SENTINEL


class CreateCollectionRequestTypedDict(TypedDict):
    collection_name: str
    index_configs: Dict[str, IndexConfigsUnionTypedDict]
    description: NotRequired[str]
    tags: NotRequired[Dict[str, str]]
    partition_config: NotRequired[PartitionConfigTypedDict]
    snapshot_retention_in_days: NotRequired[int]


class CreateCollectionRequest(BaseModel):
    collection_name: Annotated[str, pydantic.Field(alias="collectionName")]
    index_configs: Annotated[
        Dict[str, IndexConfigsUnion], pydantic.Field(alias="indexConfigs")
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
        if value is None:
            return value
        if len(value) > 5:
            raise ValueError("tags may contain at most five entries")
        for key, item in value.items():
            if not 1 <= len(key) <= 63 or any(
                char
                not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-"
                for char in key
            ):
                raise ValueError("tag keys must match ^[A-Za-z0-9_.-]{1,63}$")
            if not 1 <= len(item) <= 127 or any(char in item for char in ":#,"):
                raise ValueError(
                    "tag values must be 1-127 characters and exclude : # ,"
                )
        return value

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


class CreatedCollectionTypedDict(TypedDict):
    collection_name: str
    description: str
    tags: Dict[str, str]
    default_branch_name: Literal["main"]
    snapshot_retention_in_days: int
    created_at: int


class CreatedCollection(BaseModel):
    collection_name: Annotated[str, pydantic.Field(alias="collectionName")]
    description: str
    tags: Dict[str, str]
    default_branch_name: Annotated[
        Literal["main"], pydantic.Field(alias="defaultBranchName")
    ]
    snapshot_retention_in_days: Annotated[
        int, pydantic.Field(alias="snapshotRetentionInDays", ge=1, le=31)
    ]
    created_at: Annotated[int, pydantic.Field(alias="createdAt")]

    @property
    def created_at_dt(self) -> datetime:
        """Creation time as a timezone-aware UTC datetime."""
        return datetime.fromtimestamp(self.created_at / 1000, tz=timezone.utc)


class CreateCollectionResponseTypedDict(TypedDict):
    collection: CreatedCollectionTypedDict


class CreateCollectionResponse(BaseModel):
    collection: CreatedCollection
