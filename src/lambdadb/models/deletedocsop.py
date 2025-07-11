"""Code generated by Speakeasy (https://speakeasy.com). DO NOT EDIT."""

from __future__ import annotations
from lambdadb.types import BaseModel
from lambdadb.utils import FieldMetadata, PathParamMetadata, RequestMetadata
import pydantic
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated, NotRequired, TypedDict


class DeleteDocsRequestBodyTypedDict(TypedDict):
    ids: NotRequired[List[str]]
    r"""A list of document IDs."""
    filter_: NotRequired[Dict[str, Any]]
    r"""Query filter."""


class DeleteDocsRequestBody(BaseModel):
    ids: Optional[List[str]] = None
    r"""A list of document IDs."""

    filter_: Annotated[Optional[Dict[str, Any]], pydantic.Field(alias="filter")] = None
    r"""Query filter."""


class DeleteDocsRequestTypedDict(TypedDict):
    collection_name: str
    r"""Collection name."""
    request_body: DeleteDocsRequestBodyTypedDict


class DeleteDocsRequest(BaseModel):
    collection_name: Annotated[
        str,
        pydantic.Field(alias="collectionName"),
        FieldMetadata(path=PathParamMetadata(style="simple", explode=False)),
    ]
    r"""Collection name."""

    request_body: Annotated[
        DeleteDocsRequestBody,
        FieldMetadata(request=RequestMetadata(media_type="application/json")),
    ]
