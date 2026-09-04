"""Opt-in live Data Versioning smoke test.

Run only against an intended test project with
``LAMBDADB_RUN_VERSIONING_SMOKE=1`` and the documented environment variables.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Callable, Dict, Union
from urllib.parse import urlparse

import pytest

from lambdadb import AliasTarget, LambdaDB, Ref, RefSource, errors, models

pytestmark = pytest.mark.integration


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.fail(f"required environment variable {name} is not set")
    return value


def _required_base_url() -> str:
    value = _required_env("LAMBDADB_BASE_URL").rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        pytest.fail("LAMBDADB_BASE_URL must be an absolute http:// or https:// URL")
    return value


def _wait_for(description: str, condition: Callable[[], bool]) -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(2)
    pytest.fail(f"timed out waiting for {description}")


def _text_index() -> Dict[
    str,
    Union[
        models.IndexConfigsText,
        models.IndexConfigsVector,
        models.IndexConfigs,
        models.IndexConfigsObject,
    ],
]:
    return {
        "title": models.IndexConfigsText(
            type=models.TypeText.TEXT,
            analyzers=[models.Analyzer.STANDARD],
        )
    }


def test_data_versioning_live_smoke() -> None:
    if os.getenv("LAMBDADB_RUN_VERSIONING_SMOKE") != "1":
        pytest.skip("set LAMBDADB_RUN_VERSIONING_SMOKE=1 to run")

    suffix = uuid.uuid4().hex[:10]
    collection_name = f"python-sdk-versioning-{suffix}"
    branch_name = f"candidate-{suffix}"
    tag_name = f"validated-{suffix}"
    alias_name = f"production-{suffix}"
    seed_id = f"seed-{suffix}"
    branch_id = f"branch-{suffix}"
    bulk_id = f"bulk-{suffix}"
    create_attempted = False
    cleanup_complete = False

    client = LambdaDB(
        project_api_key=_required_env("LAMBDADB_PROJECT_API_KEY"),
        base_url=_required_base_url(),
        project_name=_required_env("LAMBDADB_PROJECT_NAME"),
        timeout_ms=30_000,
    )
    collection = client.collection(collection_name)

    try:
        create_attempted = True
        created = client.collections.create(
            collection_name=collection_name,
            index_configs=_text_index(),
            description="Python SDK Data Versioning smoke test",
            tags={"purpose": "sdk-smoke"},
            snapshot_retention_in_days=1,
        )
        assert created.collection.default_branch_name == "main"
        assert created.collection.created_at > 1_000_000_000_000

        updated = client.collections.update(
            collection_name=collection_name,
            description="Python SDK Data Versioning smoke test (updated)",
            tags={"purpose": "sdk-smoke", "state": "updated"},
            snapshot_retention_in_days=2,
        )
        assert updated.collection.snapshot_retention_in_days == 2

        collection.docs.upsert(docs=[{"id": seed_id, "title": "seed"}])

        def main_contains_seed() -> bool:
            response = collection.docs.fetch(ids=[seed_id], consistent_read=True)
            return any(item.doc.get("id") == seed_id for item in response.results)

        _wait_for("seed document on main", main_contains_seed)

        def main_has_snapshot() -> bool:
            return any(
                item.name == "main" and item.snapshot_id
                for item in collection.branches.list().branches
            )

        _wait_for("main branch snapshot", main_has_snapshot)

        branch = collection.branches.create(
            branch_name, source=RefSource.branch("main")
        ).branch
        assert branch.name == branch_name
        assert branch.created_at > 1_000_000_000_000

        with pytest.raises(errors.ResourceAlreadyExistsError):
            collection.branches.create(branch_name)
        with pytest.raises(errors.ResourceNotFoundError):
            collection.branches.delete(f"missing-{suffix}")

        collection.docs.upsert(
            docs=[{"id": branch_id, "title": "initial"}], branch=branch_name
        )

        def branch_contains_doc() -> bool:
            response = collection.docs.fetch(
                ids=[branch_id], consistent_read=True, ref=Ref.branch(branch_name)
            )
            return any(item.doc.get("id") == branch_id for item in response.results)

        _wait_for("branch document", branch_contains_doc)

        collection.docs.update(
            docs=[{"id": branch_id, "title": "updated"}], branch=branch_name
        )
        collection.docs.bulk_upsert_docs(
            docs=[{"id": bulk_id, "title": "bulk"}], branch=branch_name
        )

        def branch_updates_are_visible() -> bool:
            response = collection.docs.fetch(
                ids=[branch_id, bulk_id],
                consistent_read=True,
                ref=Ref.branch(branch_name),
            )
            documents = {item.doc.get("id"): item.doc for item in response.results}
            return (
                documents.get(branch_id, {}).get("title") == "updated"
                and bulk_id in documents
            )

        _wait_for("branch update and bulk upsert", branch_updates_are_visible)

        tag = collection.tags.create(tag_name, source=RefSource.branch(branch_name)).tag
        assert tag.snapshot_id
        alias = collection.aliases.create(
            alias_name, target=AliasTarget.tag(tag_name)
        ).alias
        assert alias.target_name == tag_name

        listed_ids = {
            document.get("id")
            for document in collection.docs.iter_all(
                page_size=1, ref=Ref.alias(alias_name)
            )
        }
        assert seed_id in listed_ids
        assert branch_id in listed_ids

        collection.tags.delete(tag_name)
        _wait_for(
            "dangling alias",
            lambda: any(
                item.alias_name == alias_name and item.dangling
                for item in collection.aliases.list().aliases
            ),
        )
        dangling = next(
            item
            for item in collection.aliases.list().aliases
            if item.alias_name == alias_name
        )
        assert dangling.dangling is True

        with pytest.raises(errors.BadRequestError):
            collection.docs.list(size=1, ref=Ref.alias(alias_name))
        with pytest.raises(errors.BadRequestError):
            collection.docs.fetch(ids=[seed_id], ref=Ref.alias(alias_name))
        with pytest.raises(errors.BadRequestError):
            collection.query(
                query={"queryString": {"query": "title:seed"}},
                ref=Ref.alias(alias_name),
            )

        missing_ref = Ref.alias(f"missing-{suffix}")
        with pytest.raises(errors.ResourceNotFoundError):
            collection.docs.list(size=1, ref=missing_ref)
        with pytest.raises(errors.ResourceNotFoundError):
            collection.docs.fetch(ids=[seed_id], ref=missing_ref)
        with pytest.raises(errors.ResourceNotFoundError):
            collection.query(
                query={"queryString": {"query": "title:seed"}},
                ref=missing_ref,
            )

        retargeted = collection.aliases.retarget(
            alias_name, target=AliasTarget.branch(branch_name)
        ).alias
        assert retargeted.target_name == branch_name
        assert retargeted.alias_revision > alias.alias_revision

        collection.docs.delete(ids=[bulk_id], branch=branch_name)
        client.collections.delete(collection_name=collection_name)
        cleanup_complete = True
    finally:
        if create_attempted and not cleanup_complete:
            try:
                client.collections.delete(collection_name=collection_name)
                cleanup_complete = True
            except Exception as cleanup_error:
                raise AssertionError(
                    f"cleanup failed for collection {collection_name}"
                ) from cleanup_error
        client.close()

    assert cleanup_complete
