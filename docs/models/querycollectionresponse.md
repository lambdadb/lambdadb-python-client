# QueryCollectionResponse

Documents selected by query.


## Fields

| Field                                                              | Type                                                               | Required                                                           | Description                                                        |
| ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `took`                                                             | *Optional[int]*                                                    | :heavy_minus_sign:                                                 | Elapsed time in milliseconds.                                      |
| `max_score`                                                        | *Optional[float]*                                                  | :heavy_minus_sign:                                                 | Maximum score.                                                     |
| `total`                                                            | *Optional[int]*                                                    | :heavy_minus_sign:                                                 | Total number of documents returned.                                |
| `docs`                                                             | List[[models.QueryCollectionDoc](../models/querycollectiondoc.md)] | :heavy_minus_sign:                                                 | List of documents.                                                 |