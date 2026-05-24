from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from lambdadb.compat.qdrant import QdrantCompatClient, models


pytestmark = pytest.mark.integration


def _require_external_integration_tests() -> None:
    run_external_tests = os.getenv("LAMBDADB_RUN_EXTERNAL_INTEGRATION_TESTS", "").lower()
    if run_external_tests not in {"1", "true", "yes"}:
        pytest.skip("Set LAMBDADB_RUN_EXTERNAL_INTEGRATION_TESTS=1 to run external Qdrant integration tests")


class FakeDocs:
    def __init__(self) -> None:
        self.docs = []
        self.deletes = []

    def upsert(self, *, docs):
        self.docs.extend(docs)
        return SimpleNamespace(message="ok")

    def fetch(self, **kwargs):
        ids = set(kwargs["ids"])
        return SimpleNamespace(
            results=[
                SimpleNamespace(doc=doc)
                for doc in self.docs
                if doc["id"] in ids
            ]
        )

    def delete(self, **kwargs):
        self.deletes.append(kwargs)
        return SimpleNamespace(message="ok")

    def list_pages(self, *, size):
        yield self.docs[:size]


class FakeCollection:
    def __init__(self) -> None:
        self.docs = FakeDocs()
        self.queries = []

    def query(self, **kwargs):
        self.queries.append(kwargs)
        return SimpleNamespace(
            results=[
                SimpleNamespace(score=0.99, doc=doc)
                for doc in self.docs.docs[: kwargs.get("size") or 10]
            ]
        )


class FakeCollections:
    def __init__(self) -> None:
        self.created = []
        self.deleted = []
        self.updated = []
        self.index_configs = {}
        self.num_docs = 0

    def create(self, **kwargs):
        self.created.append(kwargs)
        self.index_configs = kwargs["index_configs"]
        return SimpleNamespace(collection=SimpleNamespace(collection_name=kwargs["collection_name"]))

    def delete(self, **kwargs):
        self.deleted.append(kwargs)
        return SimpleNamespace(message="ok")

    def get(self, **kwargs):
        return SimpleNamespace(collection=SimpleNamespace(num_docs=self.num_docs, index_configs=self.index_configs))

    def update(self, **kwargs):
        self.updated.append(kwargs)
        self.index_configs = kwargs["index_configs"]
        return SimpleNamespace(collection=SimpleNamespace(index_configs=self.index_configs))


class FakeLambdaDB:
    def __init__(self) -> None:
        self.collections = FakeCollections()
        self._collections_by_name = {}

    def collection(self, name):
        if name not in self._collections_by_name:
            self._collections_by_name[name] = FakeCollection()
        return self._collections_by_name[name]


class ExternalCompatClient(QdrantCompatClient):
    def __init__(self) -> None:
        self.fake_lambdadb = FakeLambdaDB()
        self._exists = False
        super().__init__(self.fake_lambdadb)

    def collection_exists(self, collection_name: str, **kwargs) -> bool:
        return self._exists

    def create_collection(self, collection_name: str, *args, **kwargs) -> bool:
        self._exists = True
        return super().create_collection(collection_name, *args, **kwargs)


def test_langchain_qdrant_vector_store_smoke() -> None:
    _require_external_integration_tests()
    langchain_qdrant = pytest.importorskip("langchain_qdrant")
    embeddings_module = pytest.importorskip("langchain_core.embeddings")

    class StaticEmbeddings(embeddings_module.Embeddings):
        def embed_documents(self, texts):
            return [[1.0, 0.0, 0.0] for _ in texts]

        def embed_query(self, text):
            return [1.0, 0.0, 0.0]

    client = ExternalCompatClient()
    client.create_collection(
        collection_name="docs",
        vectors_config=models.VectorParams(size=3),
    )
    store = langchain_qdrant.QdrantVectorStore(
        client=client,
        collection_name="docs",
        embedding=StaticEmbeddings(),
        validate_collection_config=False,
    )

    ids = store.add_texts(
        ["alpha"],
        metadatas=[{"tenant": "acme"}],
        ids=["lc-1"],
    )
    docs = store.similarity_search_by_vector([1.0, 0.0, 0.0], k=1)

    assert ids == ["lc-1"]
    assert docs[0].page_content == "alpha"
    assert docs[0].metadata["tenant"] == "acme"


def test_llama_index_qdrant_vector_store_smoke() -> None:
    _require_external_integration_tests()
    llama_qdrant = pytest.importorskip("llama_index.vector_stores.qdrant")
    schema_module = pytest.importorskip("llama_index.core.schema")
    vector_store_types = pytest.importorskip("llama_index.core.vector_stores.types")

    client = ExternalCompatClient()
    store = llama_qdrant.QdrantVectorStore(
        collection_name="docs",
        client=client,
        dense_vector_name="dense",
        index_doc_id=False,
    )
    node = schema_module.TextNode(
        id_="li-1",
        text="alpha",
        metadata={"tenant": "acme"},
        embedding=[1.0, 0.0, 0.0],
    )

    ids = store.add([node])
    result = store.query(
        vector_store_types.VectorStoreQuery(
            query_embedding=[1.0, 0.0, 0.0],
            similarity_top_k=1,
        )
    )

    assert ids == ["li-1"]
    assert result.ids == ["li-1"]
    assert result.nodes[0].get_content() == "alpha"
