"""Native embedding source mappings from lambdadb OpenAPI revision f9d34b8."""

import httpx
import pytest
from pydantic import ValidationError

from lambdadb import LambdaDB, models


SOURCES = [{"field": "body", "type": "text"}, {"field": "media.photos", "type": "image"}]
COHERE = {"provider": "cohere", "model": "embed-v5.0-pro", "sources": SOURCES, "dimensions": 1024}


@pytest.mark.parametrize("embedding", [
    COHERE,
    {"provider": "openai", "model": "text-embedding-3-small", "sources": SOURCES[:1]},
    {"provider": "openai", "model": "text-embedding-3-small", "sourceField": "body"},
])
def test_source_mappings_round_trip_on_create_and_update(embedding):
    config = {"type": "vector", "embedding": embedding}
    create = models.CreateCollectionRequest(collection_name="items", index_configs={"v": config})
    assert create.model_dump(mode="json", by_alias=True)["indexConfigs"]["v"] == config
    update = models.UpdateCollectionRequestBody(index_configs={"v": config})
    assert update.model_dump(mode="json", by_alias=True)["indexConfigs"]["v"] == config


def test_typed_sources_and_explicit_null_alternative():
    config = models.EmbeddingConfig(
        provider=models.Provider.COHERE,
        model="embed-v5.0-fast",
        source_field=None,
        sources=[models.EmbeddingSource(field="photo", type=models.EmbeddingSourceType.IMAGE)],
    )
    assert config.model_dump(mode="json", by_alias=True) == {
        "provider": "cohere", "model": "embed-v5.0-fast", "sources": [{"field": "photo", "type": "image"}],
    }
    legacy = models.EmbeddingConfig.model_validate({**COHERE, "sources": None, "sourceField": "body"})
    expected = {key: value for key, value in COHERE.items() if key != "sources"}
    assert legacy.model_dump(mode="json", by_alias=True) == {**expected, "sourceField": "body"}


@pytest.mark.parametrize("patch", [
    {"sourceField": "body"}, {"sources": None}, {"sources": []}, {"sources": SOURCES * 8 + SOURCES[:1]},
    {"sources": [{"field": "body"}]}, {"sources": [{"field": " ", "type": "text"}]},
    {"sources": [{"field": "body", "type": "video"}]}, {"sources": None, "sourceField": " "},
])
def test_invalid_source_mappings(patch):
    with pytest.raises(ValidationError):
        models.EmbeddingConfig.model_validate({**COHERE, **patch})


def test_collection_response_preserves_source_mappings():
    stored = {"type": "vector", "managedEmbedding": True, "embedding": {**COHERE, "similarity": "cosine"}}
    body = {"collection": {
        "projectName": "project", "collectionName": "items", "indexConfigs": {"v": stored},
        "description": "", "tags": {}, "defaultBranchName": "main", "snapshotRetentionInDays": 1,
        "createdAt": 1788336000123, "updatedAt": 1788336000123, "numDocs": 0, "numPartitions": 1,
    }}

    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body))) as http:
        response = LambdaDB(client=http, project_api_key="test-key").collections.get(collection_name="items")
    vector = response.collection.index_configs["v"]
    assert [source.type for source in vector.embedding.sources] == [
        models.EmbeddingSourceType.TEXT, models.EmbeddingSourceType.IMAGE]
    assert response.model_dump(mode="json", by_alias=True)["collection"]["indexConfigs"]["v"] == stored
