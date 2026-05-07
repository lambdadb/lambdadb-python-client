# EmbeddingConfig

Managed embedding configuration for vector fields.


## Fields

| Field                                                  | Type                                                   | Required                                               | Description                                            |
| ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ |
| `provider`                                             | [models.Provider](../models/provider.md)               | :heavy_check_mark:                                     | Embedding provider.                                    |
| `model`                                                | *str*                                                  | :heavy_check_mark:                                     | Embedding model name. See /guides/collections/managed-embeddings for the current supported providers and models. |
| `source_field`                                         | *str*                                                  | :heavy_check_mark:                                     | Source text field name used to generate embeddings.    |
| `dimensions`                                           | *Optional[int]*                                        | :heavy_minus_sign:                                     | Resolved embedding dimensions. Optional in requests and resolved in stored collection metadata. |
| `similarity`                                           | [Optional[models.Similarity]](../models/similarity.md) | :heavy_minus_sign:                                     | Resolved vector similarity metric. Optional in requests and resolved in stored collection metadata. |
