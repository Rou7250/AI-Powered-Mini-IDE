"""Sentence-Transformers embedding function, loaded lazily and cached."""
from backend import config

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def embed(texts):
    """texts: list[str] -> list[list[float]]"""
    if not texts:
        return []
    vectors = get_model().encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return [v.tolist() for v in vectors]


def embed_one(text):
    return embed([text])[0]
