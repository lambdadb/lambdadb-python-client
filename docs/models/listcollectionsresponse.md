# ListCollectionsResponse

A list of collections matched with a projectName.


## Fields

| Field                                                              | Type                                                               | Required                                                           | Description                                                        |
| ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `collections`                                                      | List[[models.CollectionResponse](../models/collectionresponse.md)] | :heavy_check_mark:                                                 | N/A                                                                |
| `next_page_token`                                                  | *Optional[str]*                                                    | :heavy_minus_sign:                                                 | Opaque token for the next page. Absent on the last page.           |