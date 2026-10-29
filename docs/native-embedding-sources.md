# Native embedding sources and Cohere providers

This scoped update follows the public
[OpenAPI at lambdadb `1c3e7d453cca296a7b2af85a375b4c5016504101`](https://github.com/lambdadb/lambdadb/blob/1c3e7d453cca296a7b2af85a375b4c5016504101/api/openapi.json),
the `main` merge that includes
[Cohere native multimodal embeddings and text reranking #483](https://github.com/lambdadb/lambdadb/pull/483)
and [the server-managed `id` in collection `indexConfigs` #515](https://github.com/lambdadb/lambdadb/pull/515).
The public OpenAPI moved from `lambdadb/docs` to `lambdadb/lambdadb` in
[#498](https://github.com/lambdadb/lambdadb/pull/498); its first revision is
identical to the previously pinned docs revision
`94a7b71613a3bf217a370d5117b3ff6ddfbae851`. This pin identifies the source
contract, not deployment in any API environment. Cohere requests also require
the server environment to configure Cohere credentials.

## Source mappings

`EmbeddingConfig` now accepts either the legacy `sourceField` or an ordered
`sources` list. Exactly one of them must be non-null.

```python
from lambdadb import models

client.collections.create(
    collection_name="products",
    index_configs={
        "embedding": {
            "type": "vector",
            "embedding": {
                "provider": "cohere",
                "model": "embed-v5.0-pro",
                "sources": [
                    {"field": "title", "type": "text"},
                    {"field": "media.photos", "type": "image"},
                ],
                "dimensions": 1024,
            },
        },
    },
)
```

| Provider | Models | Sources | Dimensions |
| --- | --- | --- | --- |
| `openai` | `text-embedding-3-small`, `text-embedding-3-large`, `text-embedding-ada-002` | `sourceField`, or exactly one `text` source | 64-4096 within the model maximum |
| `cohere` | `embed-v5.0-pro`, `embed-v5.0-fast` | `sourceField`, or 1-16 `text`/`image` sources | 256, 512, 768, 1024, 1536 or 2048; defaults to 2048 |

Each source is a dotted path in the original stored JSON; it does not need an
index declaration. Text sources are scalar strings. Cohere image sources are
strings or flat string arrays, expanded in place into one combined vector.
Images must be supported data URIs or public HTTPS URLs. Each input is limited
to 16 effective parts, 8 images, 1 MiB of decoded image bytes, and 4,194,304
pixels per image. Missing sources and empty image arrays are skipped.

The SDK validates the request shape: one non-null source selection, 1-16
sources, nonblank paths, and `text`/`image` types. It intentionally leaves
provider/model pairs, provider dimensions, duplicate paths, image URLs and
formats, and byte/pixel limits to the server. Collection responses preserve the
stored `sources` list and resolved dimensions/similarity.

## Documents and direct vectors

Native embedding fields now also accept a caller-supplied vector. An explicit
vector takes precedence over inference and skips image retrieval for that
binding; source fields and a direct vector may coexist.

- `upsert`: supply source fields to generate a vector, or a vector to skip
  inference. A full replacement with neither does not preserve the previous vector.
- `update`: equivalent source input reuses the existing vector; changed source
  input regenerates it; removing the last source removes an inherited vector.
  Metadata-only updates preserve direct vectors when raw source fields are unchanged.
- `bulk_upsert`: now supported for native embedding collections with
  caller-supplied vectors. Bulk never generates embeddings: a present source
  without its vector fails before any documents are committed.

The SDK passes document bodies through unchanged.

## Query inputs

Queries remain free-form dictionaries. On a native field, each `knn` leg takes
exactly one of `queryText`, `queryInputs`, or `queryVector`:

```python
response = client.collection("products").query(
    query={"knn": {
        "field": "embedding",
        "queryInputs": [
            {"type": "text", "value": "red shoes"},
            {"type": "image", "value": "https://example.com/shoe.png"},
        ],
        "k": 10,
    }},
    size=10,
)
```

Cohere accepts mixed ordered parts; OpenAI accepts one text part. `queryInputs`
uses the same part, image and byte limits as document inputs. A raw
`queryVector` is accepted on native fields and skips inference. The server
validates these rules.

## Server-managed `id` in `indexConfigs`

Collection responses include the server-managed top-level `id` field as
`{"type": "keyword"}`. Create and update requests may omit it or send exactly
that configuration, so `index_configs` read from `collections.get()` can be sent
back unchanged as the base of an update. A schema containing only `id` is
accepted. The server rejects any other `id` configuration, `id` inside an object
field, and other reserved internal field names. The SDK adds no local check for
these rules. Servers without #515 reject a returned `id` as a reserved field
name; omit it when targeting such a server.

## Reranking

Native reranking adds `cohere` / `rerank-v5.0-pro` and `rerank-v5.0-fast`.
See [native reranking](native-reranking.md#cohere-reranking).
