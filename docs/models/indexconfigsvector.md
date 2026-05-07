# IndexConfigsVector


## Fields

| Field                                                  | Type                                                   | Required                                               | Description                                            |
| ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ |
| `type`                                                 | [models.TypeVector](../models/typevector.md)           | :heavy_check_mark:                                     | N/A                                                    |
| `managed_embedding`                                    | *Optional[bool]*                                       | :heavy_minus_sign:                                     | Set to true for managed embedding vector fields, or false/omit for unmanaged vector fields. |
| `dimensions`                                           | *Optional[int]*                                        | :heavy_minus_sign:                                     | Vector dimensions for unmanaged vector fields.         |
| `similarity`                                           | [Optional[models.Similarity]](../models/similarity.md) | :heavy_minus_sign:                                     | Vector similarity metric for unmanaged vector fields.  |
| `embedding`                                            | [Optional[models.EmbeddingConfig]](../models/embeddingconfig.md) | :heavy_minus_sign:                            | Managed embedding configuration for vector fields.     |

## Validation

For managed embedding vector fields, set `managed_embedding=True` and provide `embedding`. Top-level `dimensions` and `similarity` are not allowed.

For unmanaged vector fields, omit `managed_embedding` or set it to `False`. `dimensions` is required and must be between 1 and 4096, and `embedding` is not allowed.
