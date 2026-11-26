# Collections.Docs

## Overview

Use the collection-scoped API with `base_url` and `project_name`:

```python
from lambdadb import LambdaDB

with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    coll = client.collection("my_collection")
    coll.docs.list()           # list documents
    coll.docs.fetch(ids=[...]) # fetch by IDs
    coll.docs.upsert(docs=[...])
    coll.query(query={...})    # search (collection-level)
```

**Response access:** For list, query, and fetch responses use `response.results` for the full result items (with score/metadata when applicable); use `response.documents` for document bodies only. When the API returns `is_docs_inline: false` with a presigned `docs_url`, the SDK automatically fetches from that URL so `results`/`documents` are always populated. See [ListDocsResponse](../../models/listdocsresponse.md), [QueryCollectionResponse](../../models/querycollectionresponse.md), [FetchDocsResponse](../../models/fetchdocsresponse.md).

**Advanced options:** All operations accept optional `options=RequestOptions(retries=..., server_url=..., timeout_ms=..., http_headers=...)` for per-call overrides. Import with `from lambdadb import RequestOptions`. See [README](../../../README.md) for more.

### Available Operations

* [list_docs](#list_docs) - List documents in a collection.
* [list_pages](#list_pages) - Iterate pages of up to `size` documents each (handles API payload limits).
* [iter_all](#iter_all) - Iterate over all documents in the collection (handles pagination).
* [upsert](#upsert) - Upsert documents into a collection. Note that the maximum supported payload size is 6MB.
* [get_bulk_upsert](#get_bulk_upsert) - Request required info to upload documents.
* [bulk_upsert](#bulk_upsert) - Bulk upsert documents into a collection. Note that the maximum supported object size is 200MB.
* [bulk_upsert_docs](#bulk_upsert_docs) - One-step bulk upsert: pass a list of documents; the SDK gets the presigned URL, uploads to S3, and triggers bulk_upsert.
* [update](#update) - Update documents in a collection. Note that the maximum supported payload size is 6MB.
* [delete](#delete) - Delete documents by document IDs or query filter from a collection.
* [fetch](#fetch) - Lookup and return documents by document IDs from a collection.

## Data Versioning arguments

- Pass `ref=Ref.branch(name)`, `Ref.tag(name)`, or `Ref.alias(name)` to List,
  Fetch, and Query reads. `list_pages`, `iter_all`, and their async variants
  preserve the ref on every page. List, Fetch, and Query accept
  `consistent_read=True` on a Branch or an Alias that targets a Branch.
- Pass `branch="name"` to Upsert, Update, Delete, Bulk Upsert, and the one-step
  bulk helper. Writes do not accept Tag or Alias refs.
- `bulk_upsert_docs(..., transfer_client=...)` can use a client separate from
  the LambdaDB API client and forwards the signed upload headers returned by
  `get_bulk_upsert`.

See the complete [Data Versioning guide](../versioning/README.md).

## list_docs

List documents in a collection.

### Example Usage

```python
from lambdadb import LambdaDB

with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    coll = client.collection("my_collection")
    res = coll.docs.list()
    print(res)
```

When using the recommended API (`coll.docs.list()`), the collection is already bound; only the parameters below apply (e.g. `collection_name` is not used).

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `collection_name`                                                   | *str*                                                               | :heavy_check_mark:                                                  | Collection name (legacy API only; not used with `coll.docs.list()`). |
| `size`                                                              | *Optional[int]*                                                     | :heavy_minus_sign:                                                  | Max number of documents to return at once.                          |
| `page_token` | *Optional[str]* | :heavy_minus_sign: | Opaque position from `next_page_token`, not a Snapshot pin. Repeat the other arguments, including `size`; a changed request condition raises `BadRequestError`. |
| `sort` | *Optional[List[Dict[str, str]]]* | :heavy_minus_sign: | 1-4 objects such as `{"category": "asc"}` on keyword, long, double, or datetime fields (`"asc"` or `"desc"`). Default order is ascending document ID, which also breaks ties. Uses the extended list endpoint. |
| `consistent_read` | *Optional[bool]* | :heavy_minus_sign: | Include pending ordinary writes of a Branch or an Alias that targets a Branch (default `False`, not sent unless true). A Tag ref raises `ValueError`. Uses the extended list endpoint. |
| `options`                                                           | [Optional[RequestOptions]](../../../README.md)                       | :heavy_minus_sign:                                                  | Advanced options (retries, server_url, timeout_ms, http_headers).   |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.ListDocsResponse](../../models/listdocsresponse.md)** — Use `response.results` for the list of items (deprecated: `response.docs`).

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.BadRequestError       | 400                          | application/json             |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |

## list_pages

Iterate pages of up to `size` documents each. Every request repeats the same arguments and asks for `min(size, 1000)` documents, because a page token is bound to the request conditions, including the size; the SDK regroups responses into logical pages. The default page size remains 100. The API may return fewer documents per request due to payload limits. `list_pages` accepts the same `filter_`, `partition_filter`, `fields`, `include_vectors`, `sort`, `consistent_read`, and `ref` arguments as `list`.

### Example Usage

```python
from lambdadb import LambdaDB

with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    coll = client.collection("my_collection")
    for page in coll.docs.list_pages(size=10):
        # page is a list of up to 10 documents
        for doc in page:
            print(doc)
```

### Parameters

| Parameter   | Type                                    | Required   | Description                                              |
| ----------- | --------------------------------------- | ---------- | -------------------------------------------------------- |
| `size`      | *int*                                   | :heavy_minus_sign: | Max documents per page (default 100).                    |
| `options`   | [Optional[RequestOptions]](../../../README.md)                   | :heavy_minus_sign: | Advanced options (retries, server_url, timeout_ms, http_headers). |

## iter_all

Iterate over all documents in the collection. Handles pagination internally.

### Example Usage

```python
from lambdadb import LambdaDB

with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    coll = client.collection("my_collection")
    for doc in coll.docs.iter_all(page_size=100):
        print(doc)
```

### Parameters

| Parameter    | Type                                    | Required   | Description                                              |
| ------------ | --------------------------------------- | ---------- | -------------------------------------------------------- |
| `page_size`  | *int*                                   | :heavy_minus_sign: | Documents per internal page (default 100).               |
| `options`    | [Optional[RequestOptions]](../../../README.md#advanced-options) | :heavy_minus_sign: | Advanced options.                                       |

## upsert

Upsert documents into a collection. Note that the maximum supported payload size is 6MB.

### Example Usage

```python
from lambdadb import LambdaDB

with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    coll = client.collection("my_collection")
    res = coll.docs.upsert(docs=[
        {"example-field1": "example-value1", "example-field2": [0.1, 0.2, 0.3]},
        {"example-field1": "example-value2", "example-field2": [0.4, 0.5, 0.6]},
    ])
    print(res)
```

When using the recommended API (`coll.docs.upsert()`), the collection is already bound; only the parameters below apply (e.g. `collection_name` is not used).

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `collection_name`                                                   | *str*                                                               | :heavy_check_mark:                                                  | Collection name (legacy API only; not used with `coll.docs.upsert()`). |
| `docs`                                                              | List[Dict[str, *Any*]]                                              | :heavy_check_mark:                                                  | A list of documents to upsert.                                      |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.MessageResponse](../../models/messageresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.BadRequestError       | 400                          | application/json             |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |

## get_bulk_upsert

Request required info to upload documents.

### Example Usage

```python
from lambdadb import LambdaDB

with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    coll = client.collection("my_collection")
    res = coll.docs.get_bulk_upsert()
    print(res)
```

When using the recommended API (`coll.docs.get_bulk_upsert()`), the collection is already bound; only the parameters below apply (e.g. `collection_name` is not used).

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `collection_name`                                                   | *str*                                                               | :heavy_check_mark:                                                  | Collection name (legacy API only; not used with `coll.docs.get_bulk_upsert()`). |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.GetBulkUpsertDocsResponse](../../models/getbulkupsertdocsresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |

## bulk_upsert

Bulk upsert documents into a collection. Note that the maximum supported object size is 200MB.

### Example Usage

```python
from lambdadb import LambdaDB

with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    coll = client.collection("my_collection")
    res = coll.docs.bulk_upsert(object_key="example-object-key")
    print(res)
```

When using the recommended API (`coll.docs.bulk_upsert()`), the collection is already bound; only the parameters below apply (e.g. `collection_name` is not used).

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `collection_name`                                                   | *str*                                                               | :heavy_check_mark:                                                  | Collection name (legacy API only; not used with `coll.docs.bulk_upsert()`). |
| `object_key`                                                        | *str*                                                               | :heavy_check_mark:                                                  | Object key uploaded based on bulk upsert info.                      |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.MessageResponse](../../models/messageresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.BadRequestError       | 400                          | application/json             |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |

## bulk_upsert_docs

One-step bulk upsert: pass a list of documents; the SDK obtains a presigned URL, uploads the JSON payload to S3, then calls bulk_upsert. Use this instead of manually calling get_bulk_upsert, uploading to S3, and bulk_upsert. Maximum payload size 200MB.

### Example Usage

```python
from lambdadb import LambdaDB

with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    coll = client.collection("my_collection")
    docs = [{"id": "1", "text": "one"}, {"id": "2", "text": "two"}]
    res = coll.docs.bulk_upsert_docs(docs=docs)
    print(res)
```

### Parameters

| Parameter   | Type                                                                 | Required   | Description                                                         |
| ----------- | -------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------- |
| `docs`      | List[Dict[str, *Any*]]                                                | :heavy_check_mark: | List of documents to bulk upsert.                                   |
| `options`   | [Optional[RequestOptions]](../../../README.md)                        | :heavy_minus_sign: | Advanced options (retries, server_url, timeout_ms, http_headers).   |
| `retries`   | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign: | Override retry behavior.                                            |

### Response

**[models.MessageResponse](../../models/messageresponse.md)**

### Errors

Raises `ValueError` if the serialized payload exceeds the size limit. Raises `RuntimeError` if the S3 upload fails. Other errors are the same as [get_bulk_upsert](#get_bulk_upsert) and [bulk_upsert](#bulk_upsert).

## update

Update documents in a collection. Note that the maximum supported payload size is 6MB.

### Example Usage

```python
from lambdadb import LambdaDB

with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    coll = client.collection("my_collection")
    res = coll.docs.update(docs=[
        {"id": "example-id1", "example-field1": "example-value1", "example-field2": [0.1, 0.2, 0.3]},
        {"id": "example-id2", "example-field1": "example-value2", "example-field2": [0.4, 0.5, 0.6]},
    ])
    print(res)
```

When using the recommended API (`coll.docs.update()`), the collection is already bound; only the parameters below apply (e.g. `collection_name` is not used).

### Parameters

| Parameter                                                                           | Type                                                                                | Required                                                                            | Description                                                                         |
| ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `collection_name`                                                                   | *str*                                                                               | :heavy_check_mark:                                                                  | Collection name (legacy API only; not used with `coll.docs.update()`).              |
| `docs`                                                                              | List[Dict[str, *Any*]]                                                              | :heavy_check_mark:                                                                  | A list of documents to update. Each document must contain 'id' field to be updated. |
| `retries`                                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                    | :heavy_minus_sign:                                                                  | Configuration to override the default retry behavior of the client.                 |

### Response

**[models.MessageResponse](../../models/messageresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.BadRequestError       | 400                          | application/json             |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |

## delete

Delete documents by document IDs or query filter from a collection.

### Example Usage

```python
from lambdadb import LambdaDB

with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    coll = client.collection("my_collection")
    res = coll.docs.delete(ids=["example-doc-id-1", "example-doc-id-2"])
    print(res)
```

When using the recommended API (`coll.docs.delete()`), the collection is already bound; only the parameters below apply (e.g. `collection_name` is not used).

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `collection_name`                                                   | *str*                                                               | :heavy_check_mark:                                                  | Collection name (legacy API only; not used with `coll.docs.delete()`). |
| `ids`                                                               | List[*str*]                                                         | :heavy_minus_sign:                                                  | A list of document IDs.                                             |
| `query_filter`                                                      | Dict[str, *Any*]                                                    | :heavy_minus_sign:                                                  | Query filter (preferred over `filter_`).                             |
| `filter_`                                                           | Dict[str, *Any*]                                                    | :heavy_minus_sign:                                                  | Query filter (legacy; prefer `query_filter`).                       |
| `partition_filter`                                                  | [Optional[models.PartitionFilter]](../../models/partitionfilter.md) | :heavy_minus_sign:                                                  | N/A                                                                 |
| `options`                                                           | [Optional[RequestOptions]](../../../README.md)                       | :heavy_minus_sign:                                                  | Advanced options (retries, server_url, timeout_ms, http_headers).   |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.MessageResponse](../../models/messageresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.BadRequestError       | 400                          | application/json             |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |

## fetch

Lookup and return documents by document IDs from a collection.

### Example Usage

```python
from lambdadb import LambdaDB

with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    coll = client.collection("my_collection")
    res = coll.docs.fetch(ids=["example-doc-id-1", "example-doc-id-2"])
    print(res)
```

When using the recommended API (`coll.docs.fetch()`), the collection is already bound; only the parameters below apply (e.g. `collection_name` is not used).

### Parameters

| Parameter                                                                                                                                                                                                                   | Type                                                                                                                                                                                                                        | Required                                                                                                                                                                                                                    | Description                                                                                                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `collection_name`                                                                                                                                                                                                           | *str*                                                                                                                                                                                                                       | :heavy_check_mark:                                                                                                                                                                                                          | Collection name (legacy API only; not used with `coll.docs.fetch()`).                                                                                                                                                       |
| `ids`                                                                                                                                                                                                                       | List[*str*]                                                                                                                                                                                                                 | :heavy_check_mark:                                                                                                                                                                                                          | A list of 1-1000 nonblank document IDs; response byte limits also apply.                                                                                                                                       |
| `consistent_read` | *Optional[bool]* | :heavy_minus_sign: | Overlay eligible inherited and own pending writes on the selected Branch's committed snapshot; ordinary Branch reads use only the snapshot. Allowed on a directly selected Branch or an Alias that currently targets a Branch; the server resolves the Alias. Tag refs and an Alias that targets a Tag already include their fixed inherited writes but reject true with 400; pending bulk imports are excluded until a background build materializes them, and a large pending payload can return 429. |
| `include_vectors`                                                                                                                                                                                                           | *Optional[bool]*                                                                                                                                                                                                            | :heavy_minus_sign:                                                                                                                                                                                                          | If your application need to include vector values in the response, set includeVectors to true.                                                                                                                              |
| `fields`                                                                                                                                                                                                                    | [Optional[models.FieldsSelectorUnion]](../../models/fieldsselectorunion.md)                                                                                                                                                 | :heavy_minus_sign:                                                                                                                                                                                                          | An object to specify a list of field names to include and/or exclude in the result.                                                                                                                                         |
| `partition_filter`                                                                                                                                                                                                          | [Optional[models.PartitionFilter]](../../models/partitionfilter.md)                                                                                                                                                         | :heavy_minus_sign:                                                                                                                                                                                                          | N/A                                                                                                                                                                                                                         |
| `retries`                                                                                                                                                                                                                   | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                                                                            | :heavy_minus_sign:                                                                                                                                                                                                          | Configuration to override the default retry behavior of the client.                                                                                                                                                         |

### Response

**[models.FetchDocsResponse](../../models/fetchdocsresponse.md)** — Use `response.results` for full items (with `.collection`); use `response.documents` for document bodies only. When `is_docs_inline` is false, the SDK auto-fetches from `docs_url` so results are always populated.

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.BadRequestError       | 400                          | application/json             |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |
