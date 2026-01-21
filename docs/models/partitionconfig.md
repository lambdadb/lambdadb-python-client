# PartitionConfig


## Fields

| Field                                              | Type                                               | Required                                           | Description                                        |
| -------------------------------------------------- | -------------------------------------------------- | -------------------------------------------------- | -------------------------------------------------- |
| `field_name`                                       | *Optional[str]*                                    | :heavy_minus_sign:                                 | Partition field name.                              |
| `data_type`                                        | [Optional[models.DataType]](../models/datatype.md) | :heavy_minus_sign:                                 | Partition field data type.                         |
| `num_partitions`                                   | *Optional[int]*                                    | :heavy_minus_sign:                                 | The number of partitions.                          |