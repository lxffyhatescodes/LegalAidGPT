"""Central configuration. Everything runs locally; no API keys are needed."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- Data paths ---
DATA_DIR = ROOT.parent / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
CHUNKS_FILE = DATA_DIR / "chunks.jsonl"
INDEX_DIR = DATA_DIR / "index"
SOURCE_REGISTER = DATA_DIR / "source_register.csv"

# --- Retrieval (P6) ---
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # small, English; swap if needed
TOP_K = 4                    # keep small so the prompt fits a local model's context
MIN_SIMILARITY = 0.30        # below this, answer "not covered by the sources"

# --- Local LLM (P7/P8) ---
LLM_BACKEND = "ollama"    # "llama_cpp" (in-process) or "ollama" (local server)
LLM_MODEL_PATH = ROOT / "models" / "model.gguf"   # used by llama_cpp
OLLAMA_MODEL = "llama3.2:3b"                      # used by ollama
LLM_CONTEXT_TOKENS = 4096
LLM_MAX_NEW_TOKENS = 512
LLM_TEMPERATURE = 0.2        # low = more faithful to the sources

DISCLAIMER = "This is general legal information, not legal advice."
