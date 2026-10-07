# Native reranking

Native reranking is an optional **per-query** stage after retrieval, global
merge, deduplication and hydration. It is not a collection setting. This source
checkout supports `typesafe` / `jev-1.13.0` on a compatible server. LambdaDB
manages provider credentials; supply your normal LambdaDB project API key, not
a Jev API key. Omitting `rerank` or passing `None` preserves existing search
behavior. The SDK omits optional `None` values on the wire.

## Default criteria

Assume the collection has stored scalar text fields `title` and `body`:

```python
from lambdadb import models

response = client.collection("articles").query(
    query={"queryString": {"query": "body:restore"}},
    size=10,
    fields={"include": ["id", "title"]},
    rerank=models.RerankConfig(
        provider="typesafe",
        model="jev-1.13.0",
        query_text="How do I restore a previous collection version?",
        fields=["title", "body"],
        candidate_size=50,
    ),
)

if response.rerank is not None:
    print(response.rerank.status, response.rerank.reason)
for item in response.results:
    print(item.doc["id"], item.score, item.retrieval_score)
```

`Collection.query_async()`, `Collections.query()` and `Collections.query_async()`
accept the same `rerank` argument. Dictionary inputs use Python names such as
`query_text`, `candidate_size`, and `on_failure`, matching
[RerankConfigTypedDict](models/rerankconfig.md); model validation also accepts
the wire aliases `queryText`, `candidateSize`, and `onFailure`.
Both high-level methods automatically download offloaded `docsUrl` results and
preserve scores and rerank metadata. Low-level methods return the URL without
fetching it. Use `response.results` for envelopes; `response.documents` contains
only document bodies and excludes score metadata.

## Custom criteria

Custom descriptions replace the default descriptions for this request. They
must be ordered from lowest to highest relevance; ordering is the caller's
responsibility. For example:

```python
response = client.collection("articles").query(
    query={"queryString": {"query": "body:restore"}},
    size=10,
    rerank={
        "provider": "typesafe",
        "model": "jev-1.13.0",
        "query_text": "How do I restore a previous collection version?",
        "fields": ["title", "body"],
        "criteria": [
            "Does not address restoring a collection version.",
            "Partly explains how to restore a collection version.",
            "Fully explains how to restore a collection version.",
        ],
        "on_failure": "returnOriginal",
    },
)
```

Accept 2–10 distinct nonblank strings, at most 2 KiB each and 8 KiB total in
UTF-8. Text is preserved exactly. Omitted/null `criteria` selects the default
ten-level criteria; an empty array is invalid. Custom N-level criteria use
uniform normalized weights `i/(N-1)`. Even explicitly supplying the ten default
descriptions selects custom weights and differs from omission. No caller
weights, thresholds, persistent criteria registry, or custom version/hash is
supported. These descriptions illustrate the API, not a validated domain rubric.

## Request and candidate counts

See [RerankConfig](models/rerankconfig.md) for field types and required values.
`provider`, `model`, nonblank `queryText` and `fields` are required. Query text
is limited to 8 KiB UTF-8, including when retrieval uses raw vectors.
`fields` is an ordered list of 1–8 unique stored scalar text paths. The backend
accepts scalar strings on text or keyword paths, including nested object paths.
It validates the collection configuration and actual candidate values; a
non-string value or a candidate with no nonblank selected text is an error.
Rerank input fields are independent of public result projection: selecting
`body` for reranking does not force `body` into returned documents.

| Control | Meaning |
| --- | --- |
| `size` | Final number of returned documents; must be positive with reranking, at most 100. Server default is 10. |
| `knn.k` | Candidate count for that vector retrieval leg. The SDK never rewrites it. |
| `rerank.candidateSize` | Upper bound on the merged rerank pool; defaults to `max(50, size)`, with `size <= candidateSize <= 100`. |

For vector-only retrieval, increase `knn.k` explicitly when a deeper pool is
wanted. A vector leg with `k=20` can also join a lexical leg in a larger merged
pool; no rule requires every leg to have `k >= candidateSize`. Available unique
candidates may be fewer than the cap. Sparse-vector and lexical queries use
planned retrieval depth and have no separate dense-vector `k` setting.

Reranking requires a scoring retrieval query. It rejects query-less/filter-only
requests and any explicit `sort`, including an empty list. It does not expand
[facet query support](keyword-facets.md): vector/hybrid facets remain unsupported.
For supported lexical requests, facets count all matching documents rather than
only reranked candidates, including on fallback. Legacy facet-only requests with
`size=0` remain supported when reranking is absent.

The SDK validates request shape, UTF-8 limits, size/candidate relationships and
sort conflicts without injecting defaults. The server remains authoritative for
the opaque query DSL, field storage/type, input materialization limits, model
availability and admission. Invalid requests are validated before empty-result
handling. The server also limits rendered candidate text to 16 KiB and combined
query/candidate/criteria text to 256 KiB, without silently truncating it.

## Response scores and status

`score` is the value used for final ordering. On `applied` responses it is a
finite evaluation score in `[0, 1]`, **not a calibrated relevance probability**.
The original retrieval/fusion score is `retrievalScore` on the same envelope,
not inside `doc`. The SDK preserves numeric zero, double precision and server
ordering, including exact ties; it never sorts or rounds results again.
`maxScore` is the maximum final returned score and is omitted on empty results.
`total` is the returned document count, not the corpus match count.

| Status | Scores and metadata |
| --- | --- |
| `applied` | Final rerank scores and original `retrievalScore`; `scoredCount == candidateCount`. `criteriaVersion` identifies `default-relevance-v1` or `custom`. |
| `skipped` | Empty pool: `reason=noCandidates`, both counts zero, no `maxScore`, `retrievalScore` or `criteriaVersion`. |
| `fallback` | Retained original candidate order and search scores; `scoredCount=0`, reason present, no `retrievalScore` or `criteriaVersion`. No partial rerank results are exposed. |
| No reranking | Original search scores; no top-level `rerank` or `retrievalScore`. |

Top-level [RerankResponse](models/rerankresponse.md) includes required `status`,
requested `provider`/`model`, `candidateCount`, `scoredCount`, and stage `took`
in milliseconds. `resolvedModel`, `reason` and `criteriaVersion` are optional
in the DTO. Stage `took` excludes hydration; top-level response `took` covers
the complete request. `criteriaVersion` is emitted only for applied scores.
`custom` marks caller-supplied criteria, not their identity: retain the request's
criteria to reproduce a result. Scores from different criteria or models are
not directly comparable. The unsupported names `rerankScore` and `rubricVersion`
are not aliases.

## Failure handling

`onFailure` defaults to `error`; optional `returnOriginal` returns the first
`size` documents from the retained expanded candidate pool if the provider stage
fails. Hybrid fallback can differ from a separate legacy query with a smaller
candidate depth. Search scores on fallback are not constrained to `[0, 1]`.

| Failure | Behavior |
| --- | --- |
| Provider timeout, rate limit, unavailable service, invalid/incomplete scores or credential rejection | Apply `onFailure` to the whole stage; fallback reasons are `timeout`, `rateLimit`, `unavailable`, `invalidResponse`, or `credentials`. No provider credentials are returned. |
| Invalid input or candidate text, disabled model, quota/configuration or admission rejection | Return the server error; never fallback. |
| Retrieval, hydration, version routing or authorization failure | Preserve the existing error; never fallback. |
| Caller cancellation or exhausted overall deadline | Cancel pending provider work; do not start fallback beyond the deadline. |

The SDK passes policies and server outcomes through. It does not call the
provider directly, implement its own fallback, or infer success from HTTP 200:
check `rerank.status`.
