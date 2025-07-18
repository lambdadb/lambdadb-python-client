# GetBulkUpsertDocsResponse

Required info to upload documents.


## Fields

| Field                                                                        | Type                                                                         | Required                                                                     | Description                                                                  |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `url`                                                                        | *str*                                                                        | :heavy_check_mark:                                                           | Presigned URL.                                                               |
| `type`                                                                       | [Optional[models.GetBulkUpsertDocsType]](../models/getbulkupsertdocstype.md) | :heavy_minus_sign:                                                           | Content type that must be specified when uploading documents.                |
| `http_method`                                                                | [Optional[models.HTTPMethod]](../models/httpmethod.md)                       | :heavy_minus_sign:                                                           | HTTP method that must be specified when uploading documents.                 |
| `object_key`                                                                 | *str*                                                                        | :heavy_check_mark:                                                           | Object key that must be specified when uploading documents.                  |
| `size_limit_bytes`                                                           | *Optional[int]*                                                              | :heavy_minus_sign:                                                           | Object size limit in bytes.                                                  |