from __future__ import annotations

from types import MethodType, SimpleNamespace

import pytest


class FakeIndexConfigModel:
    def __init__(self, data):
        self.data = data

    def model_dump(self, **kwargs):
        assert kwargs["mode"] == "json"
        return self.data


class FakeDocs:
    def __init__(self) -> None:
        self.upserts = []
        self.deletes = []
        self.fetches = []
        self.list_pages_calls = []
        self.lists = []

    def upsert(self, *, docs):
        self.upserts.append(docs)
        return SimpleNamespace(message="ok")

    def fetch(self, **kwargs):
        self.fetches.append(kwargs)
        return SimpleNamespace(
            results=[
                SimpleNamespace(
                    doc={
                        "id": "1",
                        "_qdrant_id": 1,
                        "_qdrant_vector": [0.1, 0.2],
                        "tenant": "acme",
                    }
                )
            ]
        )

    def delete(self, **kwargs):
        self.deletes.append(kwargs)
        return SimpleNamespace(message="ok")

    def list_pages(self, *, size):
        self.list_pages_calls.append({"size": size})
        yield [
            {
                "id": "1",
                "_qdrant_id": 1,
                "_qdrant_vector": [0.1, 0.2],
                "_qdrant_vector_title": [0.3, 0.4],
                "tenant": "acme",
            }
        ]

    def list(self, **kwargs):
        self.lists.append(kwargs)
        return SimpleNamespace(
            results=[
                {
                    "collection": "docs",
                    "doc": {
                        "id": "1",
                        "_qdrant_id": 1,
                        "_qdrant_vector": [0.1, 0.2],
                        "_qdrant_vector_title": [0.3, 0.4],
                        "tenant": "acme",
                    },
                }
            ],
            next_page_token="next-token",
        )


class FakeCollection:
    def __init__(self) -> None:
        self.docs = FakeDocs()
        self.queries = []

    def query(self, **kwargs):
        self.queries.append(kwargs)
        return SimpleNamespace(
            results=[
                SimpleNamespace(
                    score=0.9,
                    doc={
                        "id": "1",
                        "_qdrant_id": 1,
                        "_qdrant_vector": [0.1, 0.2],
                        "tenant": "acme",
                    },
                )
            ]
        )


class FakeCollections:
    def __init__(self) -> None:
        self.created = []
        self.deleted = []
        self.gets = []
        self.updated = []
        self.index_configs = {}
        self.num_docs = 12

    def create(self, **kwargs):
        self.created.append(kwargs)
        self.index_configs = kwargs.get("index_configs", {})
        return SimpleNamespace(collection=SimpleNamespace(collection_name=kwargs["collection_name"]))

    def delete(self, **kwargs):
        self.deleted.append(kwargs)
        return SimpleNamespace(message="ok")

    def get(self, **kwargs):
        self.gets.append(kwargs)
        return SimpleNamespace(collection=SimpleNamespace(num_docs=self.num_docs, index_configs=self.index_configs))

    def update(self, **kwargs):
        self.updated.append(kwargs)
        self.index_configs = kwargs.get("index_configs", {})
        return SimpleNamespace(collection=SimpleNamespace(collection_name=kwargs["collection_name"], index_configs=self.index_configs))


class FakeLambdaDB:
    def __init__(self) -> None:
        self.collections = FakeCollections()
        self._collections_by_name = {}

    def collection(self, name):
        if name not in self._collections_by_name:
            self._collections_by_name[name] = FakeCollection()
        return self._collections_by_name[name]


def test_qdrant_compat_imports() -> None:
    from lambdadb.compat.qdrant import QdrantClient, QdrantCompatClient, models
    from lambdadb.compat.qdrant.models import PointStruct

    assert QdrantClient is QdrantCompatClient
    assert models.PointStruct is PointStruct


def test_create_collection_maps_vector_params() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models

    fake = FakeLambdaDB()
    client = QdrantCompatClient(fake)

    assert client.create_collection(
        collection_name="docs",
        vectors_config=models.VectorParams(size=3, distance=models.Distance.DOT),
    )

    assert fake.collections.created == [
        {
            "collection_name": "docs",
            "index_configs": {
                "_qdrant_vector": {
                    "type": "vector",
                    "dimensions": 3,
                    "similarity": "dot_product",
                }
            },
        }
    ]


def test_create_collection_maps_payload_schema() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models

    fake = FakeLambdaDB()
    client = QdrantCompatClient(fake)

    assert client.create_collection(
        collection_name="docs",
        vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE),
        payload_schema={
            "tenant": models.PayloadSchemaType.KEYWORD,
            "views": models.PayloadSchemaType.INTEGER,
            "score": models.PayloadSchemaType.FLOAT,
            "active": models.PayloadSchemaType.BOOL,
        },
    )

    assert fake.collections.created[0]["index_configs"] == {
        "_qdrant_vector": {
            "type": "vector",
            "dimensions": 3,
            "similarity": "cosine",
        },
        "tenant": {"type": "keyword"},
        "views": {"type": "long"},
        "score": {"type": "double"},
        "active": {"type": "boolean"},
    }


def test_get_collection_returns_qdrant_style_vector_config() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models

    fake = FakeLambdaDB()
    fake.collections.index_configs = {
        "_qdrant_vector": {
            "type": "vector",
            "dimensions": 3,
            "similarity": "cosine",
        }
    }
    client = QdrantCompatClient(fake)

    collection = client.get_collection(collection_name="docs")

    assert collection.config.params.vectors == models.VectorParams(
        size=3,
        distance=models.Distance.COSINE,
    )


def test_create_payload_index_merges_existing_index_configs() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models

    fake = FakeLambdaDB()
    fake.collections.num_docs = 0
    fake.collections.index_configs = {
        "_qdrant_vector": {
            "type": "vector",
            "dimensions": 3,
            "similarity": "cosine",
        }
    }
    client = QdrantCompatClient(fake)

    assert client.create_payload_index(
        collection_name="docs",
        field_name="tenant",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )

    assert fake.collections.updated == [
        {
            "collection_name": "docs",
            "index_configs": {
                "_qdrant_vector": {
                    "type": "vector",
                    "dimensions": 3,
                    "similarity": "cosine",
                },
                "tenant": {"type": "keyword"},
            },
        }
    ]


def test_create_payload_index_rejects_non_empty_collection() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models
    from lambdadb.compat.qdrant.errors import UnsupportedQdrantFeatureError

    fake = FakeLambdaDB()
    fake.collections.num_docs = 3
    fake.collections.index_configs = {
        "_qdrant_vector": {
            "type": "vector",
            "dimensions": 3,
            "similarity": "cosine",
        }
    }
    client = QdrantCompatClient(fake)

    with pytest.raises(UnsupportedQdrantFeatureError, match="only supported for empty"):
        client.create_payload_index(
            collection_name="docs",
            field_name="tenant",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

    assert fake.collections.updated == []


def test_create_payload_index_is_idempotent_for_existing_index_on_non_empty_collection() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models

    fake = FakeLambdaDB()
    fake.collections.num_docs = 3
    fake.collections.index_configs = {
        "_qdrant_vector": {
            "type": "vector",
            "dimensions": 3,
            "similarity": "cosine",
        },
        "tenant": {"type": "keyword"},
    }
    client = QdrantCompatClient(fake)

    assert client.create_payload_index(
        collection_name="docs",
        field_name="tenant",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )

    assert fake.collections.updated == []


def test_create_payload_index_normalizes_existing_index_models() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models

    fake = FakeLambdaDB()
    fake.collections.num_docs = 3
    fake.collections.index_configs = {
        "tenant": FakeIndexConfigModel({"type": "keyword"}),
    }
    client = QdrantCompatClient(fake)

    assert client.create_payload_index(
        collection_name="docs",
        field_name="tenant",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )

    assert fake.collections.updated == []


def test_upsert_maps_points_to_documents() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models

    fake = FakeLambdaDB()
    client = QdrantCompatClient(fake)
    result = client.upsert(
        collection_name="docs",
        points=[
            models.PointStruct(
                id=1,
                vector=[0.1, 0.2],
                payload={"tenant": "acme"},
            )
        ],
    )

    assert result.status == models.UpdateStatus.COMPLETED
    assert fake.collection("docs").docs.upserts == [
        [
            {
                "id": "1",
                "_qdrant_id": 1,
                "_qdrant_vector": [0.1, 0.2],
                "tenant": "acme",
            }
        ]
    ]


def test_upsert_rejects_reserved_payload_fields() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models
    from lambdadb.compat.qdrant.errors import QdrantCompatValidationError

    client = QdrantCompatClient(FakeLambdaDB())

    with pytest.raises(QdrantCompatValidationError):
        client.upsert(
            collection_name="docs",
            points=[
                models.PointStruct(
                    id=1,
                    vector=[0.1],
                    payload={"_qdrant_vector": [0.2]},
                )
            ],
        )


def test_query_points_maps_vector_and_filter() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models

    fake = FakeLambdaDB()
    client = QdrantCompatClient(fake)

    response = client.query_points(
        collection_name="docs",
        query=[0.1, 0.2],
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="tenant",
                    match=models.MatchValue(value="acme"),
                )
            ],
            must_not=[
                models.FieldCondition(
                    key="status",
                    match=models.MatchValue(value="deleted"),
                )
            ],
        ),
        limit=5,
        with_vectors=True,
    )

    assert response.points[0].id == 1
    assert response.points[0].payload == {"tenant": "acme"}
    assert response.points[0].vector == [0.1, 0.2]
    assert fake.collection("docs").queries == [
        {
            "query": {
                "knn": {
                    "field": "_qdrant_vector",
                    "k": 5,
                    "queryVector": [0.1, 0.2],
                    "filter": {
                        "bool": [
                            {
                                "queryString": {"query": "tenant:acme"},
                                "occur": "filter",
                            },
                            {
                                "queryString": {"query": "status:deleted"},
                                "occur": "must_not",
                            },
                        ]
                    },
                }
            },
            "size": 5,
            "consistent_read": True,
            "include_vectors": True,
        }
    ]


def test_match_text_maps_to_lambdadb_text_filter_terms() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models

    fake = FakeLambdaDB()
    client = QdrantCompatClient(fake)

    client.query_points(
        collection_name="docs",
        query=[0.1, 0.2],
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="body",
                    match=models.MatchText(text="serverless database"),
                )
            ],
        ),
    )

    assert fake.collection("docs").queries[0]["query"]["knn"]["filter"] == {
        "bool": [
            {"queryString": {"query": "body:serverless"}, "occur": "filter"},
            {"queryString": {"query": "body:database"}, "occur": "filter"},
        ]
    }


def test_payload_and_vector_selectors_map_to_fields_and_response() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient

    fake = FakeLambdaDB()
    collection = fake.collection("docs")

    def query(self, **kwargs):
        self.queries.append(kwargs)
        return SimpleNamespace(
            results=[
                SimpleNamespace(
                    score=0.9,
                    doc={
                        "id": "1",
                        "_qdrant_id": 1,
                        "_qdrant_vector": [0.1, 0.2],
                        "_qdrant_vector_title": [0.3, 0.4],
                        "tenant": "acme",
                        "hidden": "value",
                    },
                )
            ]
        )

    collection.query = MethodType(query, collection)
    client = QdrantCompatClient(fake)

    response = client.query_points(
        collection_name="docs",
        query=[0.1, 0.2],
        limit=1,
        with_payload=["tenant"],
        with_vectors=["title"],
    )

    assert response.points[0].payload == {"tenant": "acme"}
    assert response.points[0].vector == {"title": [0.3, 0.4]}
    assert collection.queries[0]["fields"] == {
        "include": ["_qdrant_id", "tenant", "_qdrant_vector_title"]
    }
    assert collection.queries[0]["include_vectors"] is True

    records = client.retrieve(
        collection_name="docs",
        ids=[1],
        with_payload=["tenant"],
        with_vectors=False,
    )

    assert records[0].payload == {"tenant": "acme"}
    assert records[0].vector is None
    assert collection.docs.fetches[-1] == {
        "ids": ["1"],
        "consistent_read": True,
        "include_vectors": False,
        "fields": {"include": ["_qdrant_id", "tenant"]},
    }


def test_scroll_maps_list_documents_and_applies_selectors() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient

    fake = FakeLambdaDB()
    client = QdrantCompatClient(fake)

    records, next_page = client.scroll(
        collection_name="docs",
        limit=3,
        with_payload=["tenant"],
        with_vectors=["title"],
    )

    assert next_page == "next-token"
    assert records[0].id == 1
    assert records[0].payload == {"tenant": "acme"}
    assert records[0].vector == {"title": [0.3, 0.4]}
    assert fake.collection("docs").docs.lists == [
        {
            "size": 3,
            "page_token": None,
            "filter_": None,
            "fields": {"include": ["_qdrant_id", "tenant", "_qdrant_vector_title"]},
            "include_vectors": True,
        }
    ]


def test_retrieve_and_delete_by_ids() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient

    fake = FakeLambdaDB()
    client = QdrantCompatClient(fake)

    records = client.retrieve(collection_name="docs", ids=[1], with_vectors=True)
    delete_result = client.delete(collection_name="docs", points_selector=[1])

    docs = fake.collection("docs").docs
    assert records[0].id == 1
    assert records[0].payload == {"tenant": "acme"}
    assert records[0].vector == [0.1, 0.2]
    assert docs.fetches == [{"ids": ["1"], "consistent_read": True, "include_vectors": True}]
    assert docs.deletes == [{"ids": ["1"]}]
    assert delete_result.status == "completed"


def test_delete_by_filter() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models

    fake = FakeLambdaDB()
    client = QdrantCompatClient(fake)

    result = client.delete(
        collection_name="docs",
        filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="tenant",
                    match=models.MatchValue(value="acme"),
                )
            ]
        ),
    )
    result_from_selector = client.delete(
        collection_name="docs",
        points_selector={
            "filter": {
                "must": [
                    {
                        "key": "status",
                        "match": {"value": "archived"},
                    }
                ]
            }
        },
    )

    assert result.status == "completed"
    assert result_from_selector.status == "completed"
    assert fake.collection("docs").docs.deletes == [
        {"filter_": {"queryString": {"query": "tenant:acme"}}},
        {"filter_": {"queryString": {"query": "status:archived"}}},
    ]


def test_filtered_scroll_maps_extended_list_documents() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models

    fake = FakeLambdaDB()
    client = QdrantCompatClient(fake)
    filt = models.Filter(must=[models.FieldCondition(key="tenant", match=models.MatchValue(value="acme"))])

    records, next_page = client.scroll(collection_name="docs", scroll_filter=filt, offset="page-1")

    assert next_page == "next-token"
    assert records[0].payload == {"tenant": "acme"}
    assert fake.collection("docs").docs.lists == [
        {
            "size": 10,
            "page_token": "page-1",
            "filter_": {"queryString": {"query": "tenant:acme"}},
            "fields": None,
            "include_vectors": False,
        }
    ]


def test_scroll_rejects_qdrant_point_id_offset() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient
    from lambdadb.compat.qdrant.errors import UnsupportedQdrantFeatureError

    client = QdrantCompatClient(FakeLambdaDB())

    with pytest.raises(UnsupportedQdrantFeatureError, match="point-id scroll offsets"):
        client.scroll(collection_name="docs", offset=1)


def test_filtered_count_is_not_implemented() -> None:
    from lambdadb.compat.qdrant import QdrantCompatClient, models
    from lambdadb.compat.qdrant.errors import UnsupportedQdrantFeatureError

    client = QdrantCompatClient(FakeLambdaDB())
    filt = models.Filter(must=[models.FieldCondition(key="tenant", match=models.MatchValue(value="acme"))])

    with pytest.raises(UnsupportedQdrantFeatureError):
        client.count(collection_name="docs", count_filter=filt)
