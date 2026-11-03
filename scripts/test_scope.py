import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant.guidance_pipeline import prepare_question

QUESTIONS = [
    "What must police tell me when they arrest me?",
    "My boss has refused to pay my salary for three months. What should I do?",
    "My landlord wants to evict me. What are my rights?",
    "A shop sold me a faulty phone and refuses to refund me.",
    "What is the penalty for tax evasion?",
    "How do I register a company?",
    "How do I get a passport?",
    "What is the speed limit on highways?",
]

for q in QUESTIONS:
    p = prepare_question(q)
    print(f"{p.get('status', 'allowed'):13} {str(p.get('problem_areas', '')):32} {q}")