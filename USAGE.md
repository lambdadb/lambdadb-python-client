<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous: use base_url + project_name and collection-scoped API
from lambdadb import LambdaDB

with LambdaDB(
    project_api_key="<YOUR_PROJECT_API_KEY>",
    base_url="https://api.lambdadb.ai",
    project_name="playground",
) as client:
    res = client.collections.list()
    print(res)

    # Collection-scoped (recommended for document operations)
    coll = client.collection("my_collection")
    docs = coll.docs.list()
    coll.docs.upsert(docs=[{"id": "1", "text": "hello"}])
    results = coll.query(query={"queryString": {"query": "hello"}})
```

```python
# Asynchronous
import asyncio
from lambdadb import LambdaDB

async def main():
    async with LambdaDB(
        project_api_key="<YOUR_PROJECT_API_KEY>",
        base_url="https://api.lambdadb.ai",
        project_name="playground",
    ) as client:
        res = await client.collections.list_async()
        print(res)

        coll = client.collection("my_collection")
        docs = await coll.docs.list_async()

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->
