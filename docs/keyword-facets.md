# Keyword facets

The `0.10.0rc1` candidate supports the keyword facet contract in:

- `lambdadb/lambdadb` commit `8da50bcd0b5a3c781ffccd7f01fb07ed0510dd30`,
  `api/src/main/java/ai/lambdadb/dto/QueryRequest.java`,
  `api/src/main/java/ai/lambdadb/model/query/FacetRequest.java`, and
  `api/src/main/java/ai/lambdadb/model/query/FacetResult.java`.
- `lambdadb/docs` commit `899092420ff801cfcb3b693b1ba273be7ac1f1ef`,
  `reference/api/openapi.json` and `guides/search/facets.mdx`.

These source commits do not establish deployment or package publication. Use a
server build containing the feature and rebuild existing data into a new collection.
Old keyword indexes and old Tags are unsupported; partial updates or segment merging
do not migrate their format. Candidate preparation does not establish package publication.

## Semantics

Request up to five keyword fields by name, including dotted paths. A field's `size`
is 1–100 (default 10). `size: 0` at the query level requires at least one facet and
returns counts without documents. Omit `query` to match all documents.

Counts include all documents matching the query and partition filter within the
selected ref, independent of the returned document count. Each distinct indexed
array value contributes once per document. Missing or unindexed values produce no
bucket. Results are ordered by count descending, then Unicode code point order.
`total` still counts returned documents. Facets remain available after `docsUrl`
document downloads. Without a facet request, existing responses may omit facets.

Use queryString, bool combinations of supported queries, or no query. Vector,
sparse-vector, hybrid, numeric/date range facets, and excluding a facet's own filter
are outside this contract. Existing ref and consistentRead constraints still apply.
At more than 10,000 distinct (field, value) buckets or 262,144 UTF-8 bytes of distinct
values across fields, the server returns HTTP 400 instead of partial counts.

Keyword array sorting uses the smallest indexed value ascending and largest
descending. Missing values sort last ascending and first descending.

## Example

```python
from lambdadb import LambdaDB

with LambdaDB(base_url="YOUR_BASE_URL", project_name="YOUR_PROJECT_NAME",
              project_api_key="YOUR_API_KEY") as client:
    result = client.collection("items").query(size=0, facets={"tags": {"size": 5}})
    for bucket in result.facets["tags"].buckets:
        print(bucket.value, bucket.count)
```

`query_async` supports the same arguments. `FacetRequest`, `FacetBucket`, and
`FacetResult`, plus their TypedDict counterparts, are exported from `lambdadb.models`.

## Implementation review and validation

- [Request/response models](../src/lambdadb/models/querycollectionop.py) and
  [facet models](../src/lambdadb/models/facets.py).
- [Collection methods and hydration](../src/lambdadb/collection.py),
  [low-level methods](../src/lambdadb/collections.py), and [wire tests](../tests/test_facets.py).
- At implementation time, the non-integration suite had 210 passing tests;
  focused sync/async facet tests also passed after
  the typed request conversion was added. mypy passed; pylint scored 10.00/10.
- The implementation PR did not perform a live API call or package publication.
  Subsequent [score-contract validation in PR #44](https://github.com/lambdadb/lambdadb-python-client/pull/44)
  passed all 30 valid dev API cases after the server score fix on 2026-09-29.
  This does not establish production deployment or package publication.
