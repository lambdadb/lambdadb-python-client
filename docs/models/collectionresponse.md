# CollectionResponse


## Fields

| Field                                                                 | Type                                                                  | Required                                                              | Description                                                           |
| --------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `project_name`                                                        | *str*                                                                 | :heavy_check_mark:                                                    | Project name.                                                         |
| `collection_name`                                                     | *str*                                                                 | :heavy_check_mark:                                                    | Collection name.                                                      |
| `index_configs`                                                       | Dict[str, [models.IndexConfigsUnion](../models/indexconfigsunion.md)] | :heavy_check_mark:                                                    | N/A                                                                   |
| `partition_config`                                                    | [Optional[models.PartitionConfig]](../models/partitionconfig.md)      | :heavy_minus_sign:                                                    | N/A                                                                   |
| `num_partitions`                                                      | *int*                                                                 | :heavy_check_mark:                                                    | Total number of partitions including the default partition.           |
| `num_docs`                                                            | *int*                                                                 | :heavy_check_mark:                                                    | Total number of documents.                                            |
| `source_project_name`                                                 | *Optional[str]*                                                       | :heavy_minus_sign:                                                    | Source project name.                                                  |
| `source_collection_name`                                              | *Optional[str]*                                                       | :heavy_minus_sign:                                                    | Source collection name.                                               |
| `source_collection_version_id`                                        | *Optional[str]*                                                       | :heavy_minus_sign:                                                    | Source collection version.                                            |
| `collection_status`                                                   | [models.Status](../models/status.md)                                  | :heavy_check_mark:                                                    | Status                                                                |
| `created_at`                                                         | *int*                                                                 | :heavy_check_mark:                                                    | Creation time (Unix epoch seconds).                                   |
| `updated_at`                                                         | *int*                                                                 | :heavy_check_mark:                                                    | Last update time (Unix epoch seconds).                                |
| `data_updated_at`                                                    | *int*                                                                 | :heavy_check_mark:                                                    | Data last update time (Unix epoch seconds).                           |

## Properties (datetime helpers)

| Property            | Type       | Description                                              |
| ------------------- | ---------- | -------------------------------------------------------- |
| `created_at_dt`     | *datetime* | Creation time as timezone-aware UTC `datetime`.          |
| `updated_at_dt`     | *datetime* | Last update time as timezone-aware UTC `datetime`.       |
| `data_updated_at_dt`| *datetime* | Data last update time as timezone-aware UTC `datetime`. |