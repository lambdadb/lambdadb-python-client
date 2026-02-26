# FetchDocsResponse

Fetched documents.


## Fields

| Field                                                  | Type                                                   | Required                                               | Description                                                         |
| ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------------------- |
| `total`                                                | *int*                                                  | :heavy_check_mark:                                     | Total number of documents returned.                                 |
| `took`                                                 | *int*                                                  | :heavy_check_mark:                                     | Elapsed time in milliseconds.                                       |
| `results`                                              | List[[models.FetchDocsDoc](../models/fetchdocsdoc.md)] | :heavy_check_mark:                                     | List of result items (each has `.doc`, `.collection`).             |
| `is_docs_inline`                                       | *bool*                                                 | :heavy_check_mark:                                     | Whether the list of documents is included.                          |
| `docs_url`                                             | *Optional[str]*                                        | :heavy_minus_sign:                                     | Download URL for the list of documents.                             |

## Properties

| Property      | Type                   | Description                                                                 |
| ------------- | ---------------------- | --------------------------------------------------------------------------- |
| `documents`   | List[Dict[str, *Any*]] | List of document bodies only (convenience). Use when you don't need .collection. |

**Response access:** Use `response.results` when you need per-item metadata (e.g. `.collection`); use `response.documents` when you only need the document bodies. The deprecated property `docs` still returns the same as `results` for backward compatibility.

**When `is_docs_inline` is false:** The API returns a presigned `docs_url` instead of inline results. When using `coll.docs.fetch()` or `coll.docs.fetch_async()`, the SDK automatically fetches from that URL and populates `results`/`documents`, so you can always use `response.results` and `response.documents` without handling the URL yourself.