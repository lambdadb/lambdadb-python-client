"""Vector constraints from OpenAPI revision 94a7b71."""

import asyncio

import httpx
import pytest
from pydantic import ValidationError

from lambdadb import LambdaDB, errors, models


EMBEDDING = {"provider": "openai", "model": "text-embedding-3-large", "sourceField": "body"}


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("dimensions", [64, 4096])
@pytest.mark.parametrize("similarity", ["cosine", "euclidean"])
def test_vector_schema_bounds_and_metrics(native, dimensions, similarity):
    # Provider/model-specific dimensions remain server validation; these are schema bounds.
    config = {"type": "vector"}
    options = {"dimensions": dimensions, "similarity": similarity}
    config.update({"embedding": {**EMBEDDING, **options}} if native else options)
    request = models.CreateCollectionRequest(collection_name="items", index_configs={"v": config})
    assert request.model_dump(mode="json", by_alias=True)["indexConfigs"]["v"] == config
    update = models.UpdateCollectionRequestBody(index_configs={"v": config})
    assert update.model_dump(mode="json", by_alias=True)["indexConfigs"]["v"] == config


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("dimensions", [1, 63, 4097])
def test_out_of_contract_vector_dimensions(native, dimensions):
    config = {"type": "vector"}
    config.update({"embedding": {**EMBEDDING, "dimensions": dimensions}} if native else {"dimensions": dimensions})
    with pytest.raises(ValidationError, match="between 64 and 4096"):
        models.CreateCollectionRequest(collection_name="items", index_configs={"v": config})


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("similarity", ["dot_product", "max_inner_product"])
def test_out_of_contract_vector_metrics(native, similarity):
    options = {"dimensions": 64, "similarity": similarity}
    config = {"type": "vector"}
    config.update({"embedding": {**EMBEDDING, **options}} if native else options)
    with pytest.raises(ValidationError):
        models.UpdateCollectionRequestBody(index_configs={"v": config})


def test_native_conflicts_still_precede_caller_vector_dimension_checks():
    with pytest.raises(ValidationError, match="Top-level dimensions"):
        models.IndexConfigsVector.model_validate({"type": "vector", "dimensions": 1, "embedding": EMBEDDING})
    config = models.IndexConfigsVector.model_validate({"type": "vector", "embedding": EMBEDDING})
    assert config.model_dump(mode="json", by_alias=True) == {"type": "vector", "embedding": EMBEDDING}
    assert [value.value for value in models.Similarity] == ["cosine", "euclidean"]


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("config", [
    {"type": "vector", "dimensions": 2},
    {"type": "vector", "dimensions": 64, "similarity": "dot_product"},
])
def test_legacy_out_of_contract_collection_metadata_is_a_response_validation_error(async_mode, config):
    body = {"collection": {
        "projectName": "project", "collectionName": "items", "indexConfigs": {"v": config},
        "description": "", "tags": {}, "defaultBranchName": "main", "snapshotRetentionInDays": 1,
        "createdAt": 1788336000123, "updatedAt": 1788336000123, "numDocs": 0, "numPartitions": 1,
    }}

    def handler(_):
        return httpx.Response(200, json=body)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async with LambdaDB(async_client=http, project_api_key="test-key") as sdk:
                await sdk.collections.get_async(collection_name="items")

    with pytest.raises(errors.ResponseValidationError):
        if async_mode:
            asyncio.run(run())
        else:
            with httpx.Client(transport=httpx.MockTransport(handler)) as http:
                with LambdaDB(client=http, project_api_key="test-key") as sdk:
                    sdk.collections.get(collection_name="items")
