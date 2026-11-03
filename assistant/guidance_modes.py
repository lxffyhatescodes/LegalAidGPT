"""2.3 Scenario-based guidance modes.

Three jobs, in order:
  1. classify_question()        -> what KIND of question is this (definition, rights, procedure...)
                                   and which legal TOPIC (tenant, arrest...) is it about?
  2. select_guidance_modes()    -> pick the matching modes from GUIDANCE_MODES
  3. build_mode_instructions()  -> turn the chosen modes into text for the prompt

This runs BEFORE the model, so the instructions can actually shape the answer.
No legal facts live here. Facts always come from the retrieved sources.
"""
import re

# ---------------------------------------------------------------------------
# 1. The modes (what the assistant should do for each kind of question)
# ---------------------------------------------------------------------------
GUIDANCE_MODES = {

    "legal_definition": {
        "mode": "educational_explanation",
        "instructions": """
        Define the legal concept in simple language.
        Explain relevant terminology.
        Distinguish general information from specific legal advice.
        """
    },

    "constitutional_explanation": {
        "mode": "constitutional_explanation",
        "instructions": """
        Explain the relevant constitutional provision.
        Identify the applicable section.
        Base explanations on retrieved constitutional documents.
        """
    },

    "rights_related": {
        "mode": "rights_awareness",
        "instructions": """
        Identify potentially relevant fundamental rights.
        Explain available options using retrieved sources.
        Do not automatically conclude that a violation occurred.
        """
    },

    "legal_procedure": {
        "mode": "procedural_information",
        "instructions": """
        Explain relevant legal procedures.
        Identify applicable requirements.
        Highlight missing procedural information.
        """
    },

    "legal_application": {
        "mode": "situational_legal_information",
        "instructions": """
        Relate relevant legal provisions to the user's situation.
        Identify missing facts.
        Avoid unsupported legal conclusions.
        """
    },

    "out_of_scope": {
        "mode": "scope_limitation",
        "instructions": """
        Explain that the question is outside the assistant's
        supported knowledge base.
        Do not fabricate legal information.
        """
    }
}

MAX_MODES_IN_PROMPT = 3   # a small local model gets confused by too many instructions

# ---------------------------------------------------------------------------
# 2. Classifier: the question -> {"scenarios": [...], "topics": [...], "problem_areas": [...]}
#    Simple keyword rules. Add words here when the evaluation (4.3) shows a miss.
# ---------------------------------------------------------------------------
# A word ending in * matches any word starting with it ("evict*" -> evict, evicted, eviction).
# Other words must match as whole words (so "land" does NOT match "landlord").
TOPIC_KEYWORDS = {
    "arrest": ["arrest*", "detain*", "detention", "police", "custody", "bail", "remand*",
               "warrant", "handcuff*", "charged"],
    "tenant": ["landlord", "landlady", "tenant", "tenancy", "rent", "evict*", "lease",
               "deposit", "quit notice"],
    "land": ["land", "plot", "certificate of occupancy", "c of o", "trespass*", "omonile",
             "right of occupancy"],
    "consumer": ["loan", "lender", "borrow*", "bank", "refund", "warranty", "scam", "debt",
                 "consumer", "fccpc", "digital lending", "loan app", "overcharg*", "credit"],
    "marriage": ["marri*", "husband", "wife", "spouse", "divorce", "separat*", "child",
                 "children", "maintenance", "dowry", "annul*", "matrimonial", "widow"],
    "employment": ["employ*", "salary", "wage", "sack*", "fired", "dismiss*", "resign*",
                   "redundan*", "overtime", "pension", "severance", "labour", "workplace",
                   "worker", "annual leave", "unpaid", "gratuity", "boss"],
    "legal_aid": ["legal aid", "free lawyer", "pro bono", "afford a lawyer", "legal assistance"],
}

# topic -> values of the `problem_area` column in data/source_register.csv
# (the Constitution is labelled all_areas, so it is always included)
PROBLEM_AREAS = {
    "arrest": ["arrest", "all_areas"],
    "tenant": ["tenant", "all_areas"],
    "land": ["land", "all_areas"],
    "consumer": ["consumer", "all_areas"],
    "marriage": ["marriage", "all_areas"],
    "employment": ["employment", "all_areas"],
    "legal_aid": ["legal_assistance", "all_areas"],
}

GENERAL_LEGAL_WORDS = ["law", "legal", "court", "lawyer", "judge", "sue", "right", "rights",
                       "contract", "crime", "constitution", "act", "section"]

OFF_TOPIC_WORDS = ["recipe", "weather", "football", "soccer", "movie", "song lyrics",
                   "write code", "python code", "homework", "horoscope", "bitcoin price", "joke"]

# question patterns -> scenario names (keys of GUIDANCE_MODES)
SCENARIO_PATTERNS = [
    ("legal_definition", r"\b(?:what is|what are|define|meaning of|what does .{1,40} mean)\b"),
    ("constitutional_explanation", r"\b(?:constitution|constitutional|fundamental rights?|section \d+)"),
    ("rights_related", r"\b(?:rights?|entitled|unlawful|illegal|violat\w*)\b"),
    ("legal_procedure", r"\b(?:how do i|how can i|how to|how long|procedure|process|steps|apply for|file a|report)\b"),
    ("legal_application", r"\b(?:i|my|me|we|our)\b"),
]


def _has_word(text, keyword):
    if keyword.endswith("*"):
        return re.search(rf"\b{re.escape(keyword[:-1])}", text) is not None
    return re.search(rf"\b{re.escape(keyword)}(?:s|es|ed|ing)?\b", text) is not None


def detect_topics(text):
    """Which legal topics does the text mention? e.g. ['tenant']"""
    text = (text or "").lower()
    return [topic for topic, words in TOPIC_KEYWORDS.items()
            if any(_has_word(text, w) for w in words)]


def classify_question(question, history=None):
    """Returns {"scenarios": [...], "topics": [...], "problem_areas": [...]}."""
    q = (question or "").lower()
    topics = detect_topics(q)

    # A short follow-up ("what about my deposit?") may carry the topic from the last question.
    if not topics and history:
        earlier = [m.get("content", "") for m in history if m.get("role") == "user"]
        if earlier:
            topics = detect_topics(earlier[-1])

    has_legal_word = bool(topics) or any(_has_word(q, w) for w in GENERAL_LEGAL_WORDS)
    if any(w in q for w in OFF_TOPIC_WORDS) and not has_legal_word:
        return {"scenarios": ["out_of_scope"], "topics": [], "problem_areas": []}

    scenarios = [name for name, pattern in SCENARIO_PATTERNS if re.search(pattern, q)]
    if not scenarios and has_legal_word:
        scenarios = ["legal_application"]

    areas = []
    for t in topics:
        for a in PROBLEM_AREAS[t]:
            if a not in areas:
                areas.append(a)
    return {"scenarios": scenarios, "topics": topics, "problem_areas": areas}


# ---------------------------------------------------------------------------
# 3. Pick modes and build the prompt text
# ---------------------------------------------------------------------------
def select_guidance_modes(classification):

    scenarios = classification.get("scenarios", [])

    selected_modes = []

    for scenario in scenarios:

        if scenario in GUIDANCE_MODES:

            selected_modes.append({
                "scenario": scenario,
                **GUIDANCE_MODES[scenario]
            })

    if not selected_modes:

        selected_modes.append({
            "scenario": "out_of_scope",
            **GUIDANCE_MODES["out_of_scope"]
        })

    return selected_modes


def build_mode_instructions(selected_modes):
    """One block of text to add to the prompt, e.g.
    'Guidance for this question: - Define the legal concept...'"""
    lines = []
    for m in selected_modes[:MAX_MODES_IN_PROMPT]:
        if m["scenario"] == "out_of_scope":
            continue
        lines.append("- " + " ".join(m["instructions"].split()))
    if not lines:
        return ""
    return "Guidance for this question:\n" + "\n".join(lines)
