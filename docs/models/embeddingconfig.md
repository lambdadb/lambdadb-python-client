# EmbeddingConfig

Native embedding configuration for vector fields. Legacy `managedEmbedding` / `managed_embedding` inputs remain supported.


## Fields

| Field                                                  | Type                                                   | Required                                               | Description                                            |
| ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ |
| `provider`                                             | [models.Provider](../models/provider.md)               | :heavy_check_mark:                                     | Embedding provider.                                    |
| `model`                                                | *str*                                                  | :heavy_check_mark:                                     | Embedding model name. See /guides/collections/native-embeddings for the current supported providers and models. |
| `source_field`                                         | *Optional[str]*                                        | :heavy_minus_sign:                                     | Legacy single-text source path. Use exactly one non-null `source_field` or `sources`. |
| `sources`                                              | List[[models.EmbeddingSource](../models/embeddingsource.md)] | :heavy_minus_sign:                               | Ordered source mappings, 1-16 items. OpenAI requires exactly one text source; Cohere accepts text and image sources. |
| `dimensions`                                           | *Optional[int]*                                        | :heavy_minus_sign:                                     | Optional dimensions, 64-4096. OpenAI limits depend on the model; Cohere accepts 256, 512, 768, 1024, 1536 or 2048 and defaults to 2048. |
| `similarity`                                           | [Optional[models.Similarity]](../models/similarity.md) | :heavy_minus_sign:                                     | Optional cosine or euclidean similarity, resolved in stored collection metadata. |

Omitted dimensions and similarity are omitted on the wire. The public similarity
attribute retains its existing cosine default; explicit values are serialized.

Exactly one of `source_field` and `sources` must be non-null; the other may be
omitted or `None` and is omitted on the wire. Provider/model pairs, provider
dimensions, duplicate source paths, and image limits are validated by the server.
See [native embedding sources](../native-embedding-sources.md).
