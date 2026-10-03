"""Analyzer contract: docs 3bda642 plus backend PR #437 merge 55d8882."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import subprocess
import sys

import httpx
import pytest

from lambdadb import LambdaDB, models

NAMES = [
    "standard",
    "english",
    "korean",
    "japanese",
    "chinese",
    "cjk",
    "arabic",
    "french",
    "german",
    "hindi",
    "indonesian",
    "italian",
    "portuguese",
    "russian",
    "spanish",
    "turkish",
    "armenian",
    "basque",
    "bengali",
    "brazilian",
    "bulgarian",
    "catalan",
    "czech",
    "danish",
    "dutch",
    "estonian",
    "finnish",
    "galician",
    "greek",
    "hungarian",
    "irish",
    "latvian",
    "lithuanian",
    "norwegian",
    "persian",
    "romanian",
    "serbian",
    "sorani",
    "swedish",
    "thai",
    "simple",
    "whitespace",
    "stop",
    "keyword",
    "pattern",
    "fingerprint",
    "nepali",
    "tamil",
    "telugu",
]
CASES = [[name] for name in NAMES] + [
    NAMES,
    ["chinese", "cjk"],
    [],
    ["english", "english"],
    ["chinese", "chinese"],
    None,
]


def test_analyzer_source_and_generated_outputs() -> None:
    root = Path(__file__).resolve().parents[1]
    source = json.loads((root / "schemas/text-analyzers.json").read_text())
    assert source["source"]["revision"] == "3bda642f2e7f4f26432f1dfdcb076f656d50f873"
    assert source["extension"]["revision"] == "55d888299fee44466326a9db8016af9811ade13b"
    assert len(NAMES) == len(set(NAMES)) == 49
    assert source["schema"]["items"]["enum"] == NAMES
    assert source["schema"]["default"] == ["standard"]
    assert "minItems" not in source["schema"]
    assert "uniqueItems" not in source["schema"]
    assert [analyzer.value for analyzer in models.Analyzer] == NAMES
    subprocess.run(
        [sys.executable, str(root / "scripts/generate_analyzers.py"), "--check"],
        check=True,
    )


@pytest.mark.parametrize("names", CASES)
@pytest.mark.parametrize("use_model", [False, True], ids=["dict", "model"])
@pytest.mark.parametrize("use_async", [False, True], ids=["sync", "async"])
def test_analyzers_create_and_get_round_trip(names, use_model, use_async) -> None:
    expected_field = {"type": "text"}
    if names is not None:
        expected_field["analyzers"] = names
    if use_model:
        field = models.IndexConfigsText(
            type=models.TypeText.TEXT,
            **(
                {"analyzers": [models.Analyzer(name) for name in names]}
                if names is not None
                else {}
            ),
        )
        assert field.model_dump(mode="json", by_alias=True) == expected_field
    else:
        # Exercise string inputs through the SDK's dictionary conversion path.
        field = expected_field.copy()

    created_body = {
        "collectionName": "articles",
        "description": "",
        "tags": {},
        "defaultBranchName": "main",
        "snapshotRetentionInDays": 7,
        "createdAt": 1788336000123,
    }
    methods = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.method == "POST":
            assert request.url.path == "/projects/project/collections"
            assert json.loads(request.content) == {
                "collectionName": "articles",
                "indexConfigs": {"content": expected_field},
            }
            return httpx.Response(201, json={"collection": created_body})
        assert request.method == "GET"
        assert request.url.path == "/projects/project/collections/articles"
        return httpx.Response(
            200,
            json={
                "collection": {
                    **created_body,
                    "projectName": "project",
                    "indexConfigs": {"content": expected_field},
                    "numPartitions": 1,
                    "numDocs": 0,
                    "updatedAt": 1788336000123,
                }
            },
        )

    options = {
        "project_api_key": "test-key",
        "base_url": "https://api.example",
        "project_name": "project",
    }

    async def run_async():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as transport:
            client = LambdaDB(**options, async_client=transport)
            created = await client.collections.create_async(
                collection_name="articles",
                index_configs={"content": field},
                retries=None,
            )
            assert created.collection.collection_name == "articles"
            return await client.collections.get_async(
                collection_name="articles", retries=None
            )

    if use_async:
        response = asyncio.run(run_async())
    else:
        with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
            client = LambdaDB(**options, client=transport)
            created = client.collections.create(
                collection_name="articles",
                index_configs={"content": field},
                retries=None,
            )
            assert created.collection.collection_name == "articles"
            response = client.collections.get(collection_name="articles", retries=None)

    assert methods == ["POST", "GET"]
    result = response.collection.index_configs["content"]
    assert isinstance(result, models.IndexConfigsText)
    assert result.analyzers == (
        [models.Analyzer(name) for name in names] if names is not None else None
    )
    assert result.model_dump(mode="json", by_alias=True) == expected_field


def test_text_model_accepts_new_strings_and_keeps_none_omitted() -> None:
    field = models.IndexConfigsText.model_validate({"type": "text", "analyzers": NAMES})
    assert all(isinstance(name, models.Analyzer) for name in field.analyzers)
    assert field.model_dump(mode="json") == {"type": "text", "analyzers": NAMES}
    assert models.IndexConfigsText(
        type=models.TypeText.TEXT,
        analyzers=None,
    ).model_dump(mode="json") == {"type": "text"}


@pytest.mark.parametrize("name", ["ENGLISH", "Simple", "KEYWORD", "unknown"])
def test_analyzer_names_remain_case_sensitive_in_sdk(name) -> None:
    from pydantic import ValidationError

    with pytest.raises(ValueError):
        models.Analyzer(name)
    with pytest.raises(ValidationError):
        models.IndexConfigsText.model_validate({"type": "text", "analyzers": [name]})


def test_keyword_analyzer_is_a_text_preset() -> None:
    field = models.IndexConfigsText(type=models.TypeText.TEXT, analyzers=[models.Analyzer.KEYWORD])
    assert field.model_dump(mode="json") == {"type": "text", "analyzers": ["keyword"]}


def test_nested_text_analyzers_in_create_and_update_models() -> None:
    configs = {
        "metadata": {
            "type": "object",
            "objectIndexConfigs": {"body": {"type": "text", "analyzers": NAMES}},
        }
    }
    created = models.CreateCollectionRequest(collection_name="docs", index_configs=configs)
    updated = models.UpdateCollectionRequestBody(index_configs=configs)
    assert created.model_dump(mode="json", by_alias=True)["indexConfigs"] == configs
    assert updated.model_dump(mode="json", by_alias=True) == {"indexConfigs": configs}
