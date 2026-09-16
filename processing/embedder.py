from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Add a JSON-friendly embedding list to each chunk under 'embedding'."""
    if not chunks:
        return chunks

    vectors = _model().encode(
        [chunk.get("text", "") for chunk in chunks],
        convert_to_numpy=True,
    )
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector.tolist()
    return chunks
