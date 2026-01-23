# FetchDocsResponse

Fetched documents.


## Fields

| Field                                                  | Type                                                   | Required                                               | Description                                            |
| ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ |
| `total`                                                | *int*                                                  | :heavy_check_mark:                                     | Total number of documents returned.                    |
| `took`                                                 | *int*                                                  | :heavy_check_mark:                                     | Elapsed time in milliseconds.                          |
| `docs`                                                 | List[[models.FetchDocsDoc](../models/fetchdocsdoc.md)] | :heavy_check_mark:                                     | N/A                                                    |
| `is_docs_inline`                                       | *bool*                                                 | :heavy_check_mark:                                     | Whether the list of documents is included.             |
| `docs_url`                                             | *Optional[str]*                                        | :heavy_minus_sign:                                     | Download URL for the list of documents.                |