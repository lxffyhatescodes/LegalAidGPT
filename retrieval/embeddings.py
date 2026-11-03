import time

import ollama

EMBED_MODEL = "nomic-embed-text"


def _embed(texts, attempts=3):
    for i in range(attempts):
        try:
            return ollama.embed(model=EMBED_MODEL, input=texts, keep_alive="30m")["embeddings"]
        except ollama.ResponseError:
            time.sleep(2 * (i + 1))      # give the Ollama process time to restart
    return None


def embed_documents(texts: list[str]):
    """One vector per text, or None for any text that could not be embedded."""
    prefixed = ["search_document: " + t for t in texts]
    vectors = _embed(prefixed)
    if vectors is not None:
        return vectors
    out = []                              # the batch failed: try one at a time
    for p in prefixed:
        v = _embed([p])
        out.append(v[0] if v else None)
    return out


def embed_query(question: str) -> list[float]:
    out = ollama.embed(model=EMBED_MODEL, input="search_query: " + question, keep_alive="30m")
    return out["embeddings"][0]