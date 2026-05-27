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
                SimpleNamespace(doc=_project_doc(doc, kwargs.get("fields")))
                for doc in self.docs
                if doc["id"] in ids
            ]
        )

    def delete(self, **kwargs):
        self.deletes.append(kwargs)
        ids = set(kwargs.get("ids") or [])
        if ids:
            self.docs = [doc for doc in self.docs if doc["id"] not in ids]
        filter_query = kwargs.get("filter_") or kwargs.get("filter")
        if filter_query:
            self.docs = [doc for doc in self.docs if not _matches_filter(doc, filter_query)]
        return SimpleNamespace(message="ok")

    def list_pages(self, *, size):
        yield self.docs[:size]

    def list(self, **kwargs):
        filter_query = kwargs.get("filter_") or kwargs.get("filter")
        docs = [doc for doc in self.docs if _matches_filter(doc, filter_query)]
        return SimpleNamespace(
            results=[
                {"collection": "docs", "doc": _project_doc(doc, kwargs.get("fields"))}
                for doc in docs[: kwargs.get("size") or 10]
            ],
            next_page_token=None,
        )


class FakeCollection:
    def __init__(self) -> None:
        self.docs = FakeDocs()
        self.queries = []

    def query(self, **kwargs):
        self.queries.append(kwargs)
        knn = kwargs["query"]["knn"]
        return SimpleNamespace(
            results=[
                SimpleNamespace(score=0.99, doc=_project_doc(doc, kwargs.get("fields")))
                for doc in self.docs.docs
                if _matches_filter(doc, knn.get("filter"))
            ]
            [: kwargs.get("size") or 10]
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


def test_langchain_qdrant_vector_store_filter_smoke() -> None:
    _require_external_integration_tests()
    langchain_qdrant = pytest.importorskip("langchain_qdrant")
    qdrant_models = pytest.importorskip("qdrant_client.http.models")
    embeddings_module = pytest.importorskip("langchain_core.embeddings")

    class StaticEmbeddings(embeddings_module.Embeddings):
        def embed_documents(self, texts):
            return [[1.0, 0.0, 0.0] if text == "alpha" else [0.0, 1.0, 0.0] for text in texts]

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

    store.add_texts(
        ["alpha", "beta"],
        metadatas=[{"tenant": "acme"}, {"tenant": "other"}],
        ids=["lc-1", "lc-2"],
    )
    docs = store.similarity_search_by_vector(
        [1.0, 0.0, 0.0],
        k=2,
        filter=qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="page_content",
                    match=qdrant_models.MatchValue(value="alpha"),
                )
            ]
        ),
    )

    assert [doc.page_content for doc in docs] == ["alpha"]


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


def test_llama_index_qdrant_vector_store_delete_smoke() -> None:
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
    alpha = schema_module.TextNode(
        id_="li-1",
        text="alpha",
        metadata={"tenant": "acme"},
        relationships={
            schema_module.NodeRelationship.SOURCE: schema_module.RelatedNodeInfo(node_id="alpha-ref")
        },
        embedding=[1.0, 0.0, 0.0],
    )
    beta = schema_module.TextNode(
        id_="li-2",
        text="beta",
        metadata={"tenant": "acme"},
        relationships={
            schema_module.NodeRelationship.SOURCE: schema_module.RelatedNodeInfo(node_id="beta-ref")
        },
        embedding=[0.0, 1.0, 0.0],
    )

    store.add([alpha, beta])
    store.delete("alpha-ref")
    result = store.query(
        vector_store_types.VectorStoreQuery(
            query_embedding=[1.0, 0.0, 0.0],
            similarity_top_k=2,
        )
    )

    assert result.ids == ["li-2"]


def _project_doc(doc, fields):
    include = getattr(fields, "include", None)
    if include is None and isinstance(fields, dict):
        include = fields.get("include")
    if not include:
        return doc
    projected = {"id": doc["id"]}
    for field in include:
        if field in doc:
            projected[field] = doc[field]
    return projected


def _matches_filter(doc, filter_query):
    if not filter_query:
        return True
    if "queryString" in filter_query:
        return _matches_query_string(doc, filter_query["queryString"]["query"])
    if "bool" in filter_query:
        clauses = filter_query["bool"]
        should_matches = []
        for clause in clauses:
            matched = _matches_filter(doc, clause)
            if clause.get("occur") == "must_not":
                if matched:
                    return False
            elif clause.get("occur") == "should":
                should_matches.append(matched)
            elif not matched:
                return False
        return not should_matches or any(should_matches)
    return True


def _matches_query_string(doc, query):
    field, _, expected = str(query).partition(":")
    return str(doc.get(field)) == expected
