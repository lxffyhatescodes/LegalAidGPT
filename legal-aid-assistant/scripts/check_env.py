"""Run: python scripts/check_env.py
Checks that the project environment is ready. Safe to run repeatedly."""
import importlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ok = True

def report(label, passed, hint=""):
    global ok
    ok = ok and passed
    print(f"[{'OK' if passed else 'FAIL'}] {label}" + (f"  -> {hint}" if not passed and hint else ""))

# Python version
v = sys.version_info
report(f"Python {v.major}.{v.minor}.{v.micro}", (3, 10) <= (v.major, v.minor) <= (3, 12),
       "3.10 to 3.12 is the safest range for the ML packages")

# Packages
for mod, pip_name in [("fitz", "pymupdf"), ("docx", "python-docx"), ("bs4", "beautifulsoup4"),
                      ("sentence_transformers", "sentence-transformers"), ("faiss", "faiss-cpu"),
                      ("numpy", "numpy"), ("pandas", "pandas"), ("pytest", "pytest"), ("streamlit", "streamlit")]:
    try:
        importlib.import_module(mod)
        report(f"package {pip_name}", True)
    except Exception:
        report(f"package {pip_name}", False, f"pip install {pip_name}")

# Project folders
for d in ["data/raw", "data/clean", "data/index", "models", "assistant", "ingest", "retrieval", "ui", "tests"]:
    report(f"folder {d}/", (ROOT / d).is_dir(), "create it or re-extract the starter")

# Config + local LLM
try:
    from assistant import config
    report("assistant/config.py loads", True)
except Exception as e:
    report("assistant/config.py loads", False, str(e))
    config = None

if config:
    if config.LLM_BACKEND == "ollama":
        report("ollama installed", importlib.util.find_spec("ollama") is not None,
               "pip install ollama")
        report(f"model file at {config.LLM_MODEL_PATH.relative_to(ROOT)}", config.LLM_MODEL_PATH.exists(),
               "download a .gguf model and save it as models/model.gguf")
    elif config.LLM_BACKEND == "ollama":
        report("ollama python client installed", importlib.util.find_spec("ollama") is not None,
               "install Ollama from ollama.com, then pip install ollama, then: ollama pull " + config.OLLAMA_MODEL)
    else:
        report("LLM_BACKEND is valid", False, 'use "llama_cpp" or "ollama"')

    # Embedding model (needs internet ONCE to download; offline afterwards)
    try:
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(config.EMBEDDING_MODEL)
        dim = len(m.encode("test"))
        report(f"embedding model loads (dim {dim})", True)
    except Exception as e:
        report("embedding model loads", False,
               "first run needs internet to download it once; afterwards it works offline. " + str(e)[:80])

print("\nAll checks passed." if ok else "\nFix the FAIL lines above, then run this again.")
