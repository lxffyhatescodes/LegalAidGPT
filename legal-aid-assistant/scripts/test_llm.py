import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant.llm import answer

hits = [{
    "text": "Any person who is arrested or detained shall be brought before a court of law within a reasonable time...",
    "metadata": {"source": "Constitution of Nigeria 1999", "section": "35"},
    "distance": 0.2,
}]

print(answer("I was arrested yesterday. How long can police hold me?", hits))
print("---")
print(answer("What is the penalty for tax evasion?", hits))  # should decline
print("---")
print(answer("What is the penalty for tax evasion?", []))    # no sources at all
