# CreateCollectionRequest

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `collection_name` | `str` | Yes | Collection name, 3-52 supported characters. |
| `index_configs` | `Dict[str, models.IndexConfigsUnion]` | Yes | Collection index configuration. |
| `description` | `Optional[str]` | No | Collection description, up to 255 characters. |
| `tags` | `Optional[Dict[str, str]]` | No | Up to five metadata tags. |
| `partition_config` | `Optional[models.PartitionConfig]` | No | Partition configuration. |
| `snapshot_retention_in_days` | `Optional[int]` | No | Snapshot retention, 1-31 days; API default is 30. |

The `0.8.2` cross-collection source fields were removed. Collection-scoped
Branches and Tags are not a direct replacement for copying from another
collection; see [CHANGELOG](../../CHANGELOG.md#migration-guidance).
