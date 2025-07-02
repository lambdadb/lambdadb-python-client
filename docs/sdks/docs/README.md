# Docs
(*collections.docs*)

## Overview

### Available Operations

* [upsert](#upsert) - Upsert documents into a collection. Note that the maximum supported payload size is 6MB.
* [get_bulk_upsert](#get_bulk_upsert) - Request required info to upload documents.
* [bulk_upsert](#bulk_upsert) - Bulk upsert documents into a collection. Note that the maximum supported object size is 200MB.
* [update_docs](#update_docs) - Update documents in a collection. Note that the maximum supported payload size is 6MB.
* [delete](#delete) - Delete documents by document IDs or query filter from a collection.
* [fetch](#fetch) - Lookup and return documents by document IDs from a collection.

## upsert

Upsert documents into a collection. Note that the maximum supported payload size is 6MB.

### Example Usage

```python
from lambdadb import LambdaDB


with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
) as lambda_db:

    res = lambda_db.collections.docs.upsert(project_name="<value>", collection_name="<value>", docs=[
        {
            "example-doc1": {
                "example-field1": "example-value1",
                "example-field2": [
                    0.1,
                    0.2,
                    0.3,
                ],
            },
        },
        {
            "example-doc2": {
                "example-field1": "example-value2",
                "example-field2": [
                    0.4,
                    0.5,
                    0.6,
                ],
            },
        },
    ])

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `project_name`                                                      | *str*                                                               | :heavy_check_mark:                                                  | Project name.                                                       |
| `collection_name`                                                   | *str*                                                               | :heavy_check_mark:                                                  | Collection name.                                                    |
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
) as lambda_db:

    res = lambda_db.collections.docs.get_bulk_upsert(project_name="<value>", collection_name="<value>")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `project_name`                                                      | *str*                                                               | :heavy_check_mark:                                                  | Project name.                                                       |
| `collection_name`                                                   | *str*                                                               | :heavy_check_mark:                                                  | Collection name.                                                    |
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
) as lambda_db:

    res = lambda_db.collections.docs.bulk_upsert(project_name="<value>", collection_name="<value>", object_key="example-object-key")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `project_name`                                                      | *str*                                                               | :heavy_check_mark:                                                  | Project name.                                                       |
| `collection_name`                                                   | *str*                                                               | :heavy_check_mark:                                                  | Collection name.                                                    |
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

## update_docs

Update documents in a collection. Note that the maximum supported payload size is 6MB.

### Example Usage

```python
from lambdadb import LambdaDB


with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
) as lambda_db:

    res = lambda_db.collections.docs.update_docs(project_name="<value>", collection_name="<value>", docs=[
        {
            "example-doc1": {
                "id": "example-id1",
                "example-field1": "example-value1",
                "example-field2": [
                    0.1,
                    0.2,
                    0.3,
                ],
            },
        },
        {
            "example-doc2": {
                "id": "example-id2",
                "example-field1": "example-value2",
                "example-field2": [
                    0.4,
                    0.5,
                    0.6,
                ],
            },
        },
    ])

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                           | Type                                                                                | Required                                                                            | Description                                                                         |
| ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `project_name`                                                                      | *str*                                                                               | :heavy_check_mark:                                                                  | Project name.                                                                       |
| `collection_name`                                                                   | *str*                                                                               | :heavy_check_mark:                                                                  | Collection name.                                                                    |
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
) as lambda_db:

    res = lambda_db.collections.docs.delete(project_name="<value>", collection_name="<value>", ids=[
        "example-doc-id-1",
        "example-doc-id-2",
    ])

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `project_name`                                                      | *str*                                                               | :heavy_check_mark:                                                  | Project name.                                                       |
| `collection_name`                                                   | *str*                                                               | :heavy_check_mark:                                                  | Collection name.                                                    |
| `ids`                                                               | List[*str*]                                                         | :heavy_minus_sign:                                                  | A list of document IDs.                                             |
| `filter_`                                                           | Dict[str, *Any*]                                                    | :heavy_minus_sign:                                                  | Query filter.                                                       |
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
) as lambda_db:

    res = lambda_db.collections.docs.fetch(project_name="<value>", collection_name="<value>", ids=[
        "example-doc-id-1",
        "example-doc-id-2",
    ], consistent_read=False, include_vectors=False)

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                                                                                                                                                                   | Type                                                                                                                                                                                                                        | Required                                                                                                                                                                                                                    | Description                                                                                                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `project_name`                                                                                                                                                                                                              | *str*                                                                                                                                                                                                                       | :heavy_check_mark:                                                                                                                                                                                                          | Project name.                                                                                                                                                                                                               |
| `collection_name`                                                                                                                                                                                                           | *str*                                                                                                                                                                                                                       | :heavy_check_mark:                                                                                                                                                                                                          | Collection name.                                                                                                                                                                                                            |
| `ids`                                                                                                                                                                                                                       | List[*str*]                                                                                                                                                                                                                 | :heavy_check_mark:                                                                                                                                                                                                          | A list of document IDs to fetch. Note that the maximum number of document IDs is 100.                                                                                                                                       |
| `consistent_read`                                                                                                                                                                                                           | *Optional[bool]*                                                                                                                                                                                                            | :heavy_minus_sign:                                                                                                                                                                                                          | If your application requires a strongly consistent read, set consistentRead to true. Although a strongly consistent read might take more time than an eventually consistent read, it always returns the last updated value. |
| `include_vectors`                                                                                                                                                                                                           | *Optional[bool]*                                                                                                                                                                                                            | :heavy_minus_sign:                                                                                                                                                                                                          | If your application need to include vector values in the response, set includeVectors to true.                                                                                                                              |
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