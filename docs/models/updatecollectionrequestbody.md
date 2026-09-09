# UpdateCollectionRequestBody

Provide at least one non-null field. Omitted fields and `None` are unchanged;
`tags={}` clears all metadata tags and `description=""` clears the description.

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `index_configs` | `Dict[str, IndexConfig]`, `None`, or `Unset` | No | Nonempty complete schema; preserve all existing field definitions. |
| `description` | `str`, `None`, or `Unset` | No | Replacement description; empty clears it. |
| `tags` | `Dict[str, str]`, `None`, or `Unset` | No | Replaces the whole metadata map; `{}` clears it. |
| `snapshot_retention_in_days` | `int`, `None`, or `Unset` | No | Retention, 1-31 days. |

`IndexConfig` denotes the SDK's `models.IndexConfigsUnion` type.
