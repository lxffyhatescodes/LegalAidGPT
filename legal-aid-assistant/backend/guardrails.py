"""Input and output safety checks used by assistant/pipeline.py.

Input checks run BEFORE retrieval/LLM; output checks run AFTER the LLM answers.
All checks are plain Python (no model needed), so they are fast and testable.
"""
import re
from dataclasses import dataclass, field

from . import settings as config

# ---------------------------------------------------------------- input -----
_SENSITIVE = [
    ("an email address", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("a phone number", re.compile(r"(?<!\d)(\+?234|0)[789][01]\d[\s-]?\d{3}[\s-]?\d{4}(?!\d)")),
    ("an 11-digit ID number (NIN/BVN)", re.compile(r"(?<!\d)\d{11}(?!\d)")),
    ("a card or account number", re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")),
    ("a password or PIN", re.compile(r"\b(password|passcode|pin)\s*(is|:|=)\s*\S+", re.I)),
]
_INJECTION = re.compile(
    r"(ignore|disregard|forget)\s+(all\s+|any\s+)?(the\s+)?(previous|above|prior|earlier)\s+(instructions|rules|prompt)"
    r"|(reveal|show|print|repeat)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions)"
    r"|\bjailbreak\b|\bdeveloper mode\b|pretend (you are|to be) (not|no longer)",
    re.I,
)
_HARMFUL = re.compile(
    r"(how (do|can|to)|help me)\b.{0,40}\b(forge|fake|falsify|bribe|launder|evade (arrest|police)|"
    r"hide (a )?(body|evidence)|intimidate (a )?witness|get away with)",
    re.I,
)

MSG_EMPTY = "Please type your legal question first."
MSG_SENSITIVE = (
    "For your privacy, please do not share personal details such as {what}. "
    "Remove it and describe your situation in general terms. For advice on your "
    "specific case, please consult a qualified lawyer or the Legal Aid Council."
)
MSG_INJECTION = "I can only answer legal questions using the available legal documents."
MSG_HARMFUL = (
    "I can't help with that. I can explain your rights and lawful options instead, "
    "or you can speak to a qualified lawyer or the Legal Aid Council."
)


@dataclass
class InputResult:
    ok: bool
    question: str = ""
    message: str = ""        # shown to the user when ok is False
    warnings: list = field(default_factory=list)


def check_input(raw: str | None) -> InputResult:
    q = re.sub(r"\s+", " ", (raw or "")).strip()
    if not q:
        return InputResult(False, message=MSG_EMPTY)
    warnings = []
    if len(q) > config.MAX_QUESTION_CHARS:
        q = q[: config.MAX_QUESTION_CHARS]
        warnings.append(f"Your question was long, so only the first {config.MAX_QUESTION_CHARS} characters were used.")
    if _INJECTION.search(q):
        return InputResult(False, q, MSG_INJECTION)
    if _HARMFUL.search(q):
        return InputResult(False, q, MSG_HARMFUL)
    for what, pat in _SENSITIVE:
        if pat.search(q):
            return InputResult(False, q, MSG_SENSITIVE.format(what=what))
    return InputResult(True, q, warnings=warnings)


# --------------------------------------------------------------- output -----
_BRACKET = re.compile(r"\[([^\[\]]{3,200})\]")
_FACT = re.compile(r"\b(\d+)\s*(hours?|days?|weeks?|months?|years?|naira|percent|%)", re.I)
_NUMBER_WORDS = {"twenty-four": "24", "forty-eight": "48", "seven": "7", "fourteen": "14",
                 "thirty": "30", "ninety": "90"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())


_SEC_LIST = re.compile(
    r"\s*[,(:-]?\s*(?:sections?|s\.|ss\.|article)\s*"
    r"(\d+[A-Za-z]?(?:\s*(?:,\s*and|,|and|&)\s*(?:sections?\s*)?\d+[A-Za-z]?)*)", re.I)


def _sec_ok(sec: str, text: str) -> bool:
    return bool(re.search(rf"(?<![0-9a-z]){re.escape(sec.lower())}(?![0-9a-z])", text))


def _cited_hits(answer: str, hits: list[dict]):
    """Return (set of hit indexes the answer cites, list of citations that match nothing).

    Understands two styles the small local model uses:
      [Police Act 2020, section 42]            (bracketed, as the prompt asks)
      Police Act 2020, section 42 (and 30)     (plain sentence)
    """
    used, bad = set(), []

    # 1) bracketed citations
    for m in _BRACKET.finditer(answer):
        text = m.group(1)
        low = _norm(text)
        if "legal information" in low or "not legal advice" in low:
            continue
        matched = False
        for i, h in enumerate(hits):
            src = _norm(h["metadata"]["source"]).strip()
            sec = str(h["metadata"]["section"])
            if src and (src in low or low.strip() in src or src[:25] in low) and _sec_ok(sec, low):
                used.add(i)
                matched = True
        if not matched:
            bad.append(text)

    # 2) plain-sentence citations: "<document title>, section N [, and section M]"
    titles = {}
    for i, h in enumerate(hits):
        titles.setdefault(h["metadata"]["source"], []).append(i)
    ans_low = answer.lower()
    for title, idxs in titles.items():
        t = title.lower()
        pos = 0
        while (at := ans_low.find(t, pos)) != -1:
            pos = at + len(t)
            if answer[max(0, at - 1):at] == "[":      # bracketed form already handled above
                continue
            m = _SEC_LIST.match(answer[pos:pos + 80])
            if not m:
                continue
            for sec in re.findall(r"\d+[A-Za-z]?", m.group(1)):
                hit_i = [i for i in idxs if str(hits[i]["metadata"]["section"]).lower() == sec.lower()]
                if hit_i:
                    used.update(hit_i)
                else:
                    bad.append(f"{title}, section {sec}")
    # 3) reversed order: "section 35 of the <document title>"
    for title, idxs in titles.items():
        pat = re.compile(rf"sections?\s+(\d+[A-Za-z]?)\s+of\s+(?:the\s+)?{re.escape(title)}", re.I)
        for m in pat.finditer(answer):
            sec = m.group(1)
            hit_i = [i for i in idxs if str(hits[i]["metadata"]["section"]).lower() == sec.lower()]
            if hit_i:
                used.update(hit_i)
            else:
                bad.append(f"{title}, section {sec}")
    return used, list(dict.fromkeys(bad))


@dataclass
class OutputResult:
    used: list = field(default_factory=list)       # indexes of hits actually cited
    warnings: list = field(default_factory=list)
    grounded: bool = False


def check_output(answer: str, hits: list[dict]) -> OutputResult:
    res = OutputResult()
    used, bad = _cited_hits(answer, hits)
    res.used = sorted(used)
    if bad:
        res.warnings.append(
            "Some citations in this answer could not be matched to the retrieved documents "
            "and should not be relied on: " + "; ".join(bad[:3]))
    if not used:
        res.warnings.append("This answer did not cite a specific section. Check the sources below.")

    # numbers/time limits must come from the retrieved text (system prompt rule 4)
    context = _norm(" ".join(h["text"] for h in hits))
    ctx_nums = set(re.findall(r"\d+", context)) | {v for k, v in _NUMBER_WORDS.items() if k in context}
    unsupported = [m.group(0) for m in _FACT.finditer(answer) if m.group(1) not in ctx_nums]
    if unsupported:
        res.warnings.append(
            "This answer mentions figures (" + ", ".join(sorted(set(unsupported))[:3]) +
            ") that were not found in the retrieved sources. Please verify them with a lawyer.")

    res.grounded = bool(used) and not bad and not unsupported
    return res
