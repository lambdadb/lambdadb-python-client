# SDK testing

This document describes local, CI, development-package, and prerelease
validation for the Python SDK.

## Local setup

Install the locked development environment:

```bash
poetry install --no-interaction
```

The lock uses pytest 9.0.3 or newer on supported Python 3.10 through 3.13.
Python 3.9 is no longer supported by the SDK development line.

## Non-integration tests

Run the deterministic test suite without live services or third-party SDKs:

```bash
poetry run pytest tests/ -m "not integration" -v
```

These tests cover the public SDK surface, request and response models, retry and
client lifecycle behavior, native embedding configuration, document helpers,
and the Qdrant compatibility layer.

## Static checks

Run the configured type and lint checks:

```bash
poetry run mypy src/lambdadb --ignore-missing-imports
poetry run pylint src/lambdadb
```

The normal CI workflow requires both checks to pass.

## Distribution checks

Build and inspect the wheel and source distribution:

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

Install the wheel in a clean environment and verify the installed package,
rather than importing from the source checkout:

```bash
python -m venv /tmp/lambdadb-wheel-check
/tmp/lambdadb-wheel-check/bin/python -m pip install dist/*.whl
/tmp/lambdadb-wheel-check/bin/python -c \
  "from lambdadb import LambdaDB, __version__; print(__version__)"
```

## Full live suite (release gate)

`scripts/run_live_smoke.py` runs every `tests/integration/test_*_live.py` file in
one sequential pytest process with all suite flags enabled, and fails if any
live test is skipped. The publish workflow runs it against the dev environment
for development `main` pushes and against production for release verification
and Releases. It reads the project API key from AWS Secrets Manager itself; see
[Deployed live smoke gate](../RELEASING.md#deployed-live-smoke-gate) for the
required configuration and a local invocation.

To run the same suite with a key you already hold, export the three connection
variables (or load `.env.local` without printing it) and enable every suite:

```bash
LAMBDADB_RUN_LIVE_TESTS=1 LAMBDADB_RUN_VERSIONING_SMOKE=1 \
LAMBDADB_RUN_QUERY_SCORE_SMOKE=1 LAMBDADB_RUN_BAYESIAN_SMOKE=1 \
poetry run python -m pytest tests/integration/test_*_live.py -p scripts.run_live_smoke -v
```

Use `python -m pytest` so the plugin module resolves from the repository root.
The sections below run individual suites.

## Live LambdaDB smoke test

The live test creates and removes test data. Run it only against the intended
development or staging project:

```bash
LAMBDADB_RUN_LIVE_TESTS=1 \
poetry run pytest tests/integration/test_qdrant_compat_live.py -v
```

Required configuration:

- `LAMBDADB_PROJECT_API_KEY`
- `LAMBDADB_PROJECT_NAME`
- `LAMBDADB_BASE_URL` as an absolute `http://` or `https://` URL when the
  default API URL is not the test target

Do not expose credentials in command output, logs, artifacts, or review notes.

Run the Data Versioning smoke test separately. It creates a uniquely named
temporary collection and deletes it through a `finally` cleanup path:

```bash
LAMBDADB_RUN_VERSIONING_SMOKE=1 \
poetry run pytest tests/integration/test_data_versioning_live.py -v
```

The smoke test allows up to three minutes for the main Branch's committed
snapshot to appear after an upsert; a consistent read may show the document
earlier through the pending-write overlay.

If `.env.local` exists, load it without printing its values before running the
command. If cleanup fails, report only the temporary collection name; never
include request headers or credentials.

## Query scores and keyword facets

Run the opt-in query response contract smoke against the intended test project:

```bash
LAMBDADB_RUN_QUERY_SCORE_SMOKE=1 \
poetry run pytest tests/integration/test_query_scores_live.py -m integration -v
```

Export `LAMBDADB_BASE_URL`, `LAMBDADB_PROJECT_NAME`, and
`LAMBDADB_PROJECT_API_KEY` first (or load `.env.local` without printing it).
The test creates a uniquely named collection with six synthetic documents
(6.6 MB total payload), waits up to 180 seconds for committed visibility, and
verifies deletion with HTTP 404 in fixture cleanup, including after failures.

The matrix covers omitted, empty-object, and queryString queries; facets on/off;
sync/async; inline documents, actual `docsUrl` downloads, and facet-only requests.
It verifies both raw JSON score types and parsed finite score values. Absent or
null scores are accepted; strings (including `"NaN"`), booleans, NaN and infinity
are rejected. This is necessary because Pydantic can silently coerce a `"NaN"`
string into a float NaN. Ordinary SDK parsing success alone is not a score
contract check. Raw score checks include the downloaded document array.

These checks target the query contract pinned in [keyword-facets.md](keyword-facets.md).
No production SDK coercion or error behavior is changed. The same file includes
mock regression checks that run in the non-integration suite and prove invalid
scores are detected even when SDK parsing succeeds. Live failures are not marked
as expected failures and must be reported separately from local test results.

## Bayesian search and native embedding smoke

Verify the actual deployed backend revision first, then run the opt-in suite:

```bash
LAMBDADB_RUN_BAYESIAN_SMOKE=1 \
poetry run pytest tests/integration/test_bayesian_native_live.py -m integration -v -s --tb=short
```

Use the same three connection environment variables as above. The suite creates
unique collections, tests actual document/query embeddings and native reranking,
and verifies collection deletion with HTTP 404. It includes Cohere text/image
`sources`, `queryInputs`, direct and bulk-uploaded vectors on native fields, and
Cohere reranking, so the server must have Cohere credentials configured. See the
[scoped contract guide](bayesian-native-embeddings.md) for limits and temporary
project/key cleanup. This repository has no CLI to validate.

## Third-party compatibility smoke tests

The external compatibility tests require their optional dependencies and an
explicit opt-in:

```bash
LAMBDADB_RUN_EXTERNAL_INTEGRATION_TESTS=1 \
poetry run pytest tests/integration/test_qdrant_compat_external.py -v
```

Record dependency versions and the exact SDK commit when reporting these
results.

## Workflow coverage

- `.github/workflows/ci.yaml` runs imports and the existing test suite for
  pushes and pull requests on `main`.
- `.github/workflows/dev-package.yaml` runs non-integration tests, derives an
  `X.Y.Z.devN` version from tags in its checkout, checks distributions, and
  uploads a commit-specific wheel artifact without publishing to PyPI.
- `.github/workflows/publish.yaml` validates an untagged RC or stable version
  committed on `main` or a published GitHub Release, tests Python 3.10 through
  3.13, checks the built distributions, verifies wheel installation, and runs
  the full live suite against production. Only a GitHub Release publishes,
  through PyPI Trusted Publishing, after all required jobs succeed; a `main` push
  whose version is already tagged on `origin` runs only the full live suite
  against the dev environment.

See [RELEASING.md](../RELEASING.md) for the required release sequence.
