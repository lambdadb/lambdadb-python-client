# QueryCollectionResponse

Documents selected by query.


## Fields

| Field                                                              | Type                                                               | Required                                                           | Description                                                        |
| ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `took`                                                             | *int*                                                              | :heavy_check_mark:                                                 | Elapsed time in milliseconds.                                      |
| `max_score`                                                        | *float*                                                            | :heavy_check_mark:                                                 | Maximum score.                                                     |
| `total`                                                            | *int*                                                              | :heavy_check_mark:                                                 | Total number of documents returned.                                |
| `docs`                                                             | List[[models.QueryCollectionDoc](../models/querycollectiondoc.md)] | :heavy_check_mark:                                                 | List of documents.                                                 |