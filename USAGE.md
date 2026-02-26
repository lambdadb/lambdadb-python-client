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
    list_res = coll.docs.list()
    items = list_res.results          # or list_res.documents for doc bodies only
    coll.docs.upsert(docs=[{"id": "1", "text": "hello"}])
    res = coll.query(query={"queryString": {"query": "hello"}})
    docs_only = res.documents         # use res.results for score/metadata
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
        list_res = await coll.docs.list_async()
        items = list_res.results

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->
