"""Project scanning + chunking + embedding + ChromaDB insertion."""
import hashlib
import json
import os

from backend import config
from backend.logging_config import get_logger
from backend.security import (SecurityError, check_file_size, is_probably_binary,
                              safe_project_path, safe_project_root)

log = get_logger("rag.indexer")
from backend.rag import embeddings
from backend.rag.chunker import chunk_code

IGNORED_DIRS = {".git", ".codeforge_backups", "node_modules", "__pycache__", "venv", ".venv", "dist", "build",
                ".idea", ".vscode", ".pytest_cache", "target", ".mypy_cache", "chroma_data", "tools"}
IGNORED_FILES = {".env", ".env.local", ".env.production", "secrets.json", "credentials.json",
                 "id_rsa", ".npmrc", ".pypirc"}
IGNORED_EXTENSIONS = {".pyc", ".class", ".so", ".dll", ".exe", ".lock", ".png", ".jpg",
                      ".jpeg", ".gif", ".pdf", ".zip", ".jar"}
ALLOWED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".h",
                      ".hpp", ".md", ".txt", ".json", ".yml", ".yaml", ".sql", ".go", ".rb"}


LANGUAGE_BY_EXT = {".py": "python", ".js": "javascript", ".jsx": "javascript",
                   ".ts": "typescript", ".tsx": "typescript", ".java": "java", ".c": "c",
                   ".cpp": "cpp", ".h": "c", ".hpp": "cpp", ".md": "markdown",
                   ".json": "json", ".txt": "text", ".sql": "sql", ".go": "go", ".rb": "ruby"}

_client = None


def get_client():
    global _client
    if _client is None:
        import chromadb
        os.makedirs(config.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
        _client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIRECTORY)
    return _client


def collection_name(project_id):
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in project_id)
    return ("proj-" + safe)[:60]


def get_collection(project_id):
    return get_client().get_or_create_collection(
        name=collection_name(project_id), metadata={"hnsw:space": "cosine"})


def language_of(path):
    return LANGUAGE_BY_EXT.get(os.path.splitext(path)[1].lower(), "text")


def scan_project(root, allowed_extensions=None, ignored_dirs=None, ignored_files=None):
    """Return a sorted list of relative paths worth indexing."""
    allowed = allowed_extensions or ALLOWED_EXTENSIONS
    skip_dirs = ignored_dirs or IGNORED_DIRS
    skip_files = ignored_files or IGNORED_FILES
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")
                       or d in (".github",)]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if name in skip_files or name.startswith(".env") or ext in IGNORED_EXTENSIONS:
                continue
            if ext not in allowed:
                continue
            full = os.path.join(dirpath, name)
            try:
                if os.path.getsize(full) > config.MAX_FILE_SIZE_MB * 1024 * 1024:
                    continue
            except OSError:
                continue
            found.append(os.path.relpath(full, root))
    return sorted(found)


def clear_project(project_id):
    try:
        get_client().delete_collection(collection_name(project_id))
    except Exception:
        pass
    try:
        os.remove(_manifest_path(project_id))
    except OSError:
        pass


def _manifest_path(project_id):
    return os.path.join(config.CHROMA_PERSIST_DIRECTORY, "%s.manifest.json"
                        % collection_name(project_id))


def _load_manifest(project_id):
    try:
        with open(_manifest_path(project_id), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _save_manifest(project_id, manifest):
    os.makedirs(config.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    with open(_manifest_path(project_id), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)


def _file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _add_file(collection, project_id, root, rel):
    """Chunk, embed and insert one file. Returns the number of chunks added."""
    full = os.path.join(root, rel)
    try:
        check_file_size(full)
    except SecurityError:
        return 0
    if is_probably_binary(full):
        return 0
    try:
        with open(full, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return 0
    language = language_of(rel)
    ids, docs, metas = [], [], []
    for chunk in chunk_code(text, language):
        ids.append("%s::%s::%d" % (project_id, rel, chunk["chunk_index"]))
        docs.append(chunk["content"])
        metas.append({"project_id": project_id, "file": rel, "language": language,
                      "chunk_index": chunk["chunk_index"],
                      "start_line": chunk["start_line"], "end_line": chunk["end_line"]})
    for i in range(0, len(docs), 64):
        batch = docs[i:i + 64]
        collection.add(ids=ids[i:i + 64], documents=batch, metadatas=metas[i:i + 64],
                       embeddings=embeddings.embed(batch))
    return len(docs)


def _remove_file(collection, project_id, rel):
    try:
        collection.delete(where={"$and": [{"project_id": project_id}, {"file": rel}]})
    except Exception:
        try:
            collection.delete(where={"file": rel})
        except Exception:
            pass


def index_project(project_path, project_id="local-project", reindex=False,
                  progress=None):
    """Index a project into ChromaDB.

    reindex=True wipes the collection and rebuilds it. Otherwise indexing is
    incremental: unchanged files are skipped, modified files are re-indexed,
    new files are added and deleted files have their vectors removed.
    """
    root = safe_project_root(project_path)

    if reindex:
        clear_project(project_id)
        manifest = {}
    else:
        manifest = _load_manifest(project_id)

    collection = get_collection(project_id)
    files = scan_project(root)

    total_size = 0
    new_manifest, added, skipped, updated = {}, 0, 0, 0
    for position, rel in enumerate(files, start=1):
        full = os.path.join(root, rel)
        try:
            total_size += os.path.getsize(full)
            digest = _file_hash(full)
        except OSError:
            continue
        if total_size > config.MAX_PROJECT_SIZE_MB * 1024 * 1024:
            log.warning("project exceeds MAX_PROJECT_SIZE_MB, stopping at %s", rel)
            break
        new_manifest[rel] = digest
        if manifest.get(rel) == digest and collection.count() > 0:
            skipped += 1
            if progress:
                progress(position, len(files), rel, "skipped")
            continue
        if rel in manifest:
            _remove_file(collection, project_id, rel)
            updated += 1
        added += _add_file(collection, project_id, root, rel)
        if progress:
            progress(position, len(files), rel, "indexed")

    for rel in manifest:
        if rel not in new_manifest:
            _remove_file(collection, project_id, rel)

    _save_manifest(project_id, new_manifest)
    log.info("indexed project=%s files=%d chunks_added=%d skipped=%d",
             project_id, len(files), added, skipped)
    return {"project_id": project_id, "files_indexed": len(files),
            "chunks_indexed": added, "files": files, "root": root,
            "files_skipped": skipped, "files_updated": updated,
            "total_chunks": collection.count()}


def scan_for_explorer(root, ignored_dirs=None, ignored_extensions=None):
    """Return a sorted list of relative paths for browsing in the IDE editor.

    Includes configuration files (.env, .gitignore, Dockerfile, etc.)
    while filtering out noisy build artifacts, dependencies and binaries.
    """
    skip_dirs = ignored_dirs or IGNORED_DIRS
    skip_exts = ignored_extensions or IGNORED_EXTENSIONS
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")
                       or d in (".github",)]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in skip_exts:
                continue
            full = os.path.join(dirpath, name)
            try:
                if os.path.getsize(full) > config.MAX_FILE_SIZE_MB * 1024 * 1024:
                    continue
            except OSError:
                continue
            found.append(os.path.relpath(full, root))
    return sorted(found)


def list_project_files(project_path):
    root = safe_project_root(project_path)
    return root, scan_for_explorer(root)


def read_project_file(project_path, relative_path):
    """Read one project file. Path traversal, size and binary content are checked."""
    full = safe_project_path(project_path, relative_path)
    if not os.path.isfile(full):
        raise FileNotFoundError("File not found: %s" % relative_path)
    if is_probably_binary(full):
        raise SecurityError("Refusing to read a binary file: %s" % relative_path)
    check_file_size(full)
    with open(full, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.read()
