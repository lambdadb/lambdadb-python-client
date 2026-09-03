# UpsertDocsRequestBody


## Fields

| Field                          | Type                           | Required                       | Description                    |
| ------------------------------ | ------------------------------ | ------------------------------ | ------------------------------ |
| `docs`                         | List[Dict[str, *Any*]]         | :heavy_check_mark:             | A list of documents to upsert. |
| `branch` | `Optional[str]` | :heavy_minus_sign: | Write target Branch; defaults to `main`. |
