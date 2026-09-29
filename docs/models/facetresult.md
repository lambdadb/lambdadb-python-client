# FacetResult

Facet counts for one keyword field in `QueryCollectionResponse.facets`.

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `buckets` | List[[models.FacetBucket](facetbucket.md)] | :heavy_check_mark: | Buckets ordered by count descending, then Unicode code point order for equal counts. |

Counts include all documents matching the query and partition filter within the
selected ref, independently of the number of returned documents. Missing or
unindexed field values produce no bucket. `QueryCollectionResponse.total` remains
the number of returned documents, not the sum of bucket counts.

See [QueryCollectionResponse](querycollectionresponse.md) and
[keyword facets](../keyword-facets.md).
