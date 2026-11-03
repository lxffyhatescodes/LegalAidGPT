import sys
from pathlib import Path

import ollama

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant import config

for n in (2, 3, 4):
    r = ollama.chat(
        model=config.OLLAMA_MODEL,
        messages=[{"role": "user", "content": "Explain in plain words what a tenant is."}],
        options={"num_thread": n, "num_predict": 60, "num_ctx": 2048},
        keep_alive="30m",
    )
    speed = r["eval_count"] / (r["eval_duration"] / 1e9)
    print(f"num_thread={n}: {speed:.1f} tokens/sec")