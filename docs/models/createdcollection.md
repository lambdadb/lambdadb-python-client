# CreatedCollection

Summary returned when a collection is created.

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `collection_name` | `str` | Yes | Collection name. |
| `description` | `str` | Yes | Collection description. |
| `tags` | `Dict[str, str]` | Yes | Collection metadata tags. |
| `default_branch_name` | `Literal["main"]` | Yes | Default Branch. |
| `snapshot_retention_in_days` | `int` | Yes | Snapshot retention, 1-31 days. |
| `created_at` | `int` | Yes | Creation time as Unix epoch milliseconds. |

The `created_at_dt` property returns a timezone-aware UTC `datetime`.
