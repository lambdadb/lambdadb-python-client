<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from lambdadb import Lambdadb, models


with Lambdadb() as l_client:

    res = l_client.projects.list(security=models.ListProjectsSecurity(
        admin_api_key="<YOUR_ADMIN_API_KEY>",
    ))

    # Handle response
    print(res)
```

</br>

The same SDK client can also be used to make asychronous requests by importing asyncio.
```python
# Asynchronous Example
import asyncio
from lambdadb import Lambdadb, models

async def main():

    async with Lambdadb() as l_client:

        res = await l_client.projects.list_async(security=models.ListProjectsSecurity(
            admin_api_key="<YOUR_ADMIN_API_KEY>",
        ))

        # Handle response
        print(res)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->