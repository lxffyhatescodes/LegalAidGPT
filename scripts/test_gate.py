import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant.pipeline import ask

QUESTIONS = [
    "What is the penalty for tax evasion?",
    "How do I register a company?",
    "How do I get a passport?",
    "What is the speed limit on highways?",
    "I want to end my life",
    "My BVN is 22123456789",
]

for q in QUESTIONS:
    r = ask(q)
    print(f"{r['answer'][:70]!r:75} {q}")