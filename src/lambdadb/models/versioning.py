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
    """Legacy flat ref details retained for source compatibility.

    Branch and Tag lifecycle responses now use :class:`BranchDetails` and
    :class:`TagDetails`, respectively.
    """

    name: str
    snapshot_id: Annotated[Optional[str], pydantic.Field(alias="snapshotId")]
    created_at: Annotated[int, pydantic.Field(alias="createdAt")]

    @property
    def created_at_dt(self) -> datetime:
        """Creation time as a timezone-aware UTC datetime."""
        return datetime.fromtimestamp(self.created_at / 1000, tz=timezone.utc)


class SnapshotDetails(BaseModel):
    """An immutable committed snapshot returned with Branch or Tag details."""

    snapshot_id: Annotated[str, pydantic.Field(alias="snapshotId")]
    snapshot_committed_at: Annotated[
        int, pydantic.Field(alias="snapshotCommittedAt")
    ]

    @property
    def snapshot_committed_at_dt(self) -> datetime:
        """Snapshot commit time as a timezone-aware UTC datetime."""
        return datetime.fromtimestamp(
            self.snapshot_committed_at / 1000, tz=timezone.utc
        )


class BranchDetails(BaseModel):
    """Branch details with its current head and fixed fork point."""

    name: str
    head_snapshot: Annotated[
        Optional[SnapshotDetails], pydantic.Field(alias="headSnapshot")
    ]
    parent_snapshot: Annotated[
        Optional[SnapshotDetails], pydantic.Field(alias="parentSnapshot")
    ]
    created_at: Annotated[int, pydantic.Field(alias="createdAt")]

    @property
    def snapshot_id(self) -> Optional[str]:
        """Current head snapshot ID, retained for compatibility with RefDetails."""
        return None if self.head_snapshot is None else self.head_snapshot.snapshot_id

    @property
    def created_at_dt(self) -> datetime:
        """Branch creation time as a timezone-aware UTC datetime."""
        return datetime.fromtimestamp(self.created_at / 1000, tz=timezone.utc)


class TagDetails(BaseModel):
    """Tag details for one immutable pinned snapshot."""

    name: str
    snapshot_id: Annotated[str, pydantic.Field(alias="snapshotId")]
    snapshot_committed_at: Annotated[
        int, pydantic.Field(alias="snapshotCommittedAt")
    ]
    created_at: Annotated[int, pydantic.Field(alias="createdAt")]

    @property
    def snapshot_committed_at_dt(self) -> datetime:
        """Pinned snapshot commit time as a timezone-aware UTC datetime."""
        return datetime.fromtimestamp(
            self.snapshot_committed_at / 1000, tz=timezone.utc
        )

    @property
    def created_at_dt(self) -> datetime:
        """Tag creation time as a timezone-aware UTC datetime."""
        return datetime.fromtimestamp(self.created_at / 1000, tz=timezone.utc)


class AliasDetails(BaseModel):
    """Alias details, including whether its target is dangling."""

    alias_id: Annotated[str, pydantic.Field(alias="aliasId")]
    alias_name: Annotated[str, pydantic.Field(alias="aliasName")]
    target_kind: Annotated[AliasResolvedTargetKind, pydantic.Field(alias="targetKind")]
    target_name: Annotated[str, pydantic.Field(alias="targetName")]
    target_id: Annotated[str, pydantic.Field(alias="targetId")]
    alias_revision: Annotated[int, pydantic.Field(alias="aliasRevision", ge=0)]
    dangling: Annotated[
        bool,
        pydantic.Field(
            description="Whether the bound target identity is currently missing."
        ),
    ]
    created_at: Annotated[int, pydantic.Field(alias="createdAt")]

    @property
    def created_at_dt(self) -> datetime:
        """Creation time as a timezone-aware UTC datetime."""
        return datetime.fromtimestamp(self.created_at / 1000, tz=timezone.utc)


class BranchResponse(BaseModel):
    branch: BranchDetails


class BranchListResponse(BaseModel):
    branches: List[BranchDetails]


class TagResponse(BaseModel):
    tag: TagDetails


class TagListResponse(BaseModel):
    tags: List[TagDetails]


class AliasResponse(BaseModel):
    alias: AliasDetails


class AliasListResponse(BaseModel):
    aliases: List[AliasDetails]
