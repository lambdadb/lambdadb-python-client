# UpdateCollectionRequestBody

Provide at least one field. `tags={}` clears all metadata tags.

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `index_configs` | `Dict[str, IndexConfig]` or `Unset` | No | New indexes. |
| `description` | `str` or `Unset` | No | Replacement description. |
| `tags` | `Dict[str, str]` or `Unset` | No | Replacement metadata tags. |
| `snapshot_retention_in_days` | `int` or `Unset` | No | Retention, 1-31 days. |

`IndexConfig` denotes the SDK's `models.IndexConfigsUnion` type.
