# RerankConfig

Generated from the [pinned contract](../../schemas/native-reranking.json).

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `provider` | `Literal['typesafe', 'cohere']` | Yes | Native reranking provider. The server handles provider credentials; no customer provider API key is required. |
| `model` | `Literal['jev-1.13.0', 'rerank-v5.0-pro', 'rerank-v5.0-fast']` | Yes | Explicit native reranking model; typesafe uses jev-1.13.0, cohere uses rerank-v5.0-pro or rerank-v5.0-fast. |
| `query_text` | `str` | Yes | Nonblank query text, at most 8 KiB UTF-8; required even for raw-vector retrieval. |
| `fields` | `List[str]` | Yes | Ordered unique stored scalar string paths through objects; index configs are optional. Declared leaves must be text or keyword. The server validates ancestors and candidate values before provider dispatch. |
| `candidate_size` | `Optional[int]` | No | Merged rerank candidate cap, up to 1000; defaults to max(50, size). Must be at least size; does not change knn.k. |
| `on_failure` | `Optional[Literal['error', 'returnOriginal']]` | No | Defaults to error. returnOriginal applies only to whole-stage provider failures, not input, quota, admission, retrieval or authorization errors. |
| `criteria` | `Optional[List[str]]` | No | TypeSafe/Jev only; Cohere requires omitted/null. Distinct nonblank descriptions ordered lowest to highest relevance. Omitted/null uses default criteria; at most 2 KiB each and 8 KiB total UTF-8. |

See [native reranking](../native-reranking.md) for examples and server validation.
