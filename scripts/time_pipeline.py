import sys
from pathlib import Path

import ollama

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant import config
from assistant.llm import _messages, _options
from assistant.pipeline import _search_areas

q = " ".join(sys.argv[1:]) or "my wife divorce me and wants to take two third of my wealth. What do i do"
hits = _search_areas(q, ["marriage", "all_areas"], config.TOP_K)
print("chunks:", len(hits), " characters:", sum(len(h["text"]) for h in hits))

r = ollama.chat(model=config.OLLAMA_MODEL, messages=_messages(q, hits), options=_options())
ns = 1e9
print(f"model load : {r['load_duration'] / ns:.1f} s")
print(f"read prompt: {r['prompt_eval_count']} tokens in {r['prompt_eval_duration'] / ns:.1f} s")
print(f"write reply: {r['eval_count']} tokens in {r['eval_duration'] / ns:.1f} s")
print(f"total      : {r['total_duration'] / ns:.1f} s")