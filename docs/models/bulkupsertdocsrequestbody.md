# BulkUpsertDocsRequestBody

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `object_key` | `str` | Yes | Object key returned by the upload-info request. |
| `type` | `str` | No | Uploaded content type. The SDK defaults it to `application/json` and sends it explicitly on completion. |
| `branch` | `Optional[str]` | No | Write target Branch; defaults to `main`. |
