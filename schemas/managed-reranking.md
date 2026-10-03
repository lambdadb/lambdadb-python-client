# Managed reranking contract maintenance

`managed-reranking.json` is a scoped schema adapted from backend DTOs, service
validation, tests and the managed reranking design. It is pinned to backend
`develop` revision
[55d888299fee44466326a9db8016af9811ade13b](https://github.com/lambdadb/lambdadb/commit/55d888299fee44466326a9db8016af9811ade13b),
which includes [PR #435](https://github.com/lambdadb/lambdadb/pull/435) and
[PR #442](https://github.com/lambdadb/lambdadb/pull/442).
The local reference checkout was inspected at
`a5e06d49be06d95dc5f4046aeecaf51f8a7733c0`; comparison to the pinned develop
revision showed only the subsequent analyzer extension, with no reranking
contract changes. `source.files` records SHA-256 hashes of the inspected files.
These pins identify source contracts, not deployment.

The upstream OpenAPI inspected at docs revision
`961561c379acb079aec20191e13b89809ef096e9` does not contain reranking. This is
not an extracted upstream OpenAPI fragment and does not change the SDK's base
`API_CONTRACT_REVISION` or claim adoption of unrelated intervening APIs.
The repository has no active full Speakeasy generation workflow.

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

Upstream OpenAPI propagation, live SDK validation on the intended environment,
backend usage ingestion/rate-card adoption and approved effective-time input/output
rates remain separate dependencies. No rate is inferred or copied from embeddings.
Publication and deployment require separate authorization and release checks.
