"""2.4 Guardrails.

Two moments:
  BEFORE the model:  check_question()   - is this question safe to answer?
                     check_scope()      - is it a legal question we support?
                     check_retrieval_sufficiency() - did we find enough material?
  AFTER the model:   check_response_guardrails() - is the answer's tone safe?

All rules are plain keyword/regex rules that run locally. They are a first line
of defence: add cases here when the evaluation (4.3) finds failures.
"""
import re

try:
    from assistant import config
    MIN_SIMILARITY = config.MIN_SIMILARITY
    DISCLAIMER = config.DISCLAIMER
except ImportError:                       # lets this file be tested on its own
    MIN_SIMILARITY = 0.30
    DISCLAIMER = "This is general legal information, not legal advice."

# ---------------------------------------------------------------------------
# Messages shown to the user
# ---------------------------------------------------------------------------
NO_SOURCE_MESSAGE = ("I could not find this in the available legal documents. "
                     "Please consult a qualified lawyer or the Legal Aid Council.")
OUT_OF_SCOPE_MESSAGE = "I can only help with legal questions."
PERSONAL_DATA_MESSAGE = ("For your privacy, please don't include personal identifiers such as "
                         "phone numbers, BVN or NIN, bank or card numbers, or email addresses. "
                         "Ask your question again without them, or consult a qualified lawyer.")
INJECTION_MESSAGE = "I can only give information based on the legal documents available to me."
SELF_HARM_MESSAGE = ("I'm really sorry you're going through this, and you don't have to face it "
                     "alone. If you are in immediate danger, please contact the emergency "
                     "services (112) or reach out to someone you trust right now. I'm a legal "
                     "information tool and can't help with this, but once you are safe I'm glad "
                     "to help with legal questions.")
UNSAFE_ANSWER_MESSAGE = ("I couldn't produce a safe answer to this. Please consult a qualified "
                         "lawyer or the Legal Aid Council.")

# NOTE: confirm the emergency number wording before release (national 112 rollout is ongoing).
URGENT_NOTICES = [
    (r"\b(?:kill me|threatened to kill|beat(?:ing|en)? me|beats me|domestic violence|abus(?:e|ed|ing|ive)|"
     r"rap(?:e|ed|ing)|sexual(?:ly)? assault(?:ed)?|kidnap(?:ped|ping)?|in danger|not safe)\b",
     "If you or someone else is in immediate danger, contact the emergency services (112) now."),
    (r"\b(?:arrest(?:ed|ing)?|detain(?:ed|ing)?|(?:police|in) custody|locked up|remand(?:ed)?|charged with)\b",
     "If you or someone you know is in custody now, contact a lawyer or the Legal Aid Council as soon as possible."),
    (r"\b(?:quit notice|evict(?:ed|ion|ing)?|summons|court date|served with)\b",
     "Legal notices and court papers often have deadlines. Check the dates on them and speak to a lawyer promptly."),
]

# ---------------------------------------------------------------------------
# BEFORE the model: the question
# ---------------------------------------------------------------------------
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\d)(?:\+?234|0)[789][01]\d{8}(?!\d)")
_LONG_NUMBERS = {                       # kind of data -> pattern (applied after removing spaces/hyphens between digits)
    "identity number (BVN/NIN)": re.compile(r"(?<!\d)\d{11}(?!\d)"),
    "bank account number": re.compile(r"(?<!\d)\d{10}(?!\d)"),
}
_CARD = re.compile(r"(?<!\d)\d{13,19}(?!\d)")
_SELF_HARM = re.compile(
    r"\b(?:kill myself|end my life|suicid(?:e|al)|want to die|hurt myself|self[- ]harm)\b", re.I)
_INJECTION = [re.compile(p, re.I) for p in (
    r"\b(?:ignore|disregard|forget)\b.{0,30}\b(?:instructions|rules|prompt|guidelines)\b",
    r"\b(?:reveal|show|print|repeat)\b.{0,30}\b(?:system prompt|your instructions|your rules)\b",
    r"\byou are now\b", r"\bpretend (?:you are|to be)\b", r"\bdeveloper mode\b", r"\bjailbreak\b",
    r"\b(?:invent|make up|fabricate)\b.{0,15}\b(?:law|section|case|citation)s?\b",
)]


def _luhn_ok(number):
    total, double = 0, False
    for ch in reversed(number):
        d = int(ch)
        if double:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
        double = not double
    return total % 10 == 0


def find_personal_data(text):
    """Kinds of personal data found in the text (empty list = none)."""
    found = []
    if _EMAIL.search(text):
        found.append("email address")
    digits = re.sub(r"(?<=\d)[ \-](?=\d)", "", text)
    is_phone = bool(_PHONE.search(digits))
    if is_phone:
        found.append("phone number")
    if any(_luhn_ok(m.group()) for m in _CARD.finditer(digits)):
        found.append("card number")
    for kind, pattern in _LONG_NUMBERS.items():
        if pattern.search(digits) and not (is_phone and kind.startswith("identity")):
            found.append(kind)
    return found


def check_question(question):
    """Returns {"action": "ok" | "refuse" | "redirect", "message", "notices", "reason"}.
    'notices' are urgent warnings to show above the answer."""
    q = (question or "").strip()

    def result(action, message="", reason="", notices=()):
        return {"action": action, "message": message, "reason": reason, "notices": list(notices)}

    if not q:
        return result("refuse", "Please type a legal question.", "empty")
    if _SELF_HARM.search(q):
        return result("redirect", SELF_HARM_MESSAGE, "self_harm")
    personal = find_personal_data(q)
    if personal:
        return result("refuse", PERSONAL_DATA_MESSAGE, "personal_data: " + ", ".join(personal))
    if any(p.search(q) for p in _INJECTION):
        return result("refuse", INJECTION_MESSAGE, "prompt_injection")
    notices = [text for pattern, text in URGENT_NOTICES if re.search(pattern, q, re.I)]
    return result("ok", notices=notices)


def redact_personal_data(text):
    """Masks emails and long digit strings. Use before saving or logging a question."""
    text = _EMAIL.sub("[removed]", text)
    return re.sub(r"(?<!\d)\d(?:[ \-]?\d){9,18}(?!\d)", "[removed]", text)


# ---------------------------------------------------------------------------
# BEFORE the model: scope and retrieval
# ---------------------------------------------------------------------------
def check_scope(classification):

    scenarios = set(classification.get("scenarios", []))

    if not scenarios or "out_of_scope" in scenarios:

        return {
            "allowed": False,
            "reason": "Question is outside supported scope."
        }

    return {
        "allowed": True,
        "reason": "Passed scenario scope check."
    }


def chunk_similarity(chunk):
    """Similarity score of a chunk, or None if it has none.
    If only a cosine `distance` is given, similarity = 1 - distance.
    (Confirm with the retrieval owner which one they return.)"""
    for key in ("similarity", "score"):
        if chunk.get(key) is not None:
            return float(chunk[key])
    if chunk.get("distance") is not None:
        return 1.0 - float(chunk["distance"])
    return None


def filter_weak_chunks(retrieved_chunks, min_similarity=None):
    """Drops chunks that match the question too weakly. Chunks without a score are kept."""
    limit = MIN_SIMILARITY if min_similarity is None else min_similarity
    kept = []
    for chunk in retrieved_chunks or []:
        score = chunk_similarity(chunk)
        if score is None or score >= limit:
            kept.append(chunk)
    return kept


def check_retrieval_sufficiency(retrieved_chunks):

    if not filter_weak_chunks(retrieved_chunks):

        return {
            "allowed": False,
            "reason": "No supporting legal material was retrieved."
        }

    return {
        "allowed": True,
        "reason": "Retrieved material is available."
    }


# ---------------------------------------------------------------------------
# AFTER the model: the answer
# ---------------------------------------------------------------------------
RISKY_PHRASES = [
    "i guarantee you will win",
    "you are guaranteed to win",
    "you will win",
    "you cannot lose",
    "you do not need a lawyer",
    "this definitely proves your case",
    "as your lawyer",
    "i am your lawyer",
]


def is_no_source_answer(answer):
    return (answer or "").strip().lower().startswith(
        ("i could not find", "i couldn't find", "i cannot find", "i can't find"))


def check_response_guardrails(answer):

    text = (answer or "").strip()

    warnings = []

    if not text:
        warnings.append("empty_response")

    for phrase in RISKY_PHRASES:

        if phrase in text.lower():

            warnings.append("overconfident_legal_claim")

            break

    if text and not any(
        phrase in text.lower()
        for phrase in ["general legal information", "not legal advice"]
    ):

        warnings.append("legal_information_notice_missing")

    return {
        "passed": bool(text) and "overconfident_legal_claim" not in warnings,
        "warnings": warnings
    }


def add_legal_notice(answer):
    """Adds the 'not legal advice' line if the model forgot it."""
    low = answer.lower()
    if "general legal information" in low or "not legal advice" in low:
        return answer
    return answer.rstrip() + "\n\n" + DISCLAIMER


def run_guardrails(classification, retrieved_chunks, answer):

    scope = check_scope(classification)

    retrieval = check_retrieval_sufficiency(retrieved_chunks)

    response = check_response_guardrails(answer)

    return {
        "allowed_to_answer": (
            scope["allowed"] and retrieval["allowed"]
        ),

        "scope": scope,
        "retrieval": retrieval,
        "response": response
    }
