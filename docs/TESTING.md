# SDK Testing (Pre-publish Checklist)

## Current status

| Item | Status |
|------|--------|
| **Unit test file** | `tests/test_sdk.py` added (7 test cases) |
| **pytest** | Added to dev dependencies in `pyproject.toml` |
| **CI** | Import check + mypy + pylint; pytest step added to run tests on push/PR |

## How to run tests

After installing dependencies:

```bash
poetry install --no-interaction
poetry run pytest tests/ -v
```

Or:

```bash
pip install -e ".[dev]"  # or install project dependencies
pytest tests/ -v
```

## Test coverage (`tests/test_sdk.py`)

- **test_imports**: Core imports (LambdaDB, RequestOptions, response types, etc.)
- **test_client_collection_docs_has_convenience_methods**: Presence of `coll.docs.list_pages`, `iter_all`, `bulk_upsert_docs`
- **test_collections_has_list_pages_and_iter_all**: Presence of `client.collections.list_pages`, `iter_all` and async variants
- **test_request_options_instantiation**: RequestOptions construction
- **test_collection_response_has_datetime_properties**: CollectionResponse `created_at_dt` and related datetime properties
- **test_list_collections_response_has_next_page_token**: ListCollectionsResponse `next_page_token` field
- **test_query_and_fetch_response_has_results_and_documents**: Query/Fetch responses `.results` and `.documents`

All tests validate the **public API surface only**, with **no network calls or API keys**.

## Pre-publish recommendations

1. **Run tests locally once**  
   Confirm all 7 tests pass with `poetry run pytest tests/ -v`.

2. **CI**  
   `.github/workflows/ci.yaml` includes a “Run tests” step so tests run on every push/PR.

3. **Optional additional tests**  
   - Pagination behavior of `list_pages` / `iter_all` (with mocks or test API)
   - `bulk_upsert_docs` presigned URL upload flow (mocked)
   - `_resolve_fetch_response` / `_resolve_query_response` (mocked HTTP)

The current tests are sufficient for **minimal pre-publish verification**.
