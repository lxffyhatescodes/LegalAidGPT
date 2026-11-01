"""Backend settings. Values owned by other groups are imported READ-ONLY from assistant/config.py."""
from pathlib import Path

from assistant import config as base      # not modified, only read

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"
CHUNKS_FILE = DATA_DIR / "chunks.jsonl"
INDEX_DIR = DATA_DIR / "index"
INDEX_FILE = INDEX_DIR / "faiss.index"
INDEX_IDS_FILE = INDEX_DIR / "chunk_ids.json"

# from the other groups' config
CLEAN_DIR = base.CLEAN_DIR
SOURCE_REGISTER = base.SOURCE_REGISTER
EMBEDDING_MODEL = base.EMBEDDING_MODEL
TOP_K = 5                    # backend value (Group 2 config says 4): chunks are smaller now, so 5 still fits the prompt
MIN_SIMILARITY = base.MIN_SIMILARITY
OLLAMA_MODEL = base.OLLAMA_MODEL
DISCLAIMER = base.DISCLAIMER

# backend-only
FALLBACK_MIN_SCORE = 0.12    # keyword (TF-IDF) fallback threshold when no embedding index exists
RETRIEVAL_BACKEND = "auto"   # "auto" | "dense" | "keyword"
MAX_QUESTION_CHARS = 1500
EXCERPT_CHARS = 450
