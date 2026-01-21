# DeleteDocsRequestBody


## Fields

| Field                                                            | Type                                                             | Required                                                         | Description                                                      |
| ---------------------------------------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------- |
| `ids`                                                            | List[*str*]                                                      | :heavy_minus_sign:                                               | A list of document IDs.                                          |
| `filter_`                                                        | Dict[str, *Any*]                                                 | :heavy_minus_sign:                                               | Query filter.                                                    |
| `partition_filter`                                               | [Optional[models.PartitionFilter]](../models/partitionfilter.md) | :heavy_minus_sign:                                               | N/A                                                              |