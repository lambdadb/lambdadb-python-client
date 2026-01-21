<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from lambdadb import LambdaDB


with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
) as lambda_db:

    res = lambda_db.collections.list()

    # Handle response
    print(res)
```

</br>

The same SDK client can also be used to make asynchronous requests by importing asyncio.

```python
# Asynchronous Example
import asyncio
from lambdadb import LambdaDB

async def main():

    async with LambdaDB(
        project_api_key="<YOUR_PROJECT_API_KEY>",
    ) as lambda_db:

        res = await lambda_db.collections.list_async()

        # Handle response
        print(res)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->