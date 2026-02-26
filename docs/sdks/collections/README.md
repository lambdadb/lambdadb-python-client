# Collections

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
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    res = client.collections.list()
    print(res)
```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
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
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    res = client.collections.create(
        collection_name="example-collection-name",
        index_configs={
            "example-field1": {"type": models.TypeText.TEXT, "analyzers": [models.Analyzer.ENGLISH]},
            "example-field2": {"type": models.TypeVector.VECTOR, "dimensions": 128, "similarity": models.Similarity.COSINE},
        },
    )
    print(res)
```

### Parameters

| Parameter                                                                               | Type                                                                                    | Required                                                                                | Description                                                                             |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `collection_name`                                                                       | *str*                                                                                   | :heavy_check_mark:                                                                      | Collection name must be unique within a project and the supported maximum length is 52. |
| `index_configs`                                                                         | Dict[str, [models.IndexConfigsUnion](../../models/indexconfigsunion.md)]                | :heavy_minus_sign:                                                                      | N/A                                                                                     |
| `partition_config`                                                                      | [Optional[models.PartitionConfig]](../../models/partitionconfig.md)                     | :heavy_minus_sign:                                                                      | N/A                                                                                     |
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
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    res = client.collections.delete(collection_name="my_collection")
    print(res)
```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
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
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    res = client.collections.get(collection_name="my_collection")
    print(res)
```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
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
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    res = client.collections.update(
        collection_name="my_collection",
        index_configs={
            "example-field1": {"type": models.TypeText.TEXT, "analyzers": [models.Analyzer.ENGLISH]},
            "example-field2": {"type": models.TypeVector.VECTOR, "dimensions": 128, "similarity": models.Similarity.COSINE},
            "example-field3": {"type": models.Type.KEYWORD},
        },
    )
    print(res)
```

### Parameters

| Parameter                                                                | Type                                                                     | Required                                                                 | Description                                                              |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
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
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    coll = client.collection("my_collection")
    res = coll.query(query={"queryString": {"query": "example-field1:example-value"}}, size=2)
    print(res)
```

### Parameters

| Parameter                                                                                                                                                                                                                   | Type                                                                                                                                                                                                                        | Required                                                                                                                                                                                                                    | Description                                                                                                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `collection_name`                                                                                                                                                                                                           | *str*                                                                                                                                                                                                                       | :heavy_check_mark:                                                                                                                                                                                                          | Collection name.                                                                                                                                                                                                            |
| `query`                                                                                                                                                                                                                     | Dict[str, *Any*]                                                                                                                                                                                                            | :heavy_check_mark:                                                                                                                                                                                                          | Query object.                                                                                                                                                                                                               |
| `size`                                                                                                                                                                                                                      | *Optional[int]*                                                                                                                                                                                                             | :heavy_minus_sign:                                                                                                                                                                                                          | Number of documents to return. Note that the maximum number of documents is 100.                                                                                                                                            |
| `consistent_read`                                                                                                                                                                                                           | *Optional[bool]*                                                                                                                                                                                                            | :heavy_minus_sign:                                                                                                                                                                                                          | If your application requires a strongly consistent read, set consistentRead to true. Although a strongly consistent read might take more time than an eventually consistent read, it always returns the last updated value. |
| `include_vectors`                                                                                                                                                                                                           | *Optional[bool]*                                                                                                                                                                                                            | :heavy_minus_sign:                                                                                                                                                                                                          | If your application need to include vector values in the response, set includeVectors to true.                                                                                                                              |
| `sort`                                                                                                                                                                                                                      | List[Dict[str, *Any*]]                                                                                                                                                                                                      | :heavy_minus_sign:                                                                                                                                                                                                          | List of field name, sort direction pairs.                                                                                                                                                                                   |
| `fields`                                                                                                                                                                                                                    | [Optional[models.FieldsSelectorUnion]](../../models/fieldsselectorunion.md)                                                                                                                                                 | :heavy_minus_sign:                                                                                                                                                                                                          | An object to specify a list of field names to include and/or exclude in the result.                                                                                                                                         |
| `partition_filter`                                                                                                                                                                                                          | [Optional[models.PartitionFilter]](../../models/partitionfilter.md)                                                                                                                                                         | :heavy_minus_sign:                                                                                                                                                                                                          | N/A                                                                                                                                                                                                                         |
| `retries`                                                                                                                                                                                                                   | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                                                                            | :heavy_minus_sign:                                                                                                                                                                                                          | Configuration to override the default retry behavior of the client.                                                                                                                                                         |

### Response

**[models.QueryCollectionResponse](../../models/querycollectionresponse.md)** — Use `res.results` for full result items (with `.score`, etc.); use `res.documents` for document bodies only.

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.BadRequestError       | 400                          | application/json             |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |