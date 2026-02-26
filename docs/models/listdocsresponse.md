# ListDocsResponse

Documents list.


## Fields

| Field                  | Type                   | Required               | Description                                                                 |
| ---------------------- | ---------------------- | ---------------------- | --------------------------------------------------------------------------- |
| `total`                | *int*                  | :heavy_check_mark:     | N/A                                                                         |
| `results`               | List[Dict[str, *Any*]] | :heavy_check_mark:     | List of result items (documents or items with `doc` key).                   |
| `next_page_token`      | *Optional[str]*        | :heavy_minus_sign:     | N/A                                                                         |

**Response access:** Use `response.results` for the list of items. The deprecated property `docs` still returns the same data for backward compatibility.