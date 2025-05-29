# Projects
(*projects*)

## Overview

### Available Operations

* [list](#list) - List all projects in an account.
* [create](#create) - Create a project.
* [get](#get) - Get metadata of an existing project.
* [delete](#delete) - Delete an existing project.
* [update](#update) - Configure an existing project

## list

List all projects in an account.

### Example Usage

```python
from lambdadb import Lambdadb, models


with Lambdadb() as l_client:

    res = l_client.projects.list(security=models.ListProjectsSecurity(
        admin_api_key="<YOUR_ADMIN_API_KEY>",
    ))

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `security`                                                          | [models.ListProjectsSecurity](../../listprojectssecurity.md)        | :heavy_check_mark:                                                  | The security requirements to use for the request.                   |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.ListProjectsResponse](../../models/listprojectsresponse.md)**

### Errors

| Error Type                  | Status Code                 | Content Type                |
| --------------------------- | --------------------------- | --------------------------- |
| errors.UnauthenticatedError | 401                         | application/json            |
| errors.TooManyRequestsError | 429                         | application/json            |
| errors.InternalServerError  | 500                         | application/json            |
| errors.APIError             | 4XX, 5XX                    | \*/\*                       |

## create

Create a project.

### Example Usage

```python
from lambdadb import Lambdadb, models


with Lambdadb() as l_client:

    res = l_client.projects.create(security=models.CreateProjectSecurity(
        admin_api_key="<YOUR_ADMIN_API_KEY>",
    ), request={
        "project_name": "example-project-name",
        "rate_limit": 10,
    })

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `request`                                                           | [models.CreateProjectRequest](../../models/createprojectrequest.md) | :heavy_check_mark:                                                  | The request object to use for the request.                          |
| `security`                                                          | [models.CreateProjectSecurity](../../createprojectsecurity.md)      | :heavy_check_mark:                                                  | The security requirements to use for the request.                   |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.ProjectResponse](../../models/projectresponse.md)**

### Errors

| Error Type                        | Status Code                       | Content Type                      |
| --------------------------------- | --------------------------------- | --------------------------------- |
| errors.BadRequestError            | 400                               | application/json                  |
| errors.UnauthenticatedError       | 401                               | application/json                  |
| errors.ResourceAlreadyExistsError | 409                               | application/json                  |
| errors.TooManyRequestsError       | 429                               | application/json                  |
| errors.InternalServerError        | 500                               | application/json                  |
| errors.APIError                   | 4XX, 5XX                          | \*/\*                             |

## get

Get metadata of an existing project.

### Example Usage

```python
from lambdadb import Lambdadb, models


with Lambdadb() as l_client:

    res = l_client.projects.get(security=models.GetProjectSecurity(
        admin_api_key="<YOUR_ADMIN_API_KEY>",
    ), project_name="<value>")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `security`                                                          | [models.GetProjectSecurity](../../models/getprojectsecurity.md)     | :heavy_check_mark:                                                  | N/A                                                                 |
| `project_name`                                                      | *str*                                                               | :heavy_check_mark:                                                  | Project name.                                                       |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.ProjectResponse](../../models/projectresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |

## delete

Delete an existing project.

### Example Usage

```python
from lambdadb import Lambdadb, models


with Lambdadb() as l_client:

    res = l_client.projects.delete(security=models.DeleteProjectSecurity(
        admin_api_key="<YOUR_ADMIN_API_KEY>",
    ), project_name="<value>")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                             | Type                                                                  | Required                                                              | Description                                                           |
| --------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `security`                                                            | [models.DeleteProjectSecurity](../../models/deleteprojectsecurity.md) | :heavy_check_mark:                                                    | N/A                                                                   |
| `project_name`                                                        | *str*                                                                 | :heavy_check_mark:                                                    | Project name.                                                         |
| `retries`                                                             | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)      | :heavy_minus_sign:                                                    | Configuration to override the default retry behavior of the client.   |

### Response

**[models.DeleteProjectResponse](../../models/deleteprojectresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |

## update

Configure an existing project

### Example Usage

```python
from lambdadb import Lambdadb, models


with Lambdadb() as l_client:

    res = l_client.projects.update(security=models.UpdateProjectSecurity(
        admin_api_key="<YOUR_ADMIN_API_KEY>",
    ), project_name="<value>", rate_limit=20)

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                             | Type                                                                  | Required                                                              | Description                                                           |
| --------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `security`                                                            | [models.UpdateProjectSecurity](../../models/updateprojectsecurity.md) | :heavy_check_mark:                                                    | N/A                                                                   |
| `project_name`                                                        | *str*                                                                 | :heavy_check_mark:                                                    | Project name.                                                         |
| `rate_limit`                                                          | *float*                                                               | :heavy_check_mark:                                                    | N/A                                                                   |
| `retries`                                                             | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)      | :heavy_minus_sign:                                                    | Configuration to override the default retry behavior of the client.   |

### Response

**[models.ProjectResponse](../../models/projectresponse.md)**

### Errors

| Error Type                   | Status Code                  | Content Type                 |
| ---------------------------- | ---------------------------- | ---------------------------- |
| errors.BadRequestError       | 400                          | application/json             |
| errors.UnauthenticatedError  | 401                          | application/json             |
| errors.ResourceNotFoundError | 404                          | application/json             |
| errors.TooManyRequestsError  | 429                          | application/json             |
| errors.InternalServerError   | 500                          | application/json             |
| errors.APIError              | 4XX, 5XX                     | \*/\*                        |