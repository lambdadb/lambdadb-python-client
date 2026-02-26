# DeleteDocsRequestBody


## Fields

| Field                                                            | Type                                                             | Required                                                         | Description                                                      |
| ---------------------------------------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------- |
| `ids`                                                            | List[*str*]                                                      | :heavy_minus_sign:                                               | A list of document IDs.                                          |
| `query_filter`                                                   | Dict[str, *Any*]                                                 | :heavy_minus_sign:                                               | Query filter (preferred in the SDK).                             |
| `filter_`                                                        | Dict[str, *Any*]                                                 | :heavy_minus_sign:                                               | Query filter (legacy; prefer `query_filter`).                    |
| `partition_filter`                                               | [Optional[models.PartitionFilter]](../models/partitionfilter.md) | :heavy_minus_sign:                                               | N/A                                                              |