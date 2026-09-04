# Data Versioning

The Python SDK implements the collection-scoped Data Versioning contract from
docs revision
[`a52ce19f5a1ce5ad3a30a55a5560e4591f0be9fa`](https://github.com/lambdadb/docs/commit/a52ce19f5a1ce5ad3a30a55a5560e4591f0be9fa).

## Branch, Tag, and Alias lifecycle

```python
from lambdadb import AliasTarget, LambdaDB, RefSource

with LambdaDB(project_api_key="...") as client:
    collection = client.collection("catalog")

    branch = collection.branches.create(
        "experiment",
        source=RefSource.branch("main", as_of=1788336000123),
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

    branches = collection.branches.list().branches
    tags = collection.tags.list().tags
    aliases = collection.aliases.list().aliases
```

Lifecycle methods have matching async forms: `create_async`, `list_async`,
`delete_async`, and `retarget_async`.

`RefSource` accepts a Branch or Tag. Only a Branch source accepts the optional
`as_of` epoch-millisecond cutoff. `AliasTarget` accepts a Branch or Tag; an
Alias cannot target another Alias. Invalid kinds, names, and combinations raise
a Pydantic `ValidationError` before any request is sent. Query and Fetch also
raise `ValueError` locally when `consistent_read=True` is combined with a Tag
or Alias ref; consistent reads require a directly selected Branch.

Deleting a Branch or Tag can leave an Alias dangling. Such aliases remain in
`aliases.list()` with `dangling=True` until they are retargeted or deleted.
Reading through a dangling Alias raises `BadRequestError`; selecting a ref that
does not exist raises `ResourceNotFoundError`.

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
and forward `info.headers` unchanged.
