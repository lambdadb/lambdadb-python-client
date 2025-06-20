"""Code generated by Speakeasy (https://speakeasy.com). DO NOT EDIT."""

from __future__ import annotations
from lambdadb.types import BaseModel
from lambdadb.utils import FieldMetadata, PathParamMetadata, RequestMetadata
import pydantic
from typing import Optional
from typing_extensions import Annotated, NotRequired, TypedDict


class BulkUpsertDocsRequestBodyTypedDict(TypedDict):
    object_key: str
    r"""Object key uploaded based on bulk upsert info."""


class BulkUpsertDocsRequestBody(BaseModel):
    object_key: Annotated[str, pydantic.Field(alias="objectKey")]
    r"""Object key uploaded based on bulk upsert info."""


class BulkUpsertDocsRequestTypedDict(TypedDict):
    project_name: str
    r"""Project name."""
    collection_name: str
    r"""Collection name."""
    request_body: BulkUpsertDocsRequestBodyTypedDict


class BulkUpsertDocsRequest(BaseModel):
    project_name: Annotated[
        str,
        pydantic.Field(alias="projectName"),
        FieldMetadata(path=PathParamMetadata(style="simple", explode=False)),
    ]
    r"""Project name."""

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


class BulkUpsertDocsResponseTypedDict(TypedDict):
    r"""Bulk upsert request accepted."""

    message: NotRequired[str]


class BulkUpsertDocsResponse(BaseModel):
    r"""Bulk upsert request accepted."""

    message: Optional[str] = None
