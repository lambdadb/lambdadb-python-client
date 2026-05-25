# Qdrant Compatibility Client Design

## Goal

Provide a Qdrant-style client for LambdaDB so existing Qdrant-based Python
applications can move with minimal code changes:

```diff
- from qdrant_client import QdrantClient, models
+ from lambdadb.compat.qdrant import QdrantCompatClient as QdrantClient, models

- client = QdrantClient(url="http://localhost:6333")
+ client = QdrantClient(project_api_key="...", project_name="prod")
```

The v1 goal is not to impersonate Qdrant completely. The public contract should
be explicit that this is a LambdaDB compatibility adapter for the common RAG and
vector-search subset of Qdrant's Python client.

## Product Decision

Use an explicit LambdaDB namespace for v1:

```python
from lambdadb.compat.qdrant import QdrantCompatClient, models
```

This avoids making unsupported Qdrant-specific behavior look fully supported.
If customer demand proves that import-only migration is essential, add a
separate shim package later that exposes a `qdrant_client` module and delegates
to the same implementation.

## Non-Goals

- Full Qdrant cluster/admin API compatibility.
- Qdrant local mode such as `path=":memory:"`.
- HNSW, WAL, optimizer, quantization, shard, replica, snapshot, and alias
  semantics.
- Binary compatibility with every generated Qdrant Pydantic model.
- Depending on the real `qdrant-client` package.

## Target API Surface

### Phase 1: Runtime RAG Subset

Implement enough for common application code and integrations:

| Qdrant-style method | LambdaDB mapping | Notes |
| --- | --- | --- |
| `create_collection()` | `client.collections.create()` | Dense and named dense vectors; optional payload schema. |
| `recreate_collection()` | delete if exists, then create | Preserve Qdrant-style convenience. |
| `collection_exists()` | get/list collection | Return `bool`. |
| `get_collection()` | `client.collections.get()` | Return the minimal Qdrant-style vector config needed by integrations. |
| `delete_collection()` | `client.collections.delete()` | Return `bool`. |
| `create_payload_index()` | `client.collections.update()` | Empty collections only unless the same index already exists. |
| `upsert()` | `coll.docs.upsert()` | Accept `PointStruct`, dicts, and batch lists. |
| `upload_points()` | chunked `upsert()` | No parallelism in v1 unless trivial. |
| `upload_collection()` | columnar input converted to points | Support ids, vectors, payload arrays. |
| `query_points()` | `coll.query()` | Main search method. |
| `search()` | alias to `query_points()` | Legacy compatibility. |
| `retrieve()` | `coll.docs.fetch()` | Return Qdrant-style records. |
| `delete()` | `coll.docs.delete()` | Point IDs and supported Qdrant filters. |
| `scroll()` | `coll.docs.list_pages()` | Unfiltered scroll only; payload/vector response selectors are applied client-side. |
| `count()` | collection metadata | Unfiltered count only. |

### Phase 2: Better Coverage

- Sparse vectors.
- Async client parity with `AsyncQdrantCompatClient`.
- Broader Qdrant model and method coverage driven by real integrations.
- Optional import shim.

### Phase 3: Optional Import Shim

Create a separate package, for example `lambdadb-qdrant-shim`, that installs a
top-level `qdrant_client` module:

```python
from qdrant_client import QdrantClient, models
```

This package should remain a thin wrapper over `lambdadb.compat.qdrant` so the
compatibility behavior has a single source of truth.

## Proposed Package Layout

```text
src/lambdadb/compat/
  __init__.py
  qdrant/
    __init__.py
    client.py
    models.py
    conversions.py
    filters.py
    errors.py
```

Exports from `lambdadb.compat.qdrant`:

```python
from .client import QdrantCompatClient
from . import models
```

`async_client.py`, response-specific modules, and an import-only `qdrant_client`
shim remain future work.

Do not modify generated Speakeasy modules unless the base LambdaDB API contract
needs to change. The compatibility layer should sit above the existing
collection-scoped API.

## Client Initialization

Support two initialization styles.

### Wrap an Existing LambdaDB Client

```python
from lambdadb import LambdaDB
from lambdadb.compat.qdrant import QdrantCompatClient

ldb = LambdaDB(project_api_key="...", project_name="prod")
client = QdrantCompatClient(ldb)
```

### Construct Directly

```python
client = QdrantCompatClient(
    project_api_key="...",
    base_url="https://api.lambdadb.ai",
    project_name="prod",
)
```

Also accept common Qdrant constructor names where they can be safely mapped:

| Qdrant-style arg | Handling |
| --- | --- |
| `api_key` | Alias for `project_api_key`. |
| `url` | Alias for `base_url`, unless it clearly points to local Qdrant. |
| `host`, `port`, `https`, `prefix` | Best-effort URL construction; warn if ambiguous. |
| `timeout` | Convert to LambdaDB `timeout_ms`. |
| `path`, `location=":memory:"` | Raise `UnsupportedQdrantFeatureError`. |
| Unknown kwargs | Store for diagnostics and warn once. |

## Model Layer

Implement a small model subset that supports both attribute access and dict-like
construction. Use Pydantic v2 because the SDK already depends on Pydantic.

Minimum models:

- `PointStruct`
- `VectorParams`
- `PayloadSchemaType`
- `SparseVector`
- `Distance`
- `Filter`
- `FieldCondition`
- `HasIdCondition`
- `MatchValue`
- `MatchAny`
- `MatchExcept`
- `MatchText`
- `Range`
- `SearchParams`
- `UpdateStatus`
- `ScoredPoint`
- `Record`
- `QueryResponse`
- `UpdateResult`
- `CountResult`

The initial implementation can be permissive about extra fields so application
code using newer Qdrant model fields does not fail during object construction.
Unsupported fields should be handled at conversion time.

## Data Mapping

### Point IDs

Qdrant accepts integer or UUID-like IDs. LambdaDB documents should store IDs as
strings:

```python
lambda_doc["id"] = str(point.id)
```

Preserve the original Qdrant ID separately only if needed for response fidelity:

```python
lambda_doc["_qdrant_id"] = point.id
```

Response conversion should return the original numeric ID when `_qdrant_id` is
present; otherwise return the LambdaDB string ID.

### Single Dense Vector

Default field:

```python
vector_field = "_qdrant_vector"
```

Qdrant point:

```python
models.PointStruct(
    id=1,
    vector=[0.1, 0.2, 0.3],
    payload={"text": "hello"},
)
```

LambdaDB document:

```python
{
    "id": "1",
    "_qdrant_id": 1,
    "_qdrant_vector": [0.1, 0.2, 0.3],
    "text": "hello",
}
```

### Named Dense Vectors

Qdrant point:

```python
models.PointStruct(
    id=1,
    vector={"title": [0.1, 0.2], "body": [0.3, 0.4]},
    payload={"text": "hello"},
)
```

LambdaDB document:

```python
{
    "id": "1",
    "_qdrant_id": 1,
    "_qdrant_vector_title": [0.1, 0.2],
    "_qdrant_vector_body": [0.3, 0.4],
    "text": "hello",
}
```

### Sparse Vectors

Sparse vectors are not supported in v1. The compatibility layer detects Qdrant
sparse-vector shapes and raises `UnsupportedQdrantFeatureError` before writing.

A future phase can map Qdrant sparse vectors to LambdaDB sparse-vector fields:

```python
models.SparseVector(indices=[1, 7], values=[0.3, 0.9])
```

LambdaDB field:

```python
{"indices": [1, 7], "values": [0.3, 0.9]}
```

### Payload

Qdrant payload fields become top-level LambdaDB document fields. Reserved
adapter fields use the `_qdrant_` prefix. If payload includes a reserved field,
raise `QdrantCompatValidationError` rather than silently overwriting.

Payload fields used in filters must be declared as LambdaDB index configs.
The compatibility layer accepts a small explicit schema during collection
creation:

```python
client.create_collection(
    collection_name="docs",
    vectors_config=models.VectorParams(size=1536),
    payload_schema={
        "tenant": models.PayloadSchemaType.KEYWORD,
        "views": models.PayloadSchemaType.INTEGER,
        "score": models.PayloadSchemaType.FLOAT,
        "active": models.PayloadSchemaType.BOOL,
    },
)
```

Mapping:

| Qdrant payload schema | LambdaDB index type |
| --- | --- |
| `keyword` | `keyword` |
| `integer` | `long` |
| `float` | `double` |
| `bool` | `boolean` |
| `datetime` | `datetime` |
| `text` | `text` |
| `uuid` | `keyword` |
| `geo` | raise in v1 |

`create_payload_index()` is supported only when the target LambdaDB collection is
empty, unless the same index already exists. LambdaDB currently applies a newly
added index config only to documents written after the config change. This is
different from Qdrant, where adding a payload index after ingest can index
existing payload values, though Qdrant still recommends creating payload indexes
before ingest and rebuilding HNSW if the new payload index should fully benefit
filtered vector search.

## Collection Mapping

### `create_collection()`

Common Qdrant call:

```python
client.create_collection(
    collection_name="docs",
    vectors_config=models.VectorParams(
        size=1536,
        distance=models.Distance.COSINE,
    ),
)
```

LambdaDB collection:

```python
client.collections.create(
    collection_name="docs",
    index_configs={
        "_qdrant_vector": {
            "type": "vector",
            "dimensions": 1536,
            "similarity": "cosine",
        },
        "tenant": {"type": "keyword"},
    },
)
```

Distance mapping:

| Qdrant distance | LambdaDB similarity |
| --- | --- |
| `COSINE` | `cosine` |
| `DOT` | `dot_product` |
| `EUCLID` | `euclidean` |
| `MANHATTAN` | raise in v1 |

For named vectors, generate one LambdaDB vector index per name:

```python
"_qdrant_vector_{name}"
```

## Query Mapping

### `query_points()`

Common Qdrant call:

```python
client.query_points(
    collection_name="docs",
    query=[0.1, 0.2, 0.3],
    query_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="tenant",
                match=models.MatchValue(value="acme"),
            )
        ],
    ),
    limit=10,
    with_payload=True,
    with_vectors=False,
)
```

LambdaDB query:

```python
coll.query(
    query={
        "knn": {
            "field": "_qdrant_vector",
            "queryVector": [0.1, 0.2, 0.3],
            "filter": {"queryString": {"query": "tenant:acme"}},
        },
    },
    size=10,
    consistent_read=True,
    include_vectors=False,
)
```

LambdaDB filter syntax is isolated in `filters.py` so backend contract changes
can be handled without touching client methods.

`offset` and `score_threshold` change query semantics and are unsupported in
v1.

### Legacy `search()`

Implement as a wrapper around `query_points()`:

```python
def search(self, collection_name, query_vector, query_filter=None, limit=10, **kwargs):
    return self.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
        **kwargs,
    ).points
```

## Filter Mapping

Qdrant filters support recursive `must`, `should`, and `must_not` clauses. v1
supports common top-level conditions and fails clearly for unsupported forms.

| Qdrant filter | v1 behavior |
| --- | --- |
| `Filter.must` | AND |
| `Filter.should` | OR via LambdaDB bool clauses |
| `Filter.must_not` | NOT via LambdaDB bool clauses |
| `FieldCondition.match=MatchValue` | equality |
| `FieldCondition.match=MatchAny` | IN |
| `FieldCondition.match=MatchExcept` | NOT IN |
| `FieldCondition.range` | gt/gte/lt/lte |
| `HasIdCondition` | map to ID filter |
| `MatchText` | raise in v1 |
| geo filters | raise |
| nested object filters | raise in v1 |

Policy:

- Unsupported result-changing filters raise `UnsupportedQdrantFeatureError`.
- Unsupported performance-only options, such as HNSW search params, warn once
  and continue.
- Unsupported durability/write-ordering options warn once and continue only when
  LambdaDB semantics remain safe for the operation.

## Response Mapping

Return Qdrant-style objects rather than raw LambdaDB responses.

### Upsert

Return:

```python
models.UpdateResult(
    operation_id=None,
    status=models.UpdateStatus.COMPLETED,
)
```

If LambdaDB returns accepted/asynchronous status, map to `ACKNOWLEDGED` only if
that better matches the actual visibility semantics. Otherwise use `COMPLETED`
for common application compatibility and document the behavior.

### Query/Search

LambdaDB query results become:

```python
models.QueryResponse(
    points=[
        models.ScoredPoint(
            id=...,
            score=...,
            payload={...},
            vector=...,
        )
    ]
)
```

Legacy `search()` returns `List[ScoredPoint]` because many Qdrant examples and
older integrations expect a list.

### Retrieve/Scroll

Return `List[Record]` or `(List[Record], next_page_offset)` depending on the
Qdrant-style method.

## Error Policy

Use adapter-specific exceptions that subclass standard Python exceptions first.
Do not expose LambdaDB HTTP details as Qdrant internals.

Suggested exceptions:

- `QdrantCompatError`
- `UnsupportedQdrantFeatureError`
- `QdrantCompatValidationError`

Map LambdaDB 404 collection errors to a clear collection-not-found error.

## Implementation Plan

### Step 1: Skeleton and Exports

- Add `src/lambdadb/compat/qdrant`.
- Add `QdrantCompatClient`.
- Add `models` module with the minimum Pydantic models.
- Export from `lambdadb.compat.qdrant`.
- Add import tests.

Exit criteria:

- `from lambdadb.compat.qdrant import QdrantCompatClient, models` works.
- `from lambdadb.compat.qdrant.models import PointStruct` works.

### Step 2: Conversion Unit Layer

- Implement point-to-document conversion.
- Implement document-to-record/scored-point conversion.
- Implement vector-field naming helpers.
- Implement distance/similarity mapping.
- Implement reserved-field validation.

Exit criteria:

- Pure unit tests cover dense vector, named vector, sparse placeholder, payload,
  numeric IDs, string IDs, and reserved field collisions.

### Step 3: Collection Operations

- Implement `create_collection`.
- Implement `recreate_collection`.
- Implement `collection_exists`.
- Implement `delete_collection`.

Exit criteria:

- Tests with fake LambdaDB collection methods verify generated `index_configs`.
- Unsupported distances raise clear errors.

### Step 4: Write and Read Operations

- Implement `upsert`.
- Implement `upload_points`.
- Implement `upload_collection`.
- Implement `retrieve`.
- Implement `delete` for ID selectors and supported Qdrant filters.

Exit criteria:

- Existing Qdrant-style point lists are accepted as model instances or dicts.
- LambdaDB docs calls receive the expected document payloads.
- Responses are Qdrant-style model objects.

### Step 5: Query and Filter Operations

- Implement `query_points`.
- Implement legacy `search`.
- Implement v1 filter conversion.
- Implement boolean and field-list `with_payload` and `with_vectors` behavior.

Exit criteria:

- Basic nearest-neighbor search maps to LambdaDB `knn`.
- `limit` maps to `size`.
- Equality and range filters convert correctly.
- Unsupported filters fail before network calls.

### Future Step 6: Async Client

- Add `AsyncQdrantCompatClient`.
- Mirror Phase 1 sync behavior using LambdaDB async methods.

Exit criteria:

- Async import and operation tests pass.
- Sync and async conversion logic share the same helpers.

### Implemented Step 7: Integration Smoke Tests

- Create a real LambdaDB collection.
- Upsert 3-10 points.
- Query by vector with `consistent_read=True` where available.
- Retrieve by IDs.
- Delete by IDs.
- Delete collection.

Exit criteria:

- A single smoke script can run against a test project using environment
  variables and leaves no collection behind.

## Test Plan

### Unit Tests

Add tests under `tests/test_qdrant_compat_*.py`.

Coverage:

- Imports and public exports.
- Model construction from objects and dicts.
- Point conversion:
  - dense vector
  - named dense vectors
  - sparse vector placeholder or unsupported error
  - payload merge
  - reserved payload collision
  - numeric and string IDs
- Collection config conversion:
  - cosine vector
  - dot/euclidean if supported
  - unsupported distance
  - named vectors
  - payload schema to LambdaDB index configs
  - `create_payload_index()` merge behavior
- Filter conversion:
  - must + match value
  - must + match any
  - range
  - must_not behavior
  - unsupported nested/geo filters
- Response conversion:
  - LambdaDB query result to `ScoredPoint`
  - LambdaDB fetch result to `Record`
  - vector inclusion/exclusion

### Client Tests With Fakes

Use small fake LambdaDB clients instead of network calls:

- Fake `collections.create/delete/query`.
- Fake `collection(name).docs.upsert/fetch/delete/list_pages`.
- Assert exact call arguments.
- Assert unsupported options do not make network calls.

### Type and Static Checks

Run the existing SDK checks:

```bash
poetry run pytest tests/ -v
poetry run mypy src
poetry run pyright
```

If the compatibility models use permissive Pydantic types, prefer targeted
type ignores over weakening the rest of the SDK.

### Real Integration Smoke

Add a skipped-by-default test or script:

```bash
LAMBDADB_PROJECT_API_KEY=... \
LAMBDADB_PROJECT_NAME=... \
poetry run pytest tests/integration/test_qdrant_compat_live.py -v
```

The smoke test should:

1. Create a unique collection name.
2. Create collection with a small vector dimension and payload schema.
3. Upsert sample points.
4. Query a nearest neighbor with a payload filter.
5. Retrieve by ID.
6. Delete one point.
7. Delete the collection in `finally`.

### External Integration Tests

The v1 test suite includes optional external smoke tests:

- Minimal LangChain `QdrantVectorStore` add/query flow.
- Minimal LlamaIndex `QdrantVectorStore` add/query flow.
- Tests use an in-process fake LambdaDB transport and are gated by
  `LAMBDADB_RUN_EXTERNAL_INTEGRATION_TESTS=1`.

## Documentation Plan

User-facing docs live in `docs/compatibility/qdrant.md`. Keep README brief and
link to the compatibility docs so future Pinecone or other database adapters can
share the same `docs/compatibility/` structure.

Initial docs should include:

- Migration snippet from `qdrant_client` import to explicit LambdaDB compat import.
- Basic usage example with collection creation, payload schema, upsert, and query.
- Supported method table.
- Unsupported Qdrant features table.
- Data mapping explanation.
- Filter support table.

Avoid saying "drop-in replacement" without qualification. Prefer:

> Qdrant-style compatibility layer for moving common vector-search and RAG
> workloads to LambdaDB with minimal application changes.

## Release Plan

Initial compatibility support shipped behind a minor version bump because it is
additive:

- Add compatibility layer.
- Add tests.
- Add README section.
- Add compatibility docs.
- Bump SDK package/runtime version to `0.8.0`.

Patch-level compatibility expansions can ship as `0.8.x` releases when they
only broaden supported Qdrant-shaped inputs without changing existing behavior.

Do not publish a `qdrant_client` namespace shim in the same release. Keep that
as a separate package or later opt-in module after the explicit adapter has real
usage feedback.

## Resolved Implementation Questions

1. LambdaDB filter translation is implemented in `filters.py` using
   `queryString` and `bool` clauses and is verified by unit and live filtered
   query tests.
2. `upsert()` returns Qdrant-style `COMPLETED` for v1 compatibility.
3. LangChain and LlamaIndex are the first external integration smoke targets.

## Current Implementation Status

The `0.8.0` implementation uses the current LambdaDB API surface.

Implemented:

- Use SDK-only adaptation for collection creation, upsert, query/search,
  retrieve, delete-by-ID, basic collection existence checks, and minimal
  `get_collection()` integration metadata.
- Fail unsupported result-changing Qdrant features with
  `UnsupportedQdrantFeatureError` before making LambdaDB API calls where
  possible.
- Warn and continue only for unsupported options that do not change result
  correctness, such as Qdrant-specific performance tuning knobs.
- Keep LambdaDB filter DSL translation isolated in `filters.py`.

The `0.8.1` patch extends the adapter without changing existing behavior:

- `delete()` supports supported Qdrant filters through the same `filters.py`
  conversion path used by `query_points()`.
- `retrieve()`, `query_points()`, `search()`, and `scroll()` support field-list
  `with_payload` and `with_vectors` selectors.
- External smoke coverage includes LangChain filtered search and LlamaIndex
  delete-by-filter flows.
- Treat filtered count, filtered scroll, query offset, score threshold, sparse
  vectors, and async parity as future work.

## References

- Qdrant points and upsert concepts: https://qdrant.tech/documentation/concepts/points/
- Qdrant Python client docs: https://python-client.qdrant.tech/
- Qdrant nearest-neighbor query examples: https://qdrant.tech/documentation/search/search/
- Qdrant filtering model: https://qdrant.tech/documentation/search/filtering/
