"""Similarity search over an indexed project."""
from backend import config
from backend.rag import embeddings
from backend.rag.indexer import get_collection


def search(query, project_id="local-project", top_k=None, file_filter=None):
    """Return a list of dicts: file, language, chunk_index, content, score."""
    top_k = top_k or config.RAG_TOP_K
    collection = get_collection(project_id)
    if collection.count() == 0:
        return []
    # project isolation: the collection is per project AND the metadata filter pins it
    conditions = [{"project_id": project_id}]
    if file_filter:
        conditions.append({"file": file_filter})
    where = conditions[0] if len(conditions) == 1 else {"$and": conditions}
    res = collection.query(query_embeddings=[embeddings.embed_one(query)],
                           n_results=min(top_k, collection.count()), where=where)
    out = []
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[0] * len(docs)])[0]
    for doc, meta, dist in zip(docs, metas, dists):
        out.append({"file": meta.get("file", "unknown"),
                    "language": meta.get("language", "text"),
                    "chunk_index": meta.get("chunk_index", 0),
                    "start_line": meta.get("start_line", 0),
                    "end_line": meta.get("end_line", 0),
                    "content": doc,
                    "score": round(1.0 - float(dist), 4)})
    return out


def build_context(results, max_chars=12000):
    """Format retrieved chunks into a prompt-ready context block."""
    parts, used = [], 0
    for r in results:
        block = ("--- File: %s (lines %s-%s, %s) ---\n%s"
                 % (r["file"], r.get("start_line", "?"), r.get("end_line", "?"),
                    r["language"], r["content"]))
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts) if parts else "(no relevant project context found)"


def sources_of(results):
    seen = []
    for r in results:
        if r["file"] not in seen:
            seen.append(r["file"])
    return seen
