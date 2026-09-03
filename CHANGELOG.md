# Changelog

## Unreleased

This change implements the Data Versioning API contract pinned to LambdaDB
docs revision
[`63e07d6b2e281704aa3367fbeb94f40f519241b8`](https://github.com/lambdadb/docs/commit/63e07d6b2e281704aa3367fbeb94f40f519241b8).
A source revision records the implemented contract; it does not by itself show
that the API is deployed in a particular environment.

### Added

- Collection-scoped Branch, Tag, and Alias lifecycle APIs under
  `client.collection(name).branches`, `.tags`, and `.aliases`, with matching
  synchronous and asynchronous methods.
- `Ref`, `RefSource`, and `AliasTarget` helpers with early validation of ref
  kind, name, source, target, and branch-only `as_of` combinations.
- Early rejection of `consistent_read=True` with Tag or Alias refs; consistent
  reads require a directly selected Branch.
- Read refs for query, fetch, and list operations. List page iterators and
  all-document iterators retain the ref on every request.
- Write branches for upsert, update, delete, bulk-upload-info, bulk completion,
  and the one-step bulk helper.
- Collection `description`, metadata `tags`, `default_branch_name`, and
  `snapshot_retention_in_days` fields.
- Required signed bulk-upload `headers`. The one-step helper forwards them
  unchanged and accepts a separate `transfer_client` so object-storage traffic
  need not use the LambdaDB API client.
- Epoch-millisecond datetime helpers for collection, branch, tag, and alias
  creation timestamps.
- Runtime dependencies now exclude their next incompatible major versions.
  This keeps `pip install --pre --upgrade lambdadb` from selecting an
  incompatible `httpx` 1.0 development release while opting into the SDK RC.

### Breaking changes from `0.8.2`

- `Collections.create()` and `CreateCollectionRequest` now require
  `index_configs`. The removed `source_project_name`, `source_collection_name`,
  `source_datetime`, and `source_project_api_key` arguments/fields are no
  longer sent.
- The nested value in `CreateCollectionResponse.collection` is now
  `CreatedCollection`, matching the 201 response. It contains
  `collection_name`, `description`, `tags`, `default_branch_name`,
  `snapshot_retention_in_days`, and `created_at`; it is no longer a full
  `CollectionResponse`.
- `CollectionResponse` removes `collection_status`, `source_project_name`,
  `source_collection_name`, and `source_collection_version_id`. It adds
  `description`, `tags`, `default_branch_name`, and
  `snapshot_retention_in_days`. `data_updated_at` and `data_updated_at_dt` are
  now optional.
- `created_at`, `updated_at`, and `data_updated_at` integer values now mean Unix
  epoch **milliseconds**, not seconds. Datetime helpers were corrected
  accordingly.
- Collection creation now accepts HTTP 201 instead of 202. Collection deletion
  now accepts HTTP 200 instead of 202. Document write operations remain HTTP
  202.
- `GetBulkUpsertDocsResponse` now requires `type`, `http_method`,
  `size_limit_bytes`, and `headers`, as required by the signed-upload contract.
- `Collections.update()` / `update_async()` and
  `UpdateCollectionRequestBody.index_configs` no longer require an index
  update. They accept any non-empty combination of `index_configs`,
  `description`, `tags`, and `snapshot_retention_in_days`; an empty update is
  rejected locally. Direct model users will see `index_configs` change from a
  required mapping to a mapping-or-`Unset` field.

### Migration guidance

- Replace cross-collection source creation with an explicit data-copy or import
  workflow appropriate to the application. Data Versioning Branches and Tags
  are collection-scoped snapshots and are **not** a direct replacement for the
  removed cross-collection source feature.
- Create collections with explicit `index_configs`; set metadata and retention
  with `description=`, `tags=`, and `snapshot_retention_in_days=`.
- Replace uses of removed collection fields with the new metadata/versioning
  fields or a Branch/Tag/Alias lifecycle call.
- Treat all returned timestamp integers as milliseconds. Existing code that
  calls `datetime.fromtimestamp(value)` directly must divide by 1000, or use
  the SDK's `*_at_dt` properties.
- Scope reads with `ref=Ref.branch(...)`, `Ref.tag(...)`, or `Ref.alias(...)`.
  Scope writes only with `branch="..."`; tags and aliases are read-only refs.
- For manual bulk upload, forward every value in `info.headers` unchanged and
  use `info.type` as `Content-Type`. Pass the same branch to
  `get_bulk_upsert()` and `bulk_upsert()`.
