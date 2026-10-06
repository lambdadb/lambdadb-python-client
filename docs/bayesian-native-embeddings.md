# Bayesian search and native embeddings

This scoped extension is pinned to backend
[`9072a1bc8925954369a887f558f1eaf387b7ea0e`](https://github.com/lambdadb/lambdadb/commit/9072a1bc8925954369a887f558f1eaf387b7ea0e):
[QueryRequest](https://github.com/lambdadb/lambdadb/blob/9072a1bc8925954369a887f558f1eaf387b7ea0e/api/src/main/java/ai/lambdadb/dto/QueryRequest.java),
[BayesianQuery](https://github.com/lambdadb/lambdadb/blob/9072a1bc8925954369a887f558f1eaf387b7ea0e/api/src/main/java/ai/lambdadb/model/query/BayesianQuery.java),
[RankableQueryBase](https://github.com/lambdadb/lambdadb/blob/9072a1bc8925954369a887f558f1eaf387b7ea0e/api/src/main/java/ai/lambdadb/model/query/RankableQueryBase.java), and
[FieldConfig](https://github.com/lambdadb/lambdadb/blob/9072a1bc8925954369a887f558f1eaf387b7ea0e/api/src/main/java/ai/lambdadb/model/collection/FieldConfig.java).
The base `API_CONTRACT_REVISION` and the separate reranking/analyzer pins are
unchanged; this does not port every intervening backend change. A source pin
alone does not establish deployment or availability in another environment.

The final merged TypeScript references were
[SDK PR #37](https://github.com/lambdadb/lambdadb-typescript-client/pull/37)
(`b5ca7b6e587592f92ab6817bdd0932a40b1099de`) and
[development publishing PR #38](https://github.com/lambdadb/lambdadb-typescript-client/pull/38)
(`9f5ee314c216d68ea34b932459bdb40072c77290`). Python preserves its own API and
[release policy](../RELEASING.md).

## Bayesian retrieval

All four query methods accept `candidate_size`: `collection.query`,
`collection.query_async`, `collections.query`, and `collections.query_async`.
It serializes as top-level `candidateSize` only when supplied.

```python
query = {
    "bayesian": [
        {"queryString": {"query": "body:restore"}},
        {"knn": {"field": "vector", "queryVector": [1.0, 0.0], "k": 30}},
    ]
}
collection = client.collection("documents")
response = collection.query(query=query, size=10, candidate_size=30)
```

Use the vector dimensions configured on your collection. For a native embedding
field, replace `queryVector` with `queryText`.

- Supply exactly two signals under the top-level `bayesian` key. A signal may
  combine clauses using a `bool` array.
- Explicit `boost`, including `1`, is unsupported on either signal and all of
  its Boolean descendants.
- Rank fusion is top-level only: do not nest `bayesian`, `rrf`, `mm`, or `l2`
  in either signal or its Boolean descendants.
- Without rerank, supply `candidate_size` with
  `1 <= size <= candidate_size <= 100`. Omitting it returns HTTP 400 on this contract.
- With rerank, omit the top-level budget and use `rerank.candidate_size` (model)
  or `rerank["candidateSize"]` (wire dictionary). Omitting the rerank budget
  preserves the existing server default.
- Ordinary text, KNN, RRF, Min-Max (`mm`), and L2 queries do not require and do
  not support top-level `candidateSize`.

Queries remain free-form dictionaries. This SDK has no typed query tree helpers;
no client DSL parser, fusion weights, query defaults, or ranking defaults are
added. The server validates signal counts, boosts, fusion placement, and budget
combinations. Invalid requests remain `BadRequestError` with HTTP 400. Existing
local ref/rerank validation still runs in its original order.

## Managed reranking

```python
from lambdadb import models

response = collection.query(
    query=query,
    size=10,
    rerank=models.RerankConfig(
        provider="typesafe",
        model="jev-1.13.0",
        query_text="How do I restore a previous version?",
        fields=["body"],
        candidate_size=30,
    ),
)
if response.rerank.status == "applied":
    for hit in response.results:
        print(hit.doc["id"], hit.score, hit.retrieval_score)
```

Bayesian fusion runs before reranking. `retrieval_score` preserves the fusion
score; `score` is the final rerank evaluation score when reranking is applied.
Existing response parsing and automatic collection-handle `docsUrl` downloads
remain unchanged. See [managed reranking](managed-reranking.md) for failure
semantics. These scores are not relevance probabilities.

## Native embedding configuration

On compatible servers, `embedding` enables native embeddings without an
explicit `managedEmbedding` flag:

```python
embedding = {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "sourceField": "body",
}
index_configs = {
    "body": {"type": "text"},
    "vector": {"type": "vector", "embedding": embedding},
}
client.collections.create(collection_name="articles", index_configs=index_configs)
client.collections.update(collection_name="articles", index_configs=index_configs)

articles = client.collection("articles")
articles.docs.upsert(docs=[{"id": "one", "body": "Restore a saved version using a branch."}])
response = articles.query(
    query={"knn": {"field": "vector", "queryText": "How do I restore a version?", "k": 30}},
    size=1,
    consistent_read=True,
)
```

This works through sync and async create/update, plain dictionaries,
`IndexConfigsVector`, `EmbeddingConfig`, and their existing TypedDicts. For
legacy servers, retain `"managedEmbedding": True` or `managed_embedding=True`.
Explicit `False` with `embedding` remains invalid. The SDK does not insert the
flag. It continues parsing normalized server metadata with
`managedEmbedding: true` and resolved embedding dimensions/similarity.

Native `dimensions` and `similarity`, if supplied, belong inside `embedding`.
Top-level vector options are rejected for native fields. Omitted embedding
options are omitted on the wire, allowing server defaults. The existing
`EmbeddingConfig.similarity` attribute still defaults to `Similarity.COSINE`;
serialization no longer inserts that value when the caller omitted it. Explicit
similarity values, including cosine, remain serialized. Caller-provided vector
fields continue using top-level `dimensions` and the existing cosine default.
Document vectors and `knn.queryVector` pass through unchanged.

There is no CLI or console entry point in this repository. No command flags or
new CLI are introduced; JSON-compatible dictionaries use the existing SDK API.

## Validation and development packages

After verifying the actual target deployment, load credentials only into the
test process and run:

```bash
LAMBDADB_RUN_BAYESIAN_SMOKE=1 poetry run pytest tests/integration/test_bayesian_native_live.py -m integration -v -s --tb=short
```

Also set `LAMBDADB_BASE_URL`, `LAMBDADB_PROJECT_NAME`, and
`LAMBDADB_PROJECT_API_KEY`. The test creates unique temporary collections and
verifies their deletion with HTTP 404 even after failures. It covers caller
vectors, native and legacy create/update, real document/query embeddings,
ordinary KNN, Bayesian, managed rerank, and server error classification.
Create/revoke temporary project keys and delete temporary projects through the
authorized test-stack admin API separately. Never print credentials or signed
URLs; persistent CI projects/keys must remain untouched.

Python development artifacts do **not** automatically track `develop` pushes.
`.github/workflows/dev-package.yaml` is manually dispatched with `ref` defaulting
to `develop`, requires matching `X.Y.Z.devN` versions, and only uploads GitHub
Actions artifacts. The currently committed `0.11.0` version is not a development
artifact version. Automatic publishing is a separate change; this API support
change does not modify versions, publishing workflows, tags, or releases.

## Validation on 2026-10-06

Base: `origin/develop` at `164a63a5eb80044df056dbb66fa2e3b345215f8f`.
The final staged change was reviewed against that base: only the four SDK source
files, focused tests, and documentation are included. Existing query parsing,
ref/rerank validation order, error classification, response handling, retry
behavior, and caller-vector limits remain unchanged. The intended behavior
changes are candidate budget pass-through, embedding-only acceptance, and
omission of unspecified embedding similarity. No version or workflow changed.

### Deployment evidence

Before live validation, [Deploy Dev run 37422611173](https://github.com/lambdadb/lambdadb/actions/runs/37422611173)
was confirmed successful with head SHA
`9072a1bc8925954369a887f558f1eaf387b7ea0e`. AWS ECS service/task inspection and
ECR digest lookup independently confirmed both services were `COMPLETED`, with
one running task each, task definition revision 16, and tag `dev-v3-9072a1b`:

| Service | Running image digest (also matched ECR) |
| :-- | :-- |
| Gateway | `sha256:300f65269579fcff327366490505327a549e38249c371e93df07f2ae0669bfef` |
| QueryExecutor | `sha256:bf87b32fdcbaf1b17f5cacb3ec8e9f1af1eb7ef51566d06cfb74273e3f857a54` |

The target was `dev-aws-apne2-v3`, API base URL
`https://internal-dev-aws-apne2-v3-c05a2b5d492a.lambdadb.ai`.
No deployment or IAM changes were performed.

### Commands and results

- `poetry install --no-interaction`: passed using the lock file, Python 3.12.13.
- `poetry run pytest tests/ -m 'not integration' -v`: **708 passed**, 45 deselected.
- `poetry run pytest tests/ -v`: **709 passed**, 44 optional integration skips.
- `poetry run mypy src/lambdadb --ignore-missing-imports`: passed, 79 source files.
- `poetry run pylint src/lambdadb`: passed, 10.00/10.
- `poetry run python -c "from lambdadb import LambdaDB; from lambdadb.collection import Collection, CollectionDocs; print('OK')"`: passed.
- For each `V` in `3.10`, `3.11`, `3.13`, ran
  `uv venv --python V /tmp/python-bayesian-validation/pyV`,
  `uv pip install --python /tmp/python-bayesian-validation/pyV/bin/python . pytest`,
  then `/tmp/python-bayesian-validation/pyV/bin/python -m pytest tests/ -m 'not integration' -q`:
  **708 passed**, 45 deselected on each version (3.10.20, 3.11.15, 3.13.13).
- In an isolated build environment with `build` and `twine`, ran
  `/tmp/python-bayesian-validation/build-env/bin/python -m build --outdir /tmp/python-bayesian-validation/dist`
  and `/tmp/python-bayesian-validation/build-env/bin/python -m twine check /tmp/python-bayesian-validation/dist/*`:
  wheel and sdist built and passed. The initial source environment did not have
  `build` installed; build tooling was installed separately without changing project dependencies.
- Installed the wheel into a clean Python 3.12 environment. From outside the
  checkout, verified site-packages imports, version `0.11.0`, native option
  omission, and Bayesian `candidateSize` serialization. Nothing was published.
- `git diff --cached --check`: passed.

### Live results and cleanup

An external, uncommitted administration harness was invoked with
`poetry run python /tmp/python-bayesian-validation/run_live.py`. It read the
stack admin secret through authorized AWS access into memory, created a unique
temporary project, issued a separate project key, and passed that key only in
the child process environment. Its test command was:

```bash
python -m pytest tests/integration/test_bayesian_native_live.py -m integration -v -s --tb=short
```

With `LAMBDADB_RUN_BAYESIAN_SMOKE=1`, the final run passed **3 tests in 55.35s**:

- Bayesian retrieval with caller-provided vectors; consistent/default reads,
  Boolean signals, fixed candidate budget with smaller output, ordinary text,
  KNN, RRF, Min-Max, and L2 without top-level candidate size.
- 23 invalid signal-count, boost, nested-fusion, and candidate-budget requests
  returned server `BadRequestError` / HTTP 400.
- Bayesian + JEV reranking applied through sync and async SDK calls, both scoring
  3/3 candidates and returning two documents with preserved `retrievalScore`.
  Both omitted and explicit rerank candidate budgets were exercised.
- Native embedding-only and legacy true creation, native update, normalized
  metadata, real OpenAI document vectors (1536 finite dimensions), queryText
  embeddings, ordinary KNN, and Bayesian native-vector search.

The first run passed all three feature tests but failed teardown because the
smoke reused an async client across event loops. The test now owns/closes the
async client inside the same loop. Production client lifecycle code was not
changed. The full rerun passed, including teardown.

Both runs deleted all three temporary collections and verified HTTP 404, listed
zero remaining collections, revoked the issued key and verified active-key
absence, deleted the temporary project, and verified project HTTP 404. Final
run project: `python-sdk-bayes-04e410ff66dc`; first run project:
`python-sdk-bayes-b0f105396d4d`. Persistent CI resources were not used or deleted.
Credentials and signed URLs are absent from committed files and validation logs.

Unperformed: unrelated live Data Versioning/Qdrant/query-score suites, a live
large-payload `docsUrl` download (mock response/download regression coverage
passed), package publication/RC installation/promotion, and server deployment.
There is no Python CLI to exercise. No performance or relevance improvement is
claimed. Publishing automation remains outside this API change.
