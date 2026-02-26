# QueryCollectionResponse

Documents selected by query.


## Fields

| Field                                                              | Type                                                               | Required                                                           | Description                                                        |
| ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `took`                                                             | *int*                                                              | :heavy_check_mark:                                                 | Elapsed time in milliseconds.                                      |
| `max_score`                                                        | *Optional[float]*                                                  | :heavy_minus_sign:                                                 | Maximum score.                                                     |
| `total`                                                            | *int*                                                              | :heavy_check_mark:                                                 | Total number of documents returned.                                |
| `results`                                                          | List[[models.QueryCollectionDoc](../models/querycollectiondoc.md)] | :heavy_check_mark:                                                 | List of result items (each has `.doc`, `.score`, etc.).            |
| `is_docs_inline`                                                   | *bool*                                                             | :heavy_check_mark:                                                 | Whether the list of documents is included.                         |
| `docs_url`                                                         | *Optional[str]*                                                    | :heavy_minus_sign:                                                 | Optional download URL for the list of documents.                    |

## Properties

| Property      | Type                   | Description                                                                 |
| ------------- | ---------------------- | --------------------------------------------------------------------------- |
| `documents`   | List[Dict[str, *Any*]] | List of document bodies only (convenience). Use when you don't need score.  |

**Response access:** Use `response.results` when you need score or per-item metadata; use `response.documents` when you only need the document bodies. The deprecated property `docs` still returns the same as `results` for backward compatibility.