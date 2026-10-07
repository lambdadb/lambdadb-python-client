# RerankConfig

Generated from the [pinned contract](../../schemas/native-reranking.json).

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `provider` | `Literal['typesafe']` | Yes | Native reranking provider. The server handles provider credentials; no customer provider API key is required. |
| `model` | `Literal['jev-1.13.0']` | Yes | Explicit native reranking model. |
| `query_text` | `str` | Yes | Nonblank query text, at most 8 KiB UTF-8; required even for raw-vector retrieval. |
| `fields` | `List[str]` | Yes | Ordered unique stored scalar text paths (text or keyword). The server validates collection paths and candidate values. |
| `candidate_size` | `Optional[int]` | No | Merged rerank candidate cap; defaults to max(50, size). Must be at least size; does not change knn.k. |
| `on_failure` | `Optional[Literal['error', 'returnOriginal']]` | No | Defaults to error. returnOriginal applies only to whole-stage provider failures, not input, quota, admission, retrieval or authorization errors. |
| `criteria` | `Optional[List[str]]` | No | Distinct nonblank descriptions ordered lowest to highest relevance. Omitted/null uses default criteria; at most 2 KiB each and 8 KiB total UTF-8. |

See [native reranking](../native-reranking.md) for examples and server validation.
