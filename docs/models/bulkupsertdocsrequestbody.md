# BulkUpsertDocsRequestBody

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `object_key` | `str` | Yes | Object key returned by the upload-info request. |
| `type` | `str` | No | Optional completion field. The SDK defaults it to `application/json`; the server validates the uploaded object's `Content-Type`. |
| `branch` | `Optional[str]` | No | Write target Branch; defaults to `main`. |
