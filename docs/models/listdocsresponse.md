# ListDocsResponse

Documents list.


## Fields

| Field                  | Type                   | Required               | Description            |
| ---------------------- | ---------------------- | ---------------------- | ---------------------- |
| `total`                | *int*                  | :heavy_check_mark:     | N/A                    |
| `docs`                 | List[Dict[str, *Any*]] | :heavy_check_mark:     | A list of documents.   |
| `next_page_token`      | *Optional[str]*        | :heavy_minus_sign:     | N/A                    |