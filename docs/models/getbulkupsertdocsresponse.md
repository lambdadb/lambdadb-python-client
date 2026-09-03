# GetBulkUpsertDocsResponse

Required information for a signed bulk upload.

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `url` | `str` | Yes | Presigned upload URL. |
| `type` | `models.GetBulkUpsertDocsType` | Yes | Required upload content type. |
| `http_method` | `models.HTTPMethod` | Yes | Required upload HTTP method. |
| `object_key` | `str` | Yes | Object key supplied to bulk completion. |
| `size_limit_bytes` | `int` | Yes | Maximum upload size. |
| `headers` | `Dict[str, str]` | Yes | Signed headers to forward unchanged. |
