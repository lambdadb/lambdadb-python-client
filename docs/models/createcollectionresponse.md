# CreateCollectionResponse

Created collection response returned with HTTP 201.

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `collection` | [models.CollectionResponse](collectionresponse.md) | Yes | The created collection, in the same shape as a collection read, including the normalized `index_configs` of its main Branch. |
