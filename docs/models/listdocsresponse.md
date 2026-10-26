# ListDocsResponse

Documents list.


## Fields

| Field                  | Type                   | Required               | Description                                                                 |
| ---------------------- | ---------------------- | ---------------------- | --------------------------------------------------------------------------- |
| `total`                | *int*                  | :heavy_check_mark:     | Number of documents returned in this page.                                   |
| `results`               | List[Dict[str, *Any*]] | :heavy_check_mark:     | List of result items (documents or items with `doc` key).                   |
| `next_page_token`      | *Optional[str]*        | :heavy_minus_sign:     | Opaque position for the next page, not a snapshot pin.                        |
| `is_docs_inline`       | *bool*                 | :heavy_check_mark:     | Whether the API included documents inline.                                  |
| `docs_url`             | *Optional[str]*        | :heavy_minus_sign:     | Presigned download URL for offloaded documents.                              |

**Response access:** Use `response.results` for full result items and
`response.documents` for document bodies only. The latter unwraps dictionary
envelopes containing `doc` and also accepts legacy plain-document results.
It is a convenience property and is not included in serialized responses.
The deprecated property `docs` still returns the same data as `results`.

`coll.docs.list()` and `list_async()` automatically download offloaded results
and preserve `next_page_token`. Low-level methods return the URL without
downloading it. Both response forms expose the same `documents` property.
