# Read limits and stored text

This scoped update uses these exact source revisions:

- [OpenAPI, docs `94a7b71613a3bf217a370d5117b3ff6ddfbae851`](https://github.com/lambdadb/docs/blob/94a7b71613a3bf217a370d5117b3ff6ddfbae851/reference/api/openapi.json).
- [Backend `0a54b6ecb483ce7df9677ba2071a491f9f9879c9`](https://github.com/lambdadb/lambdadb/commit/0a54b6ecb483ce7df9677ba2071a491f9f9879c9),
  including [query limits #469](https://github.com/lambdadb/lambdadb/pull/469),
  [query result spooling #472](https://github.com/lambdadb/lambdadb/pull/472),
  [stored text paths #481](https://github.com/lambdadb/lambdadb/pull/481), and
  [Fetch/List limits #493](https://github.com/lambdadb/lambdadb/pull/493).

These pins identify source contracts, not deployment or package publication.
The base Data Versioning `API_CONTRACT_REVISION` remains
`c44180406c05b1a9043d8516e7c7f60df91fc9a7`; this scoped update does not claim
full SDK regeneration or adoption of every intervening OpenAPI constraint.

## Counts and defaults

| Control | Server range | Omitted default |
| --- | --- | --- |
| Query `size` | 0-1000; zero requires at least one facet | 10 |
| Dense `knn.k` | 1-1000, independent of final size and candidate budget | Supply explicitly |
| Bayesian `candidate_size` | `size <= candidate_size <= 1000`, positive | Required without rerank |
| Rerank `candidate_size` | `size <= candidate_size <= 1000`; rerank requires positive size | `max(50, size)` |
| Fetch `ids` | 1-1000 nonblank IDs | Required |
| List `size` (GET or POST) | 1-1000 | 100 |
| Facet bucket `size` | 1-100 | 10 |

Python candidate arguments serialize as `candidateSize`. With Bayesian reranking,
omit the top-level candidate budget and use the budget inside `rerank`. The SDK
never increases `knn.k` implicitly. Rerank UTF-8, combined input, and deadline
budgets still apply even when the candidate count is valid.

Direct Query, Fetch, and List calls continue passing counts to the server, with
the existing local rerank checks. New OpenAPI empty-list/object constraints do
not add client-side rejection to document writes. Existing validation order,
error classification, and retry policies are preserved. Invalid server input
continues to raise `BadRequestError`; result-storage admission HTTP 503 uses the
existing `ServiceUnavailableError` mapping.

Document page iterators request at most 1000 items at a time and can combine
multiple requests into a larger logical page. Their default logical page size
remains 100. Every request retains the selected ref, filters, and projection.
Use an immutable Tag for a stable multi-page export.
Counts above 100 require a server build containing the corresponding limit
increase. For an older server, keep document iterator page sizes at 100 or less.

## Stored strings without source indexes

Declare only the generated vector if the source needs no search index:

```python
client.collections.create(
    collection_name="articles",
    index_configs={
        "vector": {
            "type": "vector",
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "sourceField": "article.body",
            },
        },
    },
)
articles = client.collection("articles")
articles.docs.upsert(docs=[{"id": "one", "article": {"body": "Restore a saved version."}}])
response = articles.query(
    query={"knn": {"field": "vector", "queryText": "Restore a version", "k": 20}},
    size=10,
    consistent_read=True,
    rerank={
        "provider": "typesafe",
        "model": "jev-1.13.0",
        "query_text": "Restore a version",
        "fields": ["article.body"],
    },
)
```

Both `embedding.sourceField` and `rerank.fields` select stored scalar strings
through objects. The leaf and its ancestors need no index declarations. Declared
leaves must be `text` or `keyword`, and declared ancestors must be objects.
Arrays, wildcard expansion, whole-object inputs, and blank path segments are
unsupported. The SDK passes paths through; the server validates actual values.

For embeddings, a missing source on full upsert skips generation and does not
retain an old vector; explicit null and other non-string values on unindexed
paths are rejected. Partial updates merge with the stored document first, reuse
an unchanged source's vector, and regenerate it when the source text changes.
Reranking skips missing/null selected values, but every candidate needs at least
one nonblank selected string. Invalid candidates fail before provider dispatch,
including with `on_failure="returnOriginal"`.

Use `knn.queryText` for native vector retrieval. The server validates the query
DSL; query dictionaries remain opaque to the SDK.

## Result sizes and downloads

Query no longer has a 64 MiB aggregate uncompressed public response limit. Large
results retain the existing `isDocsInline: false`, empty `docs`, and `docsUrl`
envelope. The URL returns a gzip-encoded JSON array. High-level collection
methods download and parse it automatically, preserving document order, scores,
facets, rerank metadata, and List page tokens. Low-level methods return the URL
without downloading it.

The current SDK materializes downloaded bytes, JSON, and result models in
memory; it does not provide a streaming result iterator. Project only needed
fields and avoid requesting vectors when their values are unnecessary. Fetch
still enforces a 64 MiB projected JSON budget per node and returns HTTP 400
without partial results when exceeded. Requesting 1000 IDs does not guarantee
that the selected bodies fit that budget.

## Public vector configuration

Dense vector configuration follows the pinned OpenAPI: dimensions are 64-4096
and similarity is `cosine` or `euclidean`. This applies to caller-provided and
native embedding configuration, including collection response parsing. See
[vector configuration](vector-configuration.md) for scope and migration from
previously accepted settings.

Native fields use `knn.queryText`. As of lambdadb OpenAPI `1c3e7d4`, native
fields also accept `knn.queryInputs` and a raw `knn.queryVector`; see
[native embedding sources](native-embedding-sources.md).

A candidate budget of 1000 is a request-count maximum, not a guarantee that
reranking finishes within a deployment's deadline. Production verification on
2026-10-26 recorded HTTP 408 for 1000 actual candidates with a 2000 ms server
stage budget; `returnOriginal` returned fallback with zero scored candidates.
[SDK PR #54](https://github.com/lambdadb/lambdadb-python-client/pull/54) records
those bounded checks separately from successful 1000-document retrieval.
