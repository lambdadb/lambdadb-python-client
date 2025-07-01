# Collections
(*collections*)

## Overview

### Available Operations

* [list](#list) - List all collections in an existing project.
* [create](#create) - Create a collection.
* [delete](#delete) - Delete an existing collection.
* [get](#get) - Get metadata of an existing collection.
* [update](#update) - Configure a collection.
* [query](#query) - Search a collection with a query and return the most similar documents.

## list

List all collections in an existing project.

### Example Usage

```python
from lambdadb import LambdaDB


with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
) as lambda_db:

    res = lambda_db.collections.list(project_name="<value>")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `project_name`                                                      | *str*                                                               | :heavy_check_mark:                                                  | Project name.                                                       |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.ListCollectionsResponse](../../models/listcollectionsresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |

## create

Create a collection.

### Example Usage

```python
from lambdadb import LambdaDB, models


with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
) as lambda_db:

    res = lambda_db.collections.create(project_name="<value>", collection_name="example-collection-name", index_configs={
        "example-field1": {
            "type": models.TypeText.TEXT,
            "analyzers": [
                models.Analyzer.ENGLISH,
            ],
        },
        "example-field2": {
            "type": models.TypeVector.VECTOR,
            "dimensions": 128,
            "similarity": models.Similarity.COSINE,
        },
    })

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                               | Type                                                                                    | Required                                                                                | Description                                                                             |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `project_name`                                                                          | *str*                                                                                   | :heavy_check_mark:                                                                      | Project name.                                                                           |
| `collection_name`                                                                       | *str*                                                                                   | :heavy_check_mark:                                                                      | Collection name must be unique within a project and the supported maximum length is 52. |
| `index_configs`                                                                         | Dict[str, [models.IndexConfigsUnion](../../models/indexconfigsunion.md)]                | :heavy_minus_sign:                                                                      | N/A                                                                                     |
| `source_project_name`                                                                   | *Optional[str]*                                                                         | :heavy_minus_sign:                                                                      | N/A                                                                                     |
| `source_collection_name`                                                                | *Optional[str]*                                                                         | :heavy_minus_sign:                                                                      | N/A                                                                                     |
| `source_datetime`                                                                       | *Optional[str]*                                                                         | :heavy_minus_sign:                                                                      | N/A                                                                                     |
| `source_project_api_key`                                                                | *Optional[str]*                                                                         | :heavy_minus_sign:                                                                      | N/A                                                                                     |
| `retries`                                                                               | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                        | :heavy_minus_sign:                                                                      | Configuration to override the default retry behavior of the client.                     |

### Response

**[models.CreateCollectionResponse](../../models/createcollectionresponse.md)**

### Errors

| Error Type                        | Status Code                       | Content Type                      |
| --------------------------------- | --------------------------------- | --------------------------------- |
| errors.BadRequestError            | 400                               | application/json                  |
| errors.UnauthenticatedError       | 401                               | application/json                  |
| errors.ResourceAlreadyExistsError | 409                               | application/json                  |
| errors.TooManyRequestsError       | 429                               | application/json                  |
| errors.InternalServerError        | 500                               | application/json                  |
| errors.APIError                   | 4XX, 5XX                          | \*/\*                             |

## delete

Delete an existing collection.

### Example Usage

```python
from lambdadb import LambdaDB


with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
) as lambda_db:

    res = lambda_db.collections.delete(project_name="<value>", collection_name="<value>")

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

**[models.MessageResponse](../../models/messageresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |

## get

Get metadata of an existing collection.

### Example Usage

```python
from lambdadb import LambdaDB


with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
) as lambda_db:

    res = lambda_db.collections.get(project_name="<value>", collection_name="<value>")

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

**[models.GetCollectionResponse](../../models/getcollectionresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |

## update

Configure a collection.

### Example Usage

```python
from lambdadb import LambdaDB, models


with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
) as lambda_db:

    res = lambda_db.collections.update(project_name="<value>", collection_name="<value>", index_configs={
        "example-field1": {
            "type": models.TypeText.TEXT,
            "analyzers": [
                models.Analyzer.ENGLISH,
            ],
        },
        "example-field2": {
            "type": models.TypeVector.VECTOR,
            "dimensions": 128,
            "similarity": models.Similarity.COSINE,
        },
        "example-field3": {
            "type": models.Type.KEYWORD,
        },
    })

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                | Type                                                                     | Required                                                                 | Description                                                              |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| `project_name`                                                           | *str*                                                                    | :heavy_check_mark:                                                       | Project name.                                                            |
| `collection_name`                                                        | *str*                                                                    | :heavy_check_mark:                                                       | Collection name.                                                         |
| `index_configs`                                                          | Dict[str, [models.IndexConfigsUnion](../../models/indexconfigsunion.md)] | :heavy_check_mark:                                                       | N/A                                                                      |
| `retries`                                                                | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)         | :heavy_minus_sign:                                                       | Configuration to override the default retry behavior of the client.      |

### Response

**[models.UpdateCollectionResponse](../../models/updatecollectionresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.BadRequestError       | 400                          | application/json             |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |

## query

Search a collection with a query and return the most similar documents.

### Example Usage

```python
from lambdadb import LambdaDB


with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
) as lambda_db:

    res = lambda_db.collections.query(project_name="<value>", collection_name="<value>", size=2, query={}, consistent_read=False, include_vectors=False)

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                                                                                                                                                                   | Type                                                                                                                                                                                                                        | Required                                                                                                                                                                                                                    | Description                                                                                                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `project_name`                                                                                                                                                                                                              | *str*                                                                                                                                                                                                                       | :heavy_check_mark:                                                                                                                                                                                                          | Project name.                                                                                                                                                                                                               |
| `collection_name`                                                                                                                                                                                                           | *str*                                                                                                                                                                                                                       | :heavy_check_mark:                                                                                                                                                                                                          | Collection name.                                                                                                                                                                                                            |
| `size`                                                                                                                                                                                                                      | *int*                                                                                                                                                                                                                       | :heavy_check_mark:                                                                                                                                                                                                          | Number of documents to return. Note that the maximum number of documents is 100.                                                                                                                                            |
| `query`                                                                                                                                                                                                                     | [Optional[models.Query]](../../models/query.md)                                                                                                                                                                             | :heavy_minus_sign:                                                                                                                                                                                                          | Query object.                                                                                                                                                                                                               |
| `consistent_read`                                                                                                                                                                                                           | *Optional[bool]*                                                                                                                                                                                                            | :heavy_minus_sign:                                                                                                                                                                                                          | If your application requires a strongly consistent read, set consistentRead to true. Although a strongly consistent read might take more time than an eventually consistent read, it always returns the last updated value. |
| `include_vectors`                                                                                                                                                                                                           | *Optional[bool]*                                                                                                                                                                                                            | :heavy_minus_sign:                                                                                                                                                                                                          | If your application need to include vector values in the response, set includeVectors to true.                                                                                                                              |
| `sort`                                                                                                                                                                                                                      | List[[models.Sort](../../models/sort.md)]                                                                                                                                                                                   | :heavy_minus_sign:                                                                                                                                                                                                          | List of field name, sort direction pairs.                                                                                                                                                                                   |
| `fields`                                                                                                                                                                                                                    | List[*str*]                                                                                                                                                                                                                 | :heavy_minus_sign:                                                                                                                                                                                                          | List of field name to include in results                                                                                                                                                                                    |
| `retries`                                                                                                                                                                                                                   | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                                                                            | :heavy_minus_sign:                                                                                                                                                                                                          | Configuration to override the default retry behavior of the client.                                                                                                                                                         |

### Response

**[models.QueryCollectionResponse](../../models/querycollectionresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.BadRequestError       | 400                          | application/json             |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |