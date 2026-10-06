# EmbeddingConfig

Native embedding configuration for vector fields. Existing managed embedding inputs remain supported.


## Fields

| Field                                                  | Type                                                   | Required                                               | Description                                            |
| ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ |
| `provider`                                             | [models.Provider](../models/provider.md)               | :heavy_check_mark:                                     | Embedding provider.                                    |
| `model`                                                | *str*                                                  | :heavy_check_mark:                                     | Embedding model name. See /guides/collections/managed-embeddings for the current supported providers and models. |
| `source_field`                                         | *str*                                                  | :heavy_check_mark:                                     | Source text field name used to generate embeddings.    |
| `dimensions`                                           | *Optional[int]*                                        | :heavy_minus_sign:                                     | Resolved embedding dimensions. Optional in requests and resolved in stored collection metadata. |
| `similarity`                                           | [Optional[models.Similarity]](../models/similarity.md) | :heavy_minus_sign:                                     | Resolved vector similarity metric. Optional in requests and resolved in stored collection metadata. |

Omitted dimensions and similarity are omitted on the wire. The public similarity
attribute retains its existing cosine default; explicit values are serialized.
