"""Collection update request and response models."""

from __future__ import annotations

from typing import Dict, Union

import pydantic
from pydantic import model_serializer, model_validator
from typing_extensions import Annotated, NotRequired, TypedDict

from .collectionresponse import CollectionResponse, CollectionResponseTypedDict
from .indexconfigs_union import IndexConfigsUnion, IndexConfigsUnionTypedDict
from lambdadb.types import BaseModel, UNSET, UNSET_SENTINEL, Unset
from lambdadb.utils import FieldMetadata, PathParamMetadata, RequestMetadata


class UpdateCollectionRequestBodyTypedDict(TypedDict):
    index_configs: NotRequired[Dict[str, IndexConfigsUnionTypedDict]]
    description: NotRequired[str]
    tags: NotRequired[Dict[str, str]]
    snapshot_retention_in_days: NotRequired[int]


class UpdateCollectionRequestBody(BaseModel):
    index_configs: Annotated[
        Union[Dict[str, IndexConfigsUnion], Unset], pydantic.Field(alias="indexConfigs")
    ] = UNSET
    description: Union[str, Unset] = UNSET
    tags: Union[Dict[str, str], Unset] = UNSET
    snapshot_retention_in_days: Annotated[
        Union[int, Unset], pydantic.Field(alias="snapshotRetentionInDays")
    ] = UNSET

    @model_validator(mode="after")
    def validate_non_empty(self) -> "UpdateCollectionRequestBody":
        if all(
            isinstance(value, Unset)
            for value in (
                self.index_configs,
                self.description,
                self.tags,
                self.snapshot_retention_in_days,
            )
        ):
            raise ValueError("at least one collection field must be provided")
        if (
            not isinstance(self.snapshot_retention_in_days, Unset)
            and not 1 <= self.snapshot_retention_in_days <= 31
        ):
            raise ValueError("snapshot_retention_in_days must be between 1 and 31")
        if not isinstance(self.description, Unset) and len(self.description) > 255:
            raise ValueError("description must be at most 255 characters")
        if not isinstance(self.tags, Unset):
            if len(self.tags) > 5:
                raise ValueError("tags may contain at most five entries")
            for key, value in self.tags.items():
                if not 1 <= len(key) <= 63 or any(
                    char
                    not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-"
                    for char in key
                ):
                    raise ValueError("tag keys must match ^[A-Za-z0-9_.-]{1,63}$")
                if not 1 <= len(value) <= 127 or any(char in value for char in ":#,"):
                    raise ValueError(
                        "tag values must be 1-127 characters and exclude : # ,"
                    )
        return self

    @model_serializer(mode="wrap")
    def serialize_model(self, handler):
        serialized = handler(self)
        result = {}
        for name, field in type(self).model_fields.items():
            key = field.alias or name
            value = self._get_serialized_value(serialized, name, field.alias)
            if value != UNSET_SENTINEL:
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
