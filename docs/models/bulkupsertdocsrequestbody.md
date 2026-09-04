# BulkUpsertDocsRequestBody

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `object_key` | `str` | Yes | Object key returned by the upload-info request. |
| `type` | `str` | No | Uploaded content type; defaults to `application/json`. |
| `branch` | `Optional[str]` | No | Write target Branch; defaults to `main`. |
