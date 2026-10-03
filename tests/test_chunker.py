from backend.rag.chunker import chunk_code

PY = '''import os


def alpha(x):
    return x + 1


def beta(y):
    return y * 2


class Gamma:
    def run(self):
        return alpha(1) + beta(2)
'''


def test_empty_code_produces_no_chunks():
    assert chunk_code("", "python") == []
    assert chunk_code("\n\n   \n", "python") == []


def test_python_logical_chunking_splits_on_definitions():
    chunks = chunk_code(PY, "python")
    assert len(chunks) >= 3
    joined = "\n".join(c["content"] for c in chunks)
    assert "def alpha" in joined and "class Gamma" in joined
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))


def test_window_fallback_for_unknown_language_uses_overlap():
    text = "\n".join("line %d" % i for i in range(200))
    chunks = chunk_code(text, "text", max_lines=50, overlap=10)
    assert len(chunks) > 1
    assert all(len(c["content"].splitlines()) <= 50 for c in chunks)
    assert chunks[1]["start_line"] < chunks[0]["end_line"]  # overlap present


def test_oversized_logical_block_is_split():
    big = "def huge():\n" + "\n".join("    x = %d" % i for i in range(300))
    chunks = chunk_code(big, "python", max_lines=40, overlap=5)
    assert len(chunks) > 1
