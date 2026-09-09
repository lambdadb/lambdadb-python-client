"""Collection update request and response models."""

from __future__ import annotations

from typing import Dict, Optional, Union

import pydantic
from pydantic import ConfigDict, model_serializer, model_validator
from typing_extensions import Annotated, NotRequired, TypedDict

from .collectionresponse import CollectionResponse, CollectionResponseTypedDict
from .indexconfigs_union import IndexConfigsUnion, IndexConfigsUnionTypedDict
from ._collection_validators import validate_metadata_tags
from lambdadb.types import BaseModel, UNSET, UNSET_SENTINEL, Unset
from lambdadb.utils import FieldMetadata, PathParamMetadata, RequestMetadata


class UpdateCollectionRequestBodyTypedDict(TypedDict):
    index_configs: NotRequired[Optional[Dict[str, IndexConfigsUnionTypedDict]]]
    description: NotRequired[Optional[str]]
    tags: NotRequired[Optional[Dict[str, str]]]
    snapshot_retention_in_days: NotRequired[Optional[int]]


class UpdateCollectionRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index_configs: Annotated[
        Union[Optional[Dict[str, IndexConfigsUnion]], Unset],
        pydantic.Field(alias="indexConfigs"),
    ] = UNSET
    description: Union[Optional[str], Unset] = UNSET
    tags: Union[Optional[Dict[str, str]], Unset] = UNSET
    snapshot_retention_in_days: Annotated[
        Union[Optional[int], Unset], pydantic.Field(alias="snapshotRetentionInDays")
    ] = UNSET

    @model_validator(mode="after")
    def validate_non_empty(self) -> "UpdateCollectionRequestBody":
        if all(
            isinstance(value, Unset) or value is None
            for value in (
                self.index_configs,
                self.description,
                self.tags,
                self.snapshot_retention_in_days,
            )
        ):
            raise ValueError("at least one collection field must be provided")
        if (
            not isinstance(self.index_configs, Unset)
            and self.index_configs is not None
            and not self.index_configs
        ):
            raise ValueError("index_configs must contain at least one field")
        if (
            not isinstance(self.snapshot_retention_in_days, Unset)
            and self.snapshot_retention_in_days is not None
            and not 1 <= self.snapshot_retention_in_days <= 31
        ):
            raise ValueError("snapshot_retention_in_days must be between 1 and 31")
        if (
            not isinstance(self.description, Unset)
            and self.description is not None
            and len(self.description) > 255
        ):
            raise ValueError("description must be at most 255 characters")
        if not isinstance(self.tags, Unset):
            validate_metadata_tags(self.tags)
        return self

    @model_serializer(mode="wrap")
    def serialize_model(self, handler):
        serialized = handler(self)
        result = {}
        for name, field in type(self).model_fields.items():
            key = field.alias or name
            value = self._get_serialized_value(serialized, name, field.alias)
            if value != UNSET_SENTINEL and value is not None:
                result[key] = value
        return result


class UpdateCollectionRequestTypedDict(TypedDict):
    collection_name: str
    request_body: UpdateCollectionRequestBodyTypedDict


class UpdateCollectionRequest(BaseModel):
    collection_name: Annotated[
        str,
        pydantic.Field(alias="collectionName"),
        FieldMetadata(path=PathParamMetadata(style="simple", explode=False)),
    ]
    request_body: Annotated[
        UpdateCollectionRequestBody,
        FieldMetadata(request=RequestMetadata(media_type="application/json")),
    ]


class UpdateCollectionResponseTypedDict(TypedDict):
    collection: CollectionResponseTypedDict


class UpdateCollectionResponse(BaseModel):
    collection: CollectionResponse
