# CollectionResponse


## Fields

| Field                                                                 | Type                                                                  | Required                                                              | Description                                                           |
| --------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `project_name`                                                        | *str*                                                                 | :heavy_check_mark:                                                    | Project name.                                                         |
| `collection_name`                                                     | *str*                                                                 | :heavy_check_mark:                                                    | Collection name.                                                      |
| `index_configs`                                                       | Dict[str, [models.IndexConfigsUnion](../models/indexconfigsunion.md)] | :heavy_check_mark:                                                    | N/A                                                                   |
| `num_docs`                                                            | *int*                                                                 | :heavy_check_mark:                                                    | Total number of documents.                                            |
| `source_project_name`                                                 | *Optional[str]*                                                       | :heavy_minus_sign:                                                    | Source project name.                                                  |
| `source_collection_name`                                              | *Optional[str]*                                                       | :heavy_minus_sign:                                                    | Source collection name.                                               |
| `source_collection_version_id`                                        | *Optional[str]*                                                       | :heavy_minus_sign:                                                    | Source collection version.                                            |
| `collection_status`                                                   | [models.Status](../models/status.md)                                  | :heavy_check_mark:                                                    | Status                                                                |