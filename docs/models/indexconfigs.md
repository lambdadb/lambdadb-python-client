# IndexConfigs

Types that do not need additional parameters.


## Fields

| Field                            | Type                             | Required                         | Description                      |
| -------------------------------- | -------------------------------- | -------------------------------- | -------------------------------- |
| `type`                           | [models.Type](../models/type.md) | :heavy_check_mark:               | N/A                              |
| `description`                    | *Optional[str]*                  | :heavy_minus_sign:               | Optional free-form explanation of what the field holds, up to 255 characters. Returned in collection reads only when set and never affects indexing. On update, omitting it or `None` keeps the stored description, `""` clears it, and any other value replaces it without reindexing. Not accepted on the server-managed `id` field. |