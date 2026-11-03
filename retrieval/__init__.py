"""Vector store and retrieval (Chroma + Ollama embeddings)."""
import chromadb

from assistant import config
from .embeddings import embed_documents, embed_query

# Must match the problem_area column in data/source_register.csv
CASE_AREAS = ["arrest", "tenant", "land", "consumer",
              "legal_assistance", "marriage", "employment", "all_areas"]

_client = chromadb.PersistentClient(path=str(config.INDEX_DIR / "chroma"))
collection = _client.get_or_create_collection(
    name="legal_docs",
    metadata={"hnsw:space": "cosine"},
)


def add_chunks(chunks: list[dict]) -> None:
    """chunks: [{"id", "text", "metadata": {...}}]. Skips any chunk that cannot be embedded."""
    vectors = embed_documents([c["text"] for c in chunks])
    keep = [(c, v) for c, v in zip(chunks, vectors) if v is not None]
    for c, v in zip(chunks, vectors):
        if v is None:
            print(f"   !! skipped chunk {c['id']} (could not be embedded)")
    if not keep:
        return
    collection.upsert(
        ids=[c["id"] for c, _ in keep],
        documents=[c["text"] for c, _ in keep],
        embeddings=[v for _, v in keep],
        metadatas=[c["metadata"] for c, _ in keep],
    )

def search(question, case_area=None, jurisdiction=None, k=4, max_distance=None):
    """case_area can be one area name or a list of them. Returns hits shaped
    {"text", "metadata", "distance"} (lower distance = more similar)."""
    if collection.count() == 0:
        return []
    filters = []
    if case_area:
        if isinstance(case_area, str):
            filters.append({"case_area": case_area})
        else:
            filters.append({"case_area": {"$in": list(case_area)}})
    if jurisdiction:
        filters.append({"jurisdiction": jurisdiction})
    where = filters[0] if len(filters) == 1 else ({"$and": filters} if filters else None)

    result = collection.query(
        query_embeddings=[embed_query(question)],
        n_results=k,
        where=where,
    )
    hits = []
    for text, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        if max_distance is not None and dist > max_distance:
            continue
        hits.append({"text": text, "metadata": meta, "distance": dist})
    return hits


def format_context(hits: list[dict]) -> str:
    blocks = []
    for h in hits:
        m = h["metadata"]
        label = f'{m.get("source", "Unknown source")}, section {m.get("section", "?")}'
        blocks.append(f"[{label}]\n{h['text']}")
    return "\n\n".join(blocks)