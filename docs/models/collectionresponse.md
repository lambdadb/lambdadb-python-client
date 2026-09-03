# CollectionResponse

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `project_name` | `str` | Yes | Project name. |
| `collection_name` | `str` | Yes | Collection name. |
| `index_configs` | `Dict[str, models.IndexConfigsUnion]` | Yes | Index configuration. |
| `description` | `str` | Yes | Collection description. |
| `tags` | `Dict[str, str]` | Yes | Collection metadata tags. |
| `partition_config` | `Optional[models.PartitionConfig]` | No | Partition configuration. |
| `num_partitions` | `int` | Yes | Number of partitions. |
| `num_docs` | `int` | Yes | Number of documents. |
| `default_branch_name` | `str` | Yes | Default Branch; currently `main`. |
| `snapshot_retention_in_days` | `int` | Yes | Snapshot retention, 1-31 days. |
| `created_at` | `int` | Yes | Creation time as Unix epoch milliseconds. |
| `updated_at` | `int` | Yes | Last update time as Unix epoch milliseconds. |
| `data_updated_at` | `Optional[int]` | No | Data update time as Unix epoch milliseconds. |

The `created_at_dt`, `updated_at_dt`, and `data_updated_at_dt` properties return
timezone-aware UTC `datetime` values. `data_updated_at_dt` is `None` when the
wire field is absent.
