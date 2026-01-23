# QueryCollectionResponse

Documents selected by query.


## Fields

| Field                                                              | Type                                                               | Required                                                           | Description                                                        |
| ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `took`                                                             | *int*                                                              | :heavy_check_mark:                                                 | Elapsed time in milliseconds.                                      |
| `max_score`                                                        | *Optional[float]*                                                  | :heavy_minus_sign:                                                 | Maximum score.                                                     |
| `total`                                                            | *int*                                                              | :heavy_check_mark:                                                 | Total number of documents returned.                                |
| `docs`                                                             | List[[models.QueryCollectionDoc](../models/querycollectiondoc.md)] | :heavy_check_mark:                                                 | List of documents.                                                 |
| `is_docs_inline`                                                   | *bool*                                                             | :heavy_check_mark:                                                 | Whether the list of documents is included.                         |
| `docs_url`                                                         | *Optional[str]*                                                    | :heavy_minus_sign:                                                 | Optional download URL for the list of documents.                   |