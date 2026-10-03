"""RAG pipeline tests. Embeddings and ChromaDB are faked so the suite stays fast."""
import pytest

from backend.rag import indexer


@pytest.fixture
def sample_project(tmp_path):
    (tmp_path / "auth.py").write_text("def login(user):\n    return token(user)\n")
    (tmp_path / "payment.py").write_text("def charge(token):\n    return validate(token)\n")
    (tmp_path / "README.md").write_text("# Demo\nProject docs.\n")
    (tmp_path / ".env").write_text("SECRET=do-not-index\n")
    (tmp_path / "app.pyc").write_bytes(b"\x00\x01")
    d = tmp_path / "__pycache__"
    d.mkdir()
    (d / "auth.cpython-311.pyc").write_bytes(b"\x00")
    n = tmp_path / "node_modules" / "lib"
    n.mkdir(parents=True)
    (n / "index.js").write_text("module.exports = 1;\n")
    return tmp_path


class FakeCollection:
    def __init__(self):
        self.ids, self.documents, self.metadatas = [], [], []

    def add(self, ids, documents, metadatas, embeddings):
        assert len(embeddings) == len(documents)
        self.ids += ids
        self.documents += documents
        self.metadatas += metadatas

    def count(self):
        return len(self.documents)

    def query(self, query_embeddings, n_results, where=None):
        return {"documents": [self.documents[:n_results]],
                "metadatas": [self.metadatas[:n_results]],
                "distances": [[0.1] * min(n_results, len(self.documents))]}


@pytest.fixture
def fake_store(monkeypatch):
    col = FakeCollection()
    monkeypatch.setattr(indexer, "get_collection", lambda pid: col)
    monkeypatch.setattr(indexer, "clear_project", lambda pid: None)
    monkeypatch.setattr("backend.rag.embeddings.embed", lambda texts: [[0.1, 0.2]] * len(texts))
    monkeypatch.setattr("backend.rag.embeddings.embed_one", lambda text: [0.1, 0.2])
    return col


def test_scan_skips_ignored_dirs_files_and_extensions(sample_project):
    found = indexer.scan_project(str(sample_project))
    assert sorted(found) == ["README.md", "auth.py", "payment.py"]
    assert not any(".env" in f or "node_modules" in f or f.endswith(".pyc") for f in found)


def test_index_project_creates_chunks_with_metadata(sample_project, fake_store):
    res = indexer.index_project(str(sample_project), "test-proj")
    assert res["files_indexed"] == 3
    assert res["chunks_indexed"] == len(fake_store.documents) > 0
    meta = fake_store.metadatas[0]
    assert meta["project_id"] == "test-proj"
    assert meta["file"] in ("auth.py", "payment.py", "README.md")
    assert "language" in meta and "chunk_index" in meta
    assert all("do-not-index" not in d for d in fake_store.documents)


def test_reindex_clears_previous_data(sample_project, fake_store, monkeypatch):
    cleared = {"n": 0}
    monkeypatch.setattr(indexer, "clear_project",
                        lambda pid: cleared.__setitem__("n", cleared["n"] + 1))
    indexer.index_project(str(sample_project), "test-proj", reindex=True)
    indexer.index_project(str(sample_project), "test-proj", reindex=True)
    assert cleared["n"] == 2


def test_similarity_search_returns_files(sample_project, fake_store, monkeypatch):
    from backend.rag import retriever
    monkeypatch.setattr(retriever, "get_collection", lambda pid: fake_store)
    indexer.index_project(str(sample_project), "test-proj")
    results = retriever.search("where is login implemented", "test-proj", top_k=2)
    assert results and "file" in results[0] and results[0]["score"] <= 1.0
    assert retriever.sources_of(results)


def test_build_context_and_sources_deduplicate():
    from backend.rag import retriever
    rows = [{"file": "auth.py", "language": "python", "chunk_index": 0,
             "content": "def login(): ...", "score": 0.9},
            {"file": "auth.py", "language": "python", "chunk_index": 1,
             "content": "def token(): ...", "score": 0.8}]
    ctx = retriever.build_context(rows)
    assert "auth.py" in ctx and "def token" in ctx
    assert retriever.sources_of(rows) == ["auth.py"]


def test_missing_project_path_raises():
    with pytest.raises(FileNotFoundError):
        indexer.index_project("/definitely/not/here")


def test_read_project_file_blocks_path_escape(sample_project):
    assert "login" in indexer.read_project_file(str(sample_project), "auth.py")
    with pytest.raises(ValueError):
        indexer.read_project_file(str(sample_project), "../../etc/passwd")
