# QueryCollectionDoc


## Fields

| Field                      | Type                       | Required                   | Description                |
| -------------------------- | -------------------------- | -------------------------- | -------------------------- |
| `retrieval_score` | Optional[float] | No | Original retrieval/fusion score, only on applied reranking; same envelope as score, outside doc. |
| `collection`               | *str*                      | :heavy_check_mark:         | Collection name.           |
| `score`                    | *Optional[float]*          | :heavy_minus_sign:         | Final ordering score; applied reranking uses evaluation values in [0, 1], otherwise retrieval/fusion scores. Not a relevance probability. |
| `doc`                      | Dict[str, *Any*]           | :heavy_check_mark:         | N/A                        |

See [managed reranking](../managed-reranking.md) for score meaning, examples and failure semantics.
