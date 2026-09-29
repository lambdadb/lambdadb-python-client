# FacetRequest

Options for one keyword field in `QueryCollectionRequestBody.facets`.

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `size` | *Optional[int]* | :heavy_minus_sign: | Maximum number of buckets to return, from 1 to 100. Omit it to use the server default of 10. |

The SDK omits an unset size instead of injecting the server default. Query-level
`size=0` controls returned documents; it does not permit `FacetRequest.size=0`.

See [QueryCollectionRequestBody](querycollectionrequestbody.md) and
[keyword facets](../keyword-facets.md).
