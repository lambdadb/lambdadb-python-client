# RerankResponse

Generated from the [pinned contract](../../schemas/native-reranking.json).

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `status` | `Literal['applied', 'skipped', 'fallback']` | Yes | Check status before interpreting scores: fallback keeps search scores. |
| `provider` | `str` | Yes | Requested provider. |
| `model` | `str` | Yes | Requested model. |
| `resolved_model` | `Optional[str]` | No | Resolved model when reported by the provider. |
| `candidate_count` | `int` | Yes | Actual unique candidates in the logical stage; not a guaranteed count or billing unit. |
| `scored_count` | `int` | Yes | Complete accepted scores; equals candidateCount on applied, zero on skipped/fallback. |
| `took` | `int` | Yes | Rerank stage duration in milliseconds, excluding candidate hydration. |
| `criteria_version` | `Optional[Literal['default-relevance-v1', 'custom']]` | No | Only on applied results when reported. custom identifies caller-supplied criteria, not a content hash or unique version. |
| `reason` | `Optional[str]` | No | Skipped/fallback reason: noCandidates, timeout, rateLimit, unavailable, invalidResponse or credentials. |

See [native reranking](../native-reranking.md) for examples and server validation.
