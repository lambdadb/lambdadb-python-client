# CollectionResponse

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `project_name` | `str` | Yes | Project name. |
| `collection_name` | `str` | Yes | Collection name. |
| `index_configs` | `Dict[str, IndexConfigsUnion]` | Yes | Nonempty field configuration map. |
| `description` | `str` | Yes | Collection description. |
| `tags` | `Dict[str, str]` | Yes | Collection metadata tags. |
| `partition_config` | `Optional[PartitionConfig]` | No | Partitions. |
| `num_partitions` | `int` | Yes | Number of partitions. |
| `num_docs` | `int` | Yes | Document count in the default main Branch's committed head. |
| `default_branch_name` | `Literal["main"]` | Yes | Default Branch. |
| `snapshot_retention_in_days` | `int` | Yes | Snapshot retention, 1-31 days. |
| `created_at` | `int` | Yes | Creation time as Unix epoch milliseconds. |
| `updated_at` | `int` | Yes | Last update time as Unix epoch milliseconds. |
| `data_updated_at` | `Optional[int]` | No | Last data mutation in the default main Branch's committed head, as epoch ms; absent before a committed head exists. |

The `created_at_dt`, `updated_at_dt`, and `data_updated_at_dt` properties return
timezone-aware UTC `datetime` values. `data_updated_at_dt` is `None` when the
wire field is absent.
