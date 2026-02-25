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

### Available Operations

* [list_docs](#list_docs) - List documents in a collection.
* [upsert](#upsert) - Upsert documents into a collection. Note that the maximum supported payload size is 6MB.
* [get_bulk_upsert](#get_bulk_upsert) - Request required info to upload documents.
* [bulk_upsert](#bulk_upsert) - Bulk upsert documents into a collection. Note that the maximum supported object size is 200MB.
* [update](#update) - Update documents in a collection. Note that the maximum supported payload size is 6MB.
* [delete](#delete) - Delete documents by document IDs or query filter from a collection.
* [fetch](#fetch) - Lookup and return documents by document IDs from a collection.

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
| `page_token`                                                        | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | Next page token.                                                    |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.ListDocsResponse](../../models/listdocsresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.BadRequestError       | 400                          | application/json             |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |

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
| `filter_`                                                           | Dict[str, *Any*]                                                    | :heavy_minus_sign:                                                  | Query filter.                                                       |
| `partition_filter`                                                  | [Optional[models.PartitionFilter]](../../models/partitionfilter.md) | :heavy_minus_sign:                                                  | N/A                                                                 |
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
| `ids`                                                                                                                                                                                                                       | List[*str*]                                                                                                                                                                                                                 | :heavy_check_mark:                                                                                                                                                                                                          | A list of document IDs to fetch. Note that the maximum number of document IDs is 100.                                                                                                                                       |
| `consistent_read`                                                                                                                                                                                                           | *Optional[bool]*                                                                                                                                                                                                            | :heavy_minus_sign:                                                                                                                                                                                                          | If your application requires a strongly consistent read, set consistentRead to true. Although a strongly consistent read might take more time than an eventually consistent read, it always returns the last updated value. |
| `include_vectors`                                                                                                                                                                                                           | *Optional[bool]*                                                                                                                                                                                                            | :heavy_minus_sign:                                                                                                                                                                                                          | If your application need to include vector values in the response, set includeVectors to true.                                                                                                                              |
| `fields`                                                                                                                                                                                                                    | [Optional[models.FieldsSelectorUnion]](../../models/fieldsselectorunion.md)                                                                                                                                                 | :heavy_minus_sign:                                                                                                                                                                                                          | An object to specify a list of field names to include and/or exclude in the result.                                                                                                                                         |
| `partition_filter`                                                                                                                                                                                                          | [Optional[models.PartitionFilter]](../../models/partitionfilter.md)                                                                                                                                                         | :heavy_minus_sign:                                                                                                                                                                                                          | N/A                                                                                                                                                                                                                         |
| `retries`                                                                                                                                                                                                                   | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                                                                            | :heavy_minus_sign:                                                                                                                                                                                                          | Configuration to override the default retry behavior of the client.                                                                                                                                                         |

### Response

**[models.FetchDocsResponse](../../models/fetchdocsresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.BadRequestError       | 400                          | application/json             |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |