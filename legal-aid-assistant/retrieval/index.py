"""Task 1.4: ChromaDB index and retrieval."""
import json
import re
import sys

from assistant import config

COLLECTION = "legal_chunks"
STOP = {"the", "and", "for", "what", "how", "can", "does", "are", "who",
        "must", "with", "that", "this", "any", "has", "have", "from", "your"}
_model = None


def load_chunks():
    with open(config.CHUNKS_FILE, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def get_client():
    import chromadb
    config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.INDEX_DIR))


def build_index(batch=128):
    chunks = load_chunks()
    client = get_client()
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    model = get_model()
    for i in range(0, len(chunks), batch):
        part = chunks[i:i + batch]
        vecs = model.encode([c["text"] for c in part],
                            normalize_embeddings=True).tolist()
        col.add(ids=[c["chunk_id"] for c in part],
                documents=[c["text"] for c in part],
                embeddings=vecs,
                metadatas=[c["label"] for c in part])
        print(f"indexed {min(i + batch, len(chunks))}/{len(chunks)}")
    return len(chunks)


def _result(chunk_id, text, label, sim):
    return {"chunk_id": chunk_id, "text": text, "label": label,
            "similarity": round(sim, 3),
            "doc_title": label.get("doc_title", ""),
            "section": label.get("section", ""),
            "excerpt": text[:300]}


def keyword_search(question, top_k=None, problem_area=None):
    words = {w for w in re.findall(r"[a-z]{3,}", question.lower())
             if w not in STOP}
    scored = []
    for c in load_chunks():
        if problem_area and c["label"]["problem_area"] != problem_area:
            continue
        hay = set(re.findall(r"[a-z]{3,}", c["text"].lower()))
        score = len(words & hay) / (len(words) or 1)
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    return [_result(c["chunk_id"], c["text"], c["label"], s)
            for s, c in scored[: top_k or config.TOP_K]]


def search(question, top_k=None, problem_area=None):
    """Return the best passages with their labels, dropping weak matches."""
    top_k = top_k or config.TOP_K
    try:
        model = get_model()
        col = get_client().get_collection(COLLECTION)
        q = model.encode([question], normalize_embeddings=True).tolist()
        where = {"problem_area": problem_area} if problem_area else None
        res = col.query(query_embeddings=q, n_results=top_k, where=where)
    except Exception as e:
        print("Vector search unavailable, using keyword search:", e,
              file=sys.stderr)
        return keyword_search(question, top_k, problem_area)
    out = []
    for cid, doc, meta, dist in zip(res["ids"][0], res["documents"][0],
                                    res["metadatas"][0], res["distances"][0]):
        sim = 1 - dist  # Chroma returns cosine distance
        if sim >= config.MIN_SIMILARITY:
            out.append(_result(cid, doc, meta, sim))
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        print("chunks indexed:", build_index())
    else:
        q = " ".join(sys.argv[1:]) or "What age can someone marry in Nigeria?"
        for r in search(q):
            print(f"[{r['similarity']}] {r['doc_title']}, s.{r['section']}")
            print("   ", r["text"][:200], "\n")