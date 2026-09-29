# FacetBucket

One distinct keyword value and its matching document count.

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `value` | *str* | :heavy_check_mark: | Indexed keyword value. |
| `count` | *int* | :heavy_check_mark: | Number of matching documents containing this value. Each distinct indexed array value contributes once per document. |

See [FacetResult](facetresult.md) and [keyword facets](../keyword-facets.md).
