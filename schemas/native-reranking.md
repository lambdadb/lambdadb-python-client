# Native reranking contract maintenance

`native-reranking.json` is a scoped adaptation of backend DTOs, service
validation, tests, and the public OpenAPI. It is pinned to backend
[`0a54b6ecb483ce7df9677ba2071a491f9f9879c9`](https://github.com/lambdadb/lambdadb/commit/0a54b6ecb483ce7df9677ba2071a491f9f9879c9)
and [OpenAPI at docs revision `94a7b71613a3bf217a370d5117b3ff6ddfbae851`](https://github.com/lambdadb/docs/blob/94a7b71613a3bf217a370d5117b3ff6ddfbae851/reference/api/openapi.json).
`source.files` records SHA-256 hashes of files read from the exact backend commit;
`source.openapi` records the docs revision, path, and relevant JSON pointers.
These pins identify source contracts, not deployment.

The 1000-candidate limit and optional index declarations for stored rerank paths
supersede the earlier backend `55d888299fee44466326a9db8016af9811ade13b`
contract. The scoped schema preserves existing SDK optional response fields and
validation boundaries; it is not an exact OpenAPI extraction. The base
`API_CONTRACT_REVISION` remains unchanged. See
[read limits and stored text](../docs/read-limits-and-stored-text.md) for scope
and the public vector configuration contract. There is no
active full Speakeasy generation workflow.

Generate the scoped models, TypedDicts and model references with:

```bash
python3 scripts/generate_reranking.py
python3 scripts/generate_reranking.py --check
```

The schema supplies types, required/optional fields, aliases, enums, list limits,
UTF-8 bounds and descriptions. The generator implements the corresponding
uniqueness, nonblank, UTF-8 and path-shape checks, preserving original text.
`candidateSize`, `onFailure` and `criteria` stay optional and nullable; Python
`None` is omitted during serialization and does not inject client defaults.
Response DTO optional fields remain optional, including `criteriaVersion` on
synthetic applied results in backend tests. Runtime Jev applied results report
`default-relevance-v1` or `custom`; skipped/fallback omit it.

When updating the contract, inspect the exact upstream DTO/service/test revision,
update the schema and provenance together, regenerate, and review the complete
diff. Query-body/envelope wiring, public exports, high/low-level method signatures
and presigned response hydration are maintained explicitly; they are not full-SDK
generated outputs. Run `tests/test_reranking.py`, the non-integration suite,
mypy, pylint and both generation checks. The wire tests cover sync/async,
model/dictionary inputs, default/custom 2/3/10 criteria, inline/offloaded results,
zero and double precision, original ordering, legacy omission, skip/fallback,
UTF-8 boundaries and unsupported options. They do not call a paid provider.

The SDK does not mirror the opaque query DSL or fetch collection configuration to
prevalidate paths. Server validation handles filter-only queries, scalar storage,
projection, quota, enabled models, admission and provider failures. It does not
rewrite `knn.k`, implement fallback, re-sort results or expand facets support.

## Repository boundaries and remaining dependencies

This Python SDK repository contains no CLI, console UI, AWS Secret configuration,
customer usage ingestion or rate-card/billing code. Those consumers are separate.
No client-side provider key, billing unit, rate, or Secret setting is added.

The backend source already aggregates complete successful batch usage into one
`modelCategory=rerank`, `operationType=query`, `provider=typesafe`,
`model=jev-1.13.0` token event. Its tests cover aggregation and suppression on
failure/fallback/incomplete usage. `providerRequestCount` is diagnostic rather
than a billing unit. The supplied shared-dev smoke record reports 38 contract
checks and per-request events; that is evidence about the server run, not live
verification of this SDK or complete quality/load/failure/settlement validation.

Environment validation is recorded separately in
[SDK PR #54](https://github.com/lambdadb/lambdadb-python-client/pull/54). Backend
usage ingestion/rate-card adoption and approved effective-time input/output rates
remain separate dependencies. No rate is inferred or copied from embeddings.
Publication and deployment require separate authorization and release checks.
