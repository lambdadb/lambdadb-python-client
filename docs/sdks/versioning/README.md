# Data Versioning

The Python SDK implements the collection-scoped Data Versioning contract from
`reference/api/openapi.json` (API version 1.3.0) at docs revision
[`9a1f563b9b53bc29e5278105f8fc8c25a17e0cb8`](https://github.com/lambdadb/docs/commit/9a1f563b9b53bc29e5278105f8fc8c25a17e0cb8).

## Branch, Tag, and Alias lifecycle

```python
from lambdadb import AliasTarget, BranchSource, LambdaDB, RefSource

with LambdaDB(project_api_key="...") as client:
    collection = client.collection("catalog")

    branch = collection.branches.create(
        "experiment",
        source=BranchSource.branch("main", as_of=1788336000123),
    )
    tag = collection.tags.create(
        "validated-2026-09",
        source=RefSource.branch("experiment"),
    )
    alias = collection.aliases.create(
        "production-read",
        target=AliasTarget.tag("validated-2026-09"),
    )
    alias = collection.aliases.retarget(
        "production-read",
        target=AliasTarget.branch("main"),
    )

    # Single reads return the same shape as create and list entries.
    branch = collection.branches.get("experiment")
    tag = collection.tags.get("validated-2026-09")
    alias = collection.aliases.get("production-read")

    # list() returns every entry; list_page() and list_pages() read page by page.
    branches = collection.branches.list().branches
    first_page = collection.tags.list_page(size=20)
    for page in collection.aliases.list_pages(size=50):
        ...

    # Branches expose current-head and fixed source-lineage metadata.
    current_head = branch.branch.head_snapshot
    fork_point = branch.branch.parent_snapshot
    direct_parent = branch.branch.parent_branch  # branch_id and name, or None
    published_at = tag.tag.snapshot_committed_at_dt  # None before the first publication
```

Lifecycle methods have matching async forms: `create_async`, `get_async`,
`update_async`, `rollback_async`, `list_async`, `list_page_async`,
`list_pages_async`, `delete_async`, and `retarget_async`.

Branch and Tag creation accept a Branch or Tag source: `RefSource.branch(...)`
(or `BranchSource.branch(...)`) and `RefSource.tag(...)`. Omit `source` to use
`main`. An Alias source is rejected before a request is sent. Without `as_of`,
creation pins the source snapshot, if any, together with the source's fixed
inherited and pending write ranges, without copying them or waiting for the
source build. A Tag can therefore be created before the source's first snapshot
when it captures pending writes; a source with neither a snapshot nor pending
writes returns `BadRequestError`.
A Branch created from a Tag inherits the Tag's pinned schema and every write
captured when the Tag was created; later writes to the original Branch are
excluded. Only a Branch source accepts the optional `as_of` epoch-millisecond
cutoff, which selects the latest retained committed snapshot at or before the
cutoff with no pending or inherited writes; it is not an exact-time restore.
A Tag source copies the Tag's fixed state, not a chain of Tags. `AliasTarget`
accepts a Branch or Tag; an Alias cannot target another Alias. Invalid kinds,
names, and combinations raise a Pydantic `ValidationError` or `ValueError`
before any request is sent.

Query and Fetch also raise `ValueError` locally when `consistent_read=True` is
combined with a Tag ref. A consistent read is allowed on a directly selected
Branch or through an Alias that currently targets a Branch; the server
resolves the Alias when the request is admitted and rejects an Alias that
targets a Tag with HTTP 400. The read overlays eligible inherited and own
pending writes on the Branch's committed snapshot; an ordinary Branch read
uses only the snapshot. It excludes pending bulk imports until a background
build materializes them and can return HTTP 429 when the eligible pending
payload exceeds the overlay limit. Query, Fetch, and document listing on a
Tag, or on an Alias that targets a Tag, already include the Tag's eligible
fixed inherited writes without `consistent_read`. Document listing applies the
same `consistent_read` rule; see [Ref-scoped reads](#ref-scoped-reads).

`parent_branch` is the direct source Branch's fixed identity and name, not the
Branch that committed the selected snapshot. It is present even when both
snapshot fields are `None` for an empty source. `main`, Branches created from a
Tag, and older Branches with no recorded parent return `None`. This is
historical metadata: deleting or recreating the parent does not change it and
does not block deletion.

## Ref details

Every response carries the same object per kind: create, Alias retarget,
single read, Branch update, and list entries.

| Model | Added fields |
| --- | --- |
| `BranchDetails` | `index_configs` (the Branch's own schema), `num_docs` (0 for an empty Branch), `data_updated_at` (`None` for an empty Branch) and `data_updated_at_dt` |
| `TagDetails` | `index_configs` (the schema fixed by the Tag), and `num_docs`, `data_updated_at` and `data_updated_at_dt` of its current published snapshot |
| `AliasDetails` | `index_configs` of the target's version; `None` for a dangling Alias |

A Tag created before its source's first snapshot has `snapshot_id`,
`snapshot_committed_at`, `data_updated_at` and their `_dt` properties set to
`None` and `num_docs` 0 until a build publishes its captured writes. Its
snapshot can change as those fixed writes are published.

`aliases.get(name)` on a dangling Alias still succeeds, with `dangling=True`
and `index_configs=None`. A name that is not a ref of the requested kind raises
`ResourceNotFoundError`.

## Listings

`branches.list()`, `tags.list()`, and `aliases.list()` keep their signature and
return the complete listing in name order. The server pages these listings, so
`list()` follows `next_page_token` with the server's default page size until the
last page; the returned `next_page_token` is always `None`. A failure on any
page raises, and no partial list is returned.

`list_page(size=..., page_token=...)` returns one page: the entries plus
`next_page_token`, which is `None` on the last page. `list_pages(size=...)`
iterates the pages on top of it and yields each page's entries:

```python
page = collection.branches.list_page(size=50)
while page.next_page_token:
    page = collection.branches.list_page(size=50, page_token=page.next_page_token)

for tags in collection.tags.list_pages(size=50):
    ...
```

`size` is 1-100 and the server defaults to 10 when it is omitted. `size` and
`page_token` are sent only when set, and an empty `page_token` is never sent:
it is treated as the first page. An out-of-range `size` raises a Pydantic
`ValidationError` before any request is sent; a malformed token returns
`BadRequestError`.

## Branch schema

A Branch owns its `index_configs`. A new Branch inherits the source Branch's
current schema, the Tag's pinned schema, or the origin snapshot's schema with
`as_of`; later schema updates of other Branches, including `main`, do not
change it.

```python
current = collection.branches.get("experiment").branch.index_configs
updated = collection.branches.update(
    "experiment",
    index_configs={**current, "year": {"type": "long"}},
)
```

`branches.update(name, index_configs=...)` changes that Branch only; updating
`main` also updates the collection's `index_configs`, which mirror `main`. Send
the Branch's complete nonempty schema: existing fields and settings must be
preserved (the server-managed `id` field may be included as returned or
omitted), new fields may be added at any object depth, and a field
`description` may be set, replaced, or cleared with `""`. Concurrent additive
updates of the same Branch are merged. Naming a Tag or an Alias returns
`BadRequestError`. Promoting a Branch's schema to `main` is a manual step:
apply the same additive change to `main`. `index_configs` on
`client.collections.update()` is deprecated; it updates `main` only.

## Branch rollback

```python
result = collection.branches.rollback("main", tag="validated-2026-09")
if result.head_snapshot is None:
    ...  # the Tag had no published snapshot yet
```

`branches.rollback(name, tag=...)` restores a Branch's data and index schema
from a Tag in the same collection. The Branch keeps its identity. When the Tag
has a published snapshot, the Branch records a new committed snapshot, returned
as `head_snapshot`; ordinary reads show the restored snapshot, and
`consistent_read=True` also includes eligible inherited and new writes. When
the Tag has none yet, `head_snapshot` is `None`, as is the Branch's
`head_snapshot` afterwards: the Branch head becomes empty and the Branch
inherits the Tag's fixed writes, like a Branch created from that Tag. Ordinary
reads and document listing then return no documents until a build publishes
those writes, while `consistent_read=True` includes them. Bulk writes appear
after a build.

The request body is `{"tag": ...}`, validated by the strict
`models.RollbackBranchRequestBody`; an invalid Branch or Tag name raises a
Pydantic `ValidationError` before any request is sent. Each request resolves
the Branch by name, and writes admitted before the rollback may still complete
on the previous write stream. Sending the request again performs another
rollback and can undo intervening writes, so the SDK never retries it
automatically: `options.retries` and the client `retry_config` are ignored for
this call, including on 429, 5XX, and connection errors. If two rollbacks
replace the same active write stream, one raises `CatalogConflictError` (409).
The rollback time is not recorded, so `as_of` on this Branch returns
`BadRequestError` for cutoffs between its last snapshot before the rollback and
the first snapshot published after it.

Deleting a Branch or Tag referenced by an Alias is blocked with
`RefDeleteConflictError` (409). Retarget or delete every referencing Alias
before retrying. An Alias that is already dangling remains visible in
`aliases.list()` and `aliases.get()` with `dangling=True`; reading documents
through it raises `BadRequestError`. Selecting a ref that does not exist raises
`ResourceNotFoundError`.

## Ref-scoped reads

```python
from lambdadb import Ref

collection.query(
    query={"queryString": {"query": "category:books"}},
    ref=Ref.tag("validated-2026-09"),
)
collection.docs.fetch(ids=["book-1"], ref=Ref.alias("production-read"))

for page in collection.docs.list_pages(
    size=100,
    ref=Ref.branch("experiment"),
):
    ...

async for document in collection.docs.iter_all_async(
    ref=Ref.alias("production-read")
):
    ...
```

Query and Fetch send `ref` in the JSON body. The simple List endpoint sends the
paired `refKind` and `refName` query parameters; filtered/extended List sends
`ref` in the JSON body. Pagination helpers preserve the same ref on every page.

Each listing page reads the current published Branch snapshot. A Tag, or an
Alias that targets a Tag, also includes the Tag's pending ordinary writes;
unpublished bulk imports are excluded. On a Branch, or an Alias that targets a
Branch, `consistent_read=True` also includes pending ordinary writes; it raises
`ValueError` locally with a Tag ref, and the server rejects an Alias that
targets a Tag with HTTP 400. `sort` orders by up to four keyword, long, double,
or datetime fields, each as `{"field": "asc"}` or `{"field": "desc"}`;
ascending document ID breaks ties and is the default order. Either option uses
the extended list endpoint:

```python
for page in collection.docs.list_pages(
    size=100,
    sort=[{"category": "asc"}],
    consistent_read=True,
    ref=Ref.branch("experiment"),
):
    ...
```

A page token is a position in the requested order, not a snapshot pin: each
page reads the latest data visible to the ref, so documents added after the
cursor can appear on later pages, deleted documents disappear, and a change to
a document's sort value can return it again or skip it. Repeat the same
arguments, including `size`, with `next_page_token` as `page_token`; a
malformed token or a changed request condition raises `BadRequestError`.
`list_pages` and `iter_all` do this for you.

## Branch-scoped writes

```python
collection.docs.upsert(docs=[{"id": "book-1"}], branch="experiment")
collection.docs.update(
    docs=[{"id": "book-1", "title": "New title"}],
    branch="experiment",
)
collection.docs.delete(ids=["book-1"], branch="experiment")
```

Writes accept only a Branch name. Omitting `branch` uses the API's default
`main` Branch.

## Signed bulk upload

The one-step helper requests upload information and completes the bulk upsert
against the same Branch. It forwards every signed header and can use a separate
HTTP client for object-storage transfer:

```python
import httpx

with httpx.Client() as transfer_client:
    collection.docs.bulk_upsert_docs(
        docs=[{"id": "book-1"}],
        branch="experiment",
        transfer_client=transfer_client,
    )
```

For manual upload, pass the same `branch` to `get_bulk_upsert()` and
`bulk_upsert()`, use `info.http_method`, set `Content-Type` from `info.type`,
and forward `info.headers` unchanged. The completion `type` is not a required
user argument; the SDK continues to send `application/json` by default. The
server validates the uploaded object's `Content-Type`.

## Error and retry semantics

HTTP 413, 502, 503, and 504 responses raise `PayloadTooLargeError`,
`BadGatewayError`, `ServiceUnavailableError`, and `GatewayTimeoutError`.
Conditional metadata updates can raise `CatalogConflictError` (409). A 502 or
504 from a write can leave its outcome uncertain, so verify resource state
before retrying. For 429 responses, inspect `error.headers.get("Retry-After")`;
the header is optional and `consistent_read=True` can also return 429 when the
pending-write overlay is too large.

`branches.rollback()` is never retried automatically, because a repeat can
undo intervening writes; after a 5XX or a connection error, read the Branch
before deciding whether to send it again.

Branch or Tag deletion raises `RefDeleteConflictError` (409) while an Alias
references that target. This conflict should not be blindly retried; delete or
retarget the referencing Aliases first. The same error can also represent a
conditional catalog conflict; inspect the message and current ref state.
