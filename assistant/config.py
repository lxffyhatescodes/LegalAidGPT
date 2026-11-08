"""Central configuration. Everything runs locally; no API keys are needed."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- Data paths ---
RAW_DIR = ROOT / "data" / "raw"
CLEAN_DIR = ROOT / "data" / "clean"
CHUNKS_FILE = ROOT / "data" / "chunks.jsonl"
INDEX_DIR = ROOT / "data" / "index"
SOURCE_REGISTER = ROOT / "data" / "source_register.csv"

# --- Retrieval (P6) ---
EMBEDDING_MODEL = "nomic-embed-text"  # served by Ollama
TOP_K = 4                    # keep small so the prompt fits a local model's context
MIN_SIMILARITY = 0.62        # below this, answer "not covered by the sources"

# --- Local LLM (P7/P8) ---
LLM_BACKEND = "ollama"    # "llama_cpp" (in-process) or "ollama" (local server)
LLM_MODEL_PATH = ROOT / "models" / "model.gguf"   # used by llama_cpp
OLLAMA_MODEL = "llama3.2:3b"                      # used by ollama
LLM_CONTEXT_TOKENS = 4096
LLM_MAX_NEW_TOKENS = 350
LLM_TEMPERATURE = 0.0        # low = more faithful to the sources


DISCLAIMER = "This is general legal information, not legal advice."
 
SHOW_UNVERIFIED_ANSWERS = False
LOG_PATH = ROOT / "data" / "query_log.jsonl"

# Sidebar topic picker in the UI: label shown -> problem_area value in the register
TOPICS = {
    "All topics": None,
    "Arrest & police": "arrest",
    "Tenant rights": "tenant",
    "Land": "land",
    "Consumer & lending": "consumer",
    "Legal aid": "legal_assistance",
    "Marriage & family": "marriage",
    "Employment": "employment",
}
# Example questions shown as buttons on the start screen
SAMPLE_QUESTIONS = [
    "What must police tell me when they arrest me?",
    "My landlord wants to evict me. What are my rights?",
    "Can my employer dismiss me without notice?",
    "What are my rights as a borrower of a digital loan?",
]
USE_MOCK = False

OLLAMA_URL = "http://localhost:11434"
LLM_MODEL = OLLAMA_MODEL
REQUEST_TIMEOUT_S = 120