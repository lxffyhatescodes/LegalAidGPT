"""Build the embedding index once (needs internet the first time to download the model).
Run:  python -m backend.chunker   then   python -m backend.build_index
"""
import json
import faiss
from sentence_transformers import SentenceTransformer

from . import settings as config
from .retriever import load_chunks

chunks = load_chunks()
model = SentenceTransformer(config.EMBEDDING_MODEL)
vecs = model.encode([f'{c["doc_title"]}. {c["text"]}' for c in chunks],
                    batch_size=64, show_progress_bar=True, normalize_embeddings=True).astype("float32")
index = faiss.IndexFlatIP(vecs.shape[1])
index.add(vecs)
config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
faiss.write_index(index, str(config.INDEX_FILE))
config.INDEX_IDS_FILE.write_text(json.dumps([c["chunk_id"] for c in chunks]), encoding="utf-8")
print(f"Indexed {len(chunks)} chunks -> {config.INDEX_FILE}")
