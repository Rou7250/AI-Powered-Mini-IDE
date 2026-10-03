"""Code chunking: logical boundaries where practical, line windows as fallback."""
import re

from backend import config

BOUNDARIES = {
    "python": re.compile(r"^(@\w|def\s|class\s|async\s+def\s)"),
    "javascript": re.compile(r"^(export\s|function\s|class\s|const\s+\w+\s*=\s*(\(|async|function))"),
    "typescript": re.compile(r"^(export\s|function\s|class\s|interface\s|type\s|const\s+\w+\s*=)"),
    "java": re.compile(r"^\s{0,4}(public|private|protected|static|class|interface|enum)\s"),
    "c": re.compile(r"^[A-Za-z_][\w\s\*]*\([^;]*\)\s*\{?\s*$"),
    "cpp": re.compile(r"^[A-Za-z_][\w\s\*:<>]*\([^;]*\)\s*\{?\s*$"),
    "markdown": re.compile(r"^#{1,6}\s"),
}


def _windows(lines, max_lines, overlap):
    step = max(1, max_lines - overlap)
    out = []
    i = 0
    while i < len(lines):
        out.append((i, min(len(lines), i + max_lines)))
        if i + max_lines >= len(lines):
            break
        i += step
    return out


def _logical(lines, pattern, max_lines):
    starts = [i for i, ln in enumerate(lines) if pattern.match(ln)]
    if not starts:
        return None
    if starts[0] != 0:
        starts.insert(0, 0)
    spans = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        if not lines[start:end]:
            continue
        # merge tiny blocks (decorators, one-liners) with the following block
        if spans and (end - start) < 4 and (spans[-1][1] - spans[-1][0]) + (end - start) <= max_lines:
            spans[-1] = (spans[-1][0], end)
        else:
            spans.append((start, end))
    return spans or None


def chunk_code(text, language="text", max_lines=None, overlap=None):
    """Return a list of dicts: {content, start_line, end_line, chunk_index}."""
    max_lines = max_lines or config.MAX_CHUNK_LINES
    overlap = config.CHUNK_OVERLAP_LINES if overlap is None else overlap
    lines = (text or "").splitlines()
    if not [ln for ln in lines if ln.strip()]:
        return []

    pattern = BOUNDARIES.get(language)
    spans = _logical(lines, pattern, max_lines) if pattern else None
    if not spans:
        spans = _windows(lines, max_lines, overlap)

    final = []
    for start, end in spans:
        if end - start <= max_lines:
            final.append((start, end))
        else:  # oversized logical block -> split with overlap
            for s, e in _windows(lines[start:end], max_lines, overlap):
                final.append((start + s, start + e))

    chunks = []
    for i, (start, end) in enumerate(final):
        content = "\n".join(lines[start:end]).strip("\n")
        if not content.strip():
            continue
        chunks.append({"content": content, "start_line": start + 1,
                       "end_line": end, "chunk_index": i})
    return chunks
