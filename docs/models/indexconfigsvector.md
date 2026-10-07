# IndexConfigsVector


## Fields

| Field                                                  | Type                                                   | Required                                               | Description                                            |
| ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ |
| `type`                                                 | [models.TypeVector](../models/typevector.md)           | :heavy_check_mark:                                     | N/A                                                    |
| `managed_embedding`                                    | *Optional[bool]*                                       | :heavy_minus_sign:                                     | Omit with embedding for native embeddings; true remains supported. False forbids embedding. |
| `dimensions`                                           | *Optional[int]*                                        | :heavy_minus_sign:                                     | Vector dimensions for caller-provided vector fields.         |
| `similarity`                                           | [Optional[models.Similarity]](../models/similarity.md) | :heavy_minus_sign:                                     | Vector similarity metric for caller-provided vector fields.  |
| `embedding`                                            | [Optional[models.EmbeddingConfig]](../models/embeddingconfig.md) | :heavy_minus_sign:                            | Native embedding configuration for vector fields.     |

## Validation

For native embedding vector fields, provide `embedding` and omit `managed_embedding`, or set it to `True` for legacy compatibility. Top-level `dimensions` and `similarity` are not allowed.

For caller-provided vector fields, omit both `embedding` and `managed_embedding`, or set `managed_embedding=False`. `dimensions` is required and must be between 1 and 4096, and `embedding` is not allowed.

See [native embeddings](../bayesian-native-embeddings.md) for create/update examples and the exact contract pin.
