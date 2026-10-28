# EmbeddingSource

Ordered source mapping for a native embedding field.


## Fields

| Field   | Type                                                         | Required           | Description                                                                          |
| ------- | ------------------------------------------------------------ | ------------------ | ------------------------------------------------------------------------------------ |
| `field` | *str*                                                        | :heavy_check_mark: | Unique dotted path in the original stored JSON; no index declaration is required.    |
| `type`  | [models.EmbeddingSourceType](../models/embeddingsourcetype.md) | :heavy_check_mark: | `text` for a scalar string; `image` (Cohere only) for a string or flat string array. |

The SDK checks the field shape. Path uniqueness, image URL/data URI format, and
byte or pixel limits are validated by the server.
