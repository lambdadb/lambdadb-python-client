"""Data Versioning models for collection-scoped branches, tags, and aliases."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

import pydantic
from pydantic import ConfigDict, model_validator
from typing_extensions import Annotated

from lambdadb.types import BaseModel

_REF_NAME = pydantic.StringConstraints(
    min_length=3,
    max_length=52,
    pattern=r"^[a-zA-Z0-9_-]{3,52}$",
)
RefName = Annotated[str, _REF_NAME]


class RefKind(str, Enum):
    """Kinds accepted when selecting data for a read."""

    BRANCH = "branch"
    TAG = "tag"
    ALIAS = "alias"


class RefSourceKind(str, Enum):
    """Kinds accepted as a new branch or tag source."""

    BRANCH = "branch"
    TAG = "tag"


class AliasTargetKind(str, Enum):
    """Kinds accepted as an alias target."""

    BRANCH = "branch"
    TAG = "tag"


class AliasResolvedTargetKind(str, Enum):
    """Target kinds returned by the API."""

    BRANCH = "BRANCH"
    TAG = "TAG"


class Ref(BaseModel):
    """A branch, tag, or alias used to scope a read operation."""

    kind: RefKind
    name: RefName
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        protected_namespaces=(),
        extra="forbid",
    )

    @classmethod
    def branch(cls, name: str) -> "Ref":
        """Select a branch."""
        return cls(kind=RefKind.BRANCH, name=name)

    @classmethod
    def tag(cls, name: str) -> "Ref":
        """Select a tag."""
        return cls(kind=RefKind.TAG, name=name)

    @classmethod
    def alias(cls, name: str) -> "Ref":
        """Select an alias."""
        return cls(kind=RefKind.ALIAS, name=name)


RefContext = Ref


class RefSource(BaseModel):
    """Source for a new branch or tag; ``as_of`` is valid only for branches."""

    kind: RefSourceKind
    name: RefName
    as_of: Annotated[Optional[int], pydantic.Field(alias="asOf")] = None
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        protected_namespaces=(),
        extra="forbid",
    )

    @model_validator(mode="after")
    def validate_as_of(self) -> "RefSource":
        if self.kind is RefSourceKind.TAG and self.as_of is not None:
            raise ValueError("as_of is only valid for a branch source")
        if self.as_of is not None and self.as_of < 0:
            raise ValueError("as_of must be a Unix epoch timestamp in milliseconds")
        return self

    @classmethod
    def branch(cls, name: str, *, as_of: Optional[int] = None) -> "RefSource":
        """Use a branch head, optionally at an epoch-millisecond cutoff."""
        return cls(kind=RefSourceKind.BRANCH, name=name, as_of=as_of)

    @classmethod
    def tag(cls, name: str) -> "RefSource":
        """Use a tag snapshot."""
        return cls(kind=RefSourceKind.TAG, name=name)


class AliasTarget(BaseModel):
    """A branch or tag targeted by an alias."""

    kind: AliasTargetKind
    name: RefName
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        protected_namespaces=(),
        extra="forbid",
    )

    @classmethod
    def branch(cls, name: str) -> "AliasTarget":
        return cls(kind=AliasTargetKind.BRANCH, name=name)

    @classmethod
    def tag(cls, name: str) -> "AliasTarget":
        return cls(kind=AliasTargetKind.TAG, name=name)


class RefDetails(BaseModel):
    """Branch or tag details returned by the API."""

    name: str
    snapshot_id: Annotated[Optional[str], pydantic.Field(alias="snapshotId")]
    created_at: Annotated[int, pydantic.Field(alias="createdAt")]

    @property
    def created_at_dt(self) -> datetime:
        """Creation time as a timezone-aware UTC datetime."""
        return datetime.fromtimestamp(self.created_at / 1000, tz=timezone.utc)


class AliasDetails(BaseModel):
    """Alias details, including whether its target is dangling."""

    alias_id: Annotated[str, pydantic.Field(alias="aliasId")]
    alias_name: Annotated[str, pydantic.Field(alias="aliasName")]
    target_kind: Annotated[AliasResolvedTargetKind, pydantic.Field(alias="targetKind")]
    target_name: Annotated[str, pydantic.Field(alias="targetName")]
    target_id: Annotated[str, pydantic.Field(alias="targetId")]
    alias_revision: Annotated[int, pydantic.Field(alias="aliasRevision", ge=0)]
    dangling: bool
    created_at: Annotated[int, pydantic.Field(alias="createdAt")]

    @property
    def created_at_dt(self) -> datetime:
        """Creation time as a timezone-aware UTC datetime."""
        return datetime.fromtimestamp(self.created_at / 1000, tz=timezone.utc)


class BranchResponse(BaseModel):
    branch: RefDetails


class BranchListResponse(BaseModel):
    branches: List[RefDetails]


class TagResponse(BaseModel):
    tag: RefDetails


class TagListResponse(BaseModel):
    tags: List[RefDetails]


class AliasResponse(BaseModel):
    alias: AliasDetails


class AliasListResponse(BaseModel):
    aliases: List[AliasDetails]
