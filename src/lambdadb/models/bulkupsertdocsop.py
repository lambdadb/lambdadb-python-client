"""Code generated by Speakeasy (https://speakeasy.com). DO NOT EDIT."""

from __future__ import annotations
from lambdadb.types import BaseModel
from lambdadb.utils import FieldMetadata, PathParamMetadata, RequestMetadata
import pydantic
from typing_extensions import Annotated, TypedDict


class BulkUpsertDocsRequestBodyTypedDict(TypedDict):
    object_key: str
    r"""Object key uploaded based on bulk upsert info."""


class BulkUpsertDocsRequestBody(BaseModel):
    object_key: Annotated[str, pydantic.Field(alias="objectKey")]
    r"""Object key uploaded based on bulk upsert info."""


class BulkUpsertDocsRequestTypedDict(TypedDict):
    collection_name: str
    r"""Collection name."""
    request_body: BulkUpsertDocsRequestBodyTypedDict


class BulkUpsertDocsRequest(BaseModel):
    collection_name: Annotated[
        str,
        pydantic.Field(alias="collectionName"),
        FieldMetadata(path=PathParamMetadata(style="simple", explode=False)),
    ]
    r"""Collection name."""

    request_body: Annotated[
        BulkUpsertDocsRequestBody,
        FieldMetadata(request=RequestMetadata(media_type="application/json")),
    ]
