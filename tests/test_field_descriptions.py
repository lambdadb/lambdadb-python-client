"""Optional index field descriptions from the public OpenAPI FieldDescription component."""

from __future__ import annotations

import json

import httpx
import pytest
from pydantic import ValidationError

from lambdadb import LambdaDB, models

EMBEDDING = {"provider": "openai", "model": "text-embedding-3-small", "sourceField": "body"}

DESCRIBED = {
    "id": {"type": "keyword"},
    "title": {"type": "text", "analyzers": ["english"], "description": "Book title as printed on the cover"},
    "year": {"type": "long", "description": "Publication year"},
    "v": {"type": "vector", "dimensions": 128, "similarity": "cosine", "description": "Caller-provided vector"},
    "bodyEmbedding": {"type": "vector", "managedEmbedding": True, "embedding": EMBEDDING, "description": "Native"},
    "author": {
        "type": "object",
        "description": "Author details",
        "objectIndexConfigs": {
            "name": {"type": "keyword", "description": "Full name"},
            "bio": {"type": "text"},
        },
    },
}

PLAIN = {
    "id": {"type": "keyword"},
    "title": {"type": "text", "analyzers": ["english"]},
    "year": {"type": "long"},
    "v": {"type": "vector", "dimensions": 128, "similarity": "cosine"},
    "bodyEmbedding": {"type": "vector", "managedEmbedding": True, "embedding": EMBEDDING},
    "author": {"type": "object", "objectIndexConfigs": {"name": {"type": "keyword"}, "bio": {"type": "text"}}},
}


def _collection(index_configs):
    return {
        "projectName": "project", "collectionName": "books", "indexConfigs": index_configs,
        "description": "", "tags": {}, "defaultBranchName": "main", "snapshotRetentionInDays": 1,
        "createdAt": 1788336000123, "updatedAt": 1788336000123, "numDocs": 0, "numPartitions": 1,
    }


@pytest.mark.parametrize("configs", [DESCRIBED, PLAIN])
def test_create_and_update_models_round_trip_descriptions(configs):
    created = models.CreateCollectionRequest(collection_name="books", index_configs=configs)
    updated = models.UpdateCollectionRequestBody(index_configs=configs)
    assert created.model_dump(mode="json", by_alias=True)["indexConfigs"] == configs
    assert updated.model_dump(mode="json", by_alias=True) == {"indexConfigs": configs}


def test_description_attribute_is_set_on_every_variant():
    request = models.CreateCollectionRequest(collection_name="books", index_configs=DESCRIBED)
    fields = request.index_configs
    assert isinstance(fields["title"], models.IndexConfigsText)
    assert isinstance(fields["year"], models.IndexConfigs)
    assert isinstance(fields["v"], models.IndexConfigsVector)
    assert isinstance(fields["author"], models.IndexConfigsObject)
    assert fields["title"].description == "Book title as printed on the cover"
    assert fields["year"].description == "Publication year"
    assert fields["v"].description == "Caller-provided vector"
    assert fields["bodyEmbedding"].description == "Native"
    assert fields["author"].description == "Author details"
    assert fields["id"].description is None


@pytest.mark.parametrize(
    ("model", "kwargs", "expected"),
    [
        (models.IndexConfigs, {"type": "keyword"}, {"type": "keyword"}),
        (models.IndexConfigsText, {"type": "text"}, {"type": "text"}),
        (models.IndexConfigsVector, {"type": "vector", "dimensions": 64}, {"type": "vector", "dimensions": 64, "similarity": "cosine"}),
        (models.IndexConfigsObject, {"type": "object", "objectIndexConfigs": {"a": {"type": "long"}}}, {"type": "object", "objectIndexConfigs": {"a": {"type": "long"}}}),
    ],
)
def test_absent_or_none_description_is_omitted_from_payloads(model, kwargs, expected):
    # Existing payloads stay byte-identical: no description key is emitted unless one is set.
    assert model.model_validate(kwargs).model_dump(mode="json", by_alias=True) == expected
    assert model.model_validate({**kwargs, "description": None}).model_dump(mode="json", by_alias=True) == expected
    assert model.model_validate(kwargs).description is None


@pytest.mark.parametrize("model_type", ["keyword", "text", "vector", "object"])
def test_empty_description_is_sent_to_clear_on_update(model_type):
    field = {"type": model_type, "description": ""}
    if model_type == "vector":
        field["dimensions"] = 64
    if model_type == "object":
        field["objectIndexConfigs"] = {"a": {"type": "long"}}
    updated = models.UpdateCollectionRequestBody(index_configs={"f": field})
    assert updated.model_dump(mode="json", by_alias=True)["indexConfigs"]["f"]["description"] == ""


@pytest.mark.parametrize("model_type", ["keyword", "text", "vector", "object"])
def test_description_longer_than_255_characters_is_rejected_locally(model_type):
    field = {"type": model_type, "description": "x" * 256}
    if model_type == "vector":
        field["dimensions"] = 64
    if model_type == "object":
        field["objectIndexConfigs"] = {"a": {"type": "long"}}
    with pytest.raises(ValidationError, match="255"):
        models.CreateCollectionRequest(collection_name="books", index_configs={"f": field})
    field["description"] = "x" * 255
    models.CreateCollectionRequest(collection_name="books", index_configs={"f": field})


def test_nested_object_children_given_as_models_keep_descriptions():
    field = models.IndexConfigsObject(
        type=models.TypeObject.OBJECT,
        description="Author details",
        object_index_configs={
            "name": models.IndexConfigs(type=models.Type.KEYWORD, description="Full name"),
            "bio": models.IndexConfigsText(type=models.TypeText.TEXT),
        },
    )
    assert field.model_dump(mode="json", by_alias=True) == DESCRIBED["author"]


@pytest.mark.parametrize("configs", [DESCRIBED, PLAIN])
def test_collection_reads_return_descriptions_only_when_set(configs):
    response = models.GetCollectionResponse.model_validate({"collection": _collection(configs)})
    fields = response.collection.index_configs
    assert fields["title"].description == configs["title"].get("description")
    assert fields["author"].description == configs["author"].get("description")
    assert response.model_dump(mode="json", by_alias=True)["collection"]["indexConfigs"] == configs


def test_descriptions_are_sent_on_create_and_update_and_returned_schema_round_trips():
    sent = []

    def handler(request):
        if request.method != "GET":
            sent.append(json.loads(request.read())["indexConfigs"])
        return httpx.Response(
            201 if request.method == "POST" else 200, json={"collection": _collection(DESCRIBED)}
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        sdk = LambdaDB(client=http, project_api_key="test-key")
        created = sdk.collections.create(collection_name="books", index_configs=DESCRIBED)
        assert created.collection.collection_name == "books"
        returned = sdk.collections.get(collection_name="books").collection.index_configs
        sdk.collections.update(collection_name="books", index_configs=returned)
        # A description-only change on an existing field; other settings stay as returned.
        retitled = {**DESCRIBED, "title": {**DESCRIBED["title"], "description": "Title"}}
        sdk.collections.update(collection_name="books", index_configs=retitled)
        cleared = {**DESCRIBED, "year": {"type": "long", "description": ""}}
        sdk.collections.update(collection_name="books", index_configs=cleared)

    assert sent == [DESCRIBED, DESCRIBED, retitled, cleared]
