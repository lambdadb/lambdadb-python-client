# Qdrant Compatibility

LambdaDB provides an explicit Qdrant-style compatibility client for common
vector-search and RAG migration paths:

```python
from lambdadb.compat.qdrant import QdrantCompatClient, models

client = QdrantCompatClient(
    project_api_key="<YOUR_PROJECT_API_KEY>",
    base_url="https://api.lambdadb.ai",
    project_name="playground",
)
```

The compatibility layer is not a full `qdrant_client` replacement. It maps the
common dense-vector subset onto LambdaDB and raises `UnsupportedQdrantFeatureError`
for unsupported behavior where possible.

## Migration Shape

For v1, switch the import and client construction explicitly:

```diff
- from qdrant_client import QdrantClient, models
+ from lambdadb.compat.qdrant import QdrantCompatClient as QdrantClient, models

- client = QdrantClient(url="http://localhost:6333")
+ client = QdrantClient(
+     project_api_key="<YOUR_PROJECT_API_KEY>",
+     base_url="https://api.lambdadb.ai",
+     project_name="playground",
+ )
```

## Basic Usage

Declare payload fields used in filters when the collection is created:

```python
client.create_collection(
    collection_name="docs",
    vectors_config=models.VectorParams(
        size=3,
        distance=models.Distance.COSINE,
    ),
    payload_schema={
        "tenant": models.PayloadSchemaType.KEYWORD,
    },
)

client.upsert(
    collection_name="docs",
    points=[
        models.PointStruct(
            id=1,
            vector=[1.0, 0.0, 0.0],
            payload={"tenant": "acme", "title": "alpha"},
        )
    ],
)

result = client.query_points(
    collection_name="docs",
    query=[1.0, 0.0, 0.0],
    query_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="tenant",
                match=models.MatchValue(value="acme"),
            )
        ]
    ),
    limit=10,
)
```

## Supported Surface

| Qdrant-style API | Status | Notes |
| --- | --- | --- |
| `QdrantCompatClient(...)` | Supported | Accepts LambdaDB config directly or an existing LambdaDB client. |
| `collection_exists()` | Supported | Maps to LambdaDB collection metadata lookup. |
| `get_collection()` | Supported | Returns minimal Qdrant-style collection metadata used by integrations. |
| `create_collection()` | Supported | Dense vectors and named dense vectors. Use `payload_schema` for filter fields. |
| `recreate_collection()` | Supported | Deletes the collection if it exists, then creates it. |
| `delete_collection()` | Supported | Maps to LambdaDB collection delete. |
| `create_payload_index()` | Limited | Only supported for empty collections unless the same index already exists. |
| `upsert()` | Supported | Dense vectors only. Qdrant IDs become LambdaDB document IDs. |
| `upload_points()` | Supported | Batches points through `upsert()`. |
| `upload_collection()` | Supported | Converts vectors, ids, and payload arrays into points. |
| `retrieve()` | Supported | Uses strongly consistent LambdaDB fetches. |
| `query_points()` | Supported | Dense vector query plus simple payload filters. |
| `search()` | Supported | Wrapper around `query_points()`. |
| `delete()` | Limited | Point IDs only. Delete by filter is unsupported. |
| `scroll()` | Limited | Unfiltered scroll without vectors only. |
| `count()` | Limited | Unfiltered collection count only. |

## Payload Indexes

LambdaDB filter fields must be indexed. For the safest Qdrant migration path,
declare those fields at collection creation time:

```python
payload_schema={
    "tenant": models.PayloadSchemaType.KEYWORD,
    "views": models.PayloadSchemaType.INTEGER,
    "score": models.PayloadSchemaType.FLOAT,
    "active": models.PayloadSchemaType.BOOL,
}
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
| `geo` | Unsupported |

`create_payload_index()` is intentionally limited. LambdaDB collection updates
replace `indexConfigs`, so the compatibility client reads the existing configs,
merges the new payload index, and sends the full merged set. LambdaDB currently
applies newly added index configs only to documents written after the change, so
adding a new payload index to a non-empty collection is rejected. Recreate the
collection with `payload_schema` or reingest documents after adding the index.

## Data Mapping

| Qdrant concept | LambdaDB mapping |
| --- | --- |
| point id | document `id`, stringified |
| original numeric id | `_qdrant_id` reserved field |
| unnamed dense vector | `_qdrant_vector` |
| named dense vector `title` | `_qdrant_vector_title` |
| payload fields | top-level document fields |

Payload fields cannot use `id` or the reserved `_qdrant_` prefix.

## Filter Support

| Qdrant filter | Status |
| --- | --- |
| `Filter.must` | Supported |
| `Filter.should` | Supported through LambdaDB bool clauses |
| `Filter.must_not` | Supported |
| `FieldCondition.match=MatchValue` | Supported |
| `FieldCondition.match=MatchAny` | Supported |
| `FieldCondition.match=MatchExcept` | Supported |
| `FieldCondition.range` | Supported |
| `HasIdCondition` | Supported |
| `MatchText` | Unsupported in v1 |
| Geo filters | Unsupported |
| Nested object filters | Unsupported |

## Unsupported In v1

- Local Qdrant mode (`path`, `location=":memory:"`)
- Sparse vectors
- Multi-vector comparators
- Geo payload indexes and geo filters
- Delete by filter
- Filtered scroll
- Filtered count
- Scroll with vectors
- `query_points()` offset
- `score_threshold`
- HNSW/search tuning semantics beyond warnings

## Live Test

LambdaDB live tests are opt-in:

```bash
LAMBDADB_RUN_LIVE_TESTS=1 poetry run pytest tests/integration/test_qdrant_compat_live.py -v
```

Required environment:

```bash
LAMBDADB_PROJECT_API_KEY=...
LAMBDADB_PROJECT_NAME=...
LAMBDADB_BASE_URL=https://api.lambdadb.ai
```

External integration smoke tests are also optional. They run only when the
relevant packages are installed:

```bash
poetry run python -m pip install langchain-qdrant llama-index-vector-stores-qdrant llama-index-core
LAMBDADB_RUN_EXTERNAL_INTEGRATION_TESTS=1 poetry run pytest tests/integration/test_qdrant_compat_external.py -v
```

These tests exercise LangChain and LlamaIndex against the compatibility client
with an in-process fake LambdaDB transport, so they do not require LambdaDB
credentials.

## Design Notes

Internal design notes live in [qdrant-design.md](qdrant-design.md).
