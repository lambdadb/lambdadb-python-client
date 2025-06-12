<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from lambdadb import Lambdadb


with Lambdadb(
    project_api_key="<YOUR_PROJECT_API_KEY>",
) as l_client:

    res = l_client.projects.collections.list(project_name="<value>")

    # Handle response
    print(res)
```

</br>

The same SDK client can also be used to make asychronous requests by importing asyncio.
```python
# Asynchronous Example
import asyncio
from lambdadb import Lambdadb

async def main():

    async with Lambdadb(
        project_api_key="<YOUR_PROJECT_API_KEY>",
    ) as l_client:

        res = await l_client.projects.collections.list_async(project_name="<value>")

        # Handle response
        print(res)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->