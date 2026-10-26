# Vector configuration

Dense vector configuration follows the public OpenAPI at docs revision
[`94a7b71613a3bf217a370d5117b3ff6ddfbae851`](https://github.com/lambdadb/docs/blob/94a7b71613a3bf217a370d5117b3ff6ddfbae851/reference/api/openapi.json).
The relevant JSON pointers are:

- `/components/schemas/EmbeddingConfig`
- `/components/schemas/IndexConfigs/additionalProperties/oneOf/1`
- `/components/schemas/IndexConfigs/additionalProperties/oneOf/2`

This is a scoped contract update. The base Data Versioning
`API_CONTRACT_REVISION` remains unchanged; no full SDK generation is implied.
A source pin records the contract, not deployment or package publication.

## Schema bounds

| Setting | Public contract |
| --- | --- |
| Caller-provided `dimensions` | Required integer, 64-4096 |
| Native `embedding.dimensions` | Optional integer, 64-4096; the server also applies the selected model's maximum |
| `similarity` / `embedding.similarity` | `cosine` or `euclidean` |

Native dimensions and similarity belong inside `embedding`; top-level values
remain invalid on native fields. Omitted native options stay omitted on the
wire so the server resolves defaults. Caller-provided vectors retain the cosine
default. The SDK does not select models or infer their changing capabilities.

The same constraints apply to create/update input and parsed collection metadata.
The server may accept additional legacy configurations, but this SDK follows
the public schema. Query dictionaries remain opaque: the server validates vector
contents, their dimensions against the selected field, and native `queryText`.

## Upgrade requirements

Earlier SDK versions accepted dimensions 1-63, `dot_product`, and
`max_inner_product`. These configurations now fail model validation. The
`Similarity.DOT_PRODUCT` and `Similarity.MAX_INNER_PRODUCT` enum members are
removed. A collection response containing such settings raises
`ResponseValidationError`; migrate those collections before upgrading.

Existing collection index settings cannot be changed in place. Create a new
collection with a supported schema and re-embed/reimport documents as needed.
Padding vectors or replacing a similarity metric can change retrieval behavior;
choose the representation and metric for the application and validate ranking.

Qdrant compatibility accepts dimensions 64-4096 and maps `COSINE`/`EUCLID` to
the corresponding public similarities. `DOT` and `MANHATTAN` requests raise
`UnsupportedQdrantFeatureError`; they are never silently mapped to cosine.

See [native embedding configuration](bayesian-native-embeddings.md) and
[read limits and stored text](read-limits-and-stored-text.md) for complete
requests, stored source paths, and query limits.
