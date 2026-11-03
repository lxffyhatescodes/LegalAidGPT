"""Backend entry point (Group 3, role: backend and integration).

The UI only ever calls ask() or explain_document(). Everything else here is
swappable. With config.USE_MOCK = True it runs on placeholder data so the
frontend can be built and demoed before the other groups deliver.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from . import config


# ----------------------------------------------------------------------------
# Data contract (matches section 6 of the architecture guide)
# ----------------------------------------------------------------------------
@dataclass
class Answer:
    answer: str
    citations: list = field(default_factory=list)  # {chunk_id, doc_title, section, excerpt}
    grounded: bool = True
    warnings: list = field(default_factory=list)
    disclaimer: str = config.DISCLAIMER
    urgent: bool = False  # extra flag: emergency guidance shown first


# ----------------------------------------------------------------------------
# Mock knowledge base. PLACEHOLDER TEXT ONLY, replaced by Group 1's real chunks.
# ----------------------------------------------------------------------------
MOCK_CHUNKS = [
    {
        "chunk_id": "mock_constitution_s35",
        "doc_title": "Constitution (mock)",
        "section": "Section 35",
        "heading": "Right to personal liberty",
        "topics": ["arrest-and-detention", "fundamental-rights"],
        "keywords": "arrest arrested detain detained police custody bail court liberty cell station",
        "text": "[Mock excerpt] A person who is arrested should be told the reasons for the arrest, "
                "in a language they understand, and should be brought before a court within a reasonable time.",
        "steps": [
            "Stay calm and ask what the reason for the arrest is.",
            "Ask to contact a lawyer or a family member.",
            "Do not sign any statement you do not understand.",
        ],
    },
    {
        "chunk_id": "mock_constitution_s34",
        "doc_title": "Constitution (mock)",
        "section": "Section 34",
        "heading": "Respect for dignity of the person",
        "topics": ["arrest-and-detention", "fundamental-rights"],
        "keywords": "torture dignity beaten beating violence abuse inhuman degrading treatment police",
        "text": "[Mock excerpt] Every person has a right to respect for the dignity of their person, "
                "and no one should be subjected to torture or inhuman or degrading treatment.",
        "steps": [
            "Note the date, place and names or badge numbers if you can.",
            "Seek medical care and keep any records.",
            "Report to a lawyer, a legal aid office or a human rights body.",
        ],
    },
    {
        "chunk_id": "mock_constitution_s36",
        "doc_title": "Constitution (mock)",
        "section": "Section 36",
        "heading": "Right to fair hearing",
        "topics": ["fundamental-rights", "arrest-and-detention"],
        "keywords": "fair hearing trial court accused innocent charge charged lawyer defence rights",
        "text": "[Mock excerpt] A person charged with a crime is presumed innocent until proven guilty "
                "and has the right to a fair hearing and to defend themselves.",
        "steps": [
            "Ask the court or police what the exact charge is.",
            "Get legal representation as early as you can.",
        ],
    },
    {
        "chunk_id": "mock_tenancy_001",
        "doc_title": "Tenancy guide (mock)",
        "section": "Part 2",
        "heading": "Notice before recovering premises",
        "topics": ["tenancy-housing"],
        "keywords": "landlord tenant tenancy rent evict eviction quit notice house flat apartment premises lease",
        "text": "[Mock excerpt] A landlord must usually give written notice before recovering premises, "
                "and must follow the court process rather than removing a tenant by force.",
        "steps": [
            "Ask for the notice in writing and keep a copy.",
            "Keep proof of rent payments (receipts, transfers).",
            "Do not hand over keys or move out before getting advice.",
        ],
    },
    {
        "chunk_id": "mock_employment_001",
        "doc_title": "Labour guide (mock)",
        "section": "Part 4",
        "heading": "Ending a contract of employment",
        "topics": ["employment"],
        "keywords": "employer employee job work fired sacked dismissed termination salary wages contract notice resign",
        "text": "[Mock excerpt] An employer should give notice, or pay in place of notice, when ending a "
                "contract, and should pay wages already earned.",
        "steps": [
            "Ask for the termination in writing.",
            "Keep your contract, payslips and messages.",
            "Calculate any unpaid wages and notice pay.",
        ],
    },
    {
        "chunk_id": "mock_consumer_001",
        "doc_title": "Consumer guide (mock)",
        "section": "Part 1",
        "heading": "Faulty goods and refunds",
        "topics": ["consumer"],
        "keywords": "consumer buy bought shop seller product goods faulty defective refund receipt warranty fake scam",
        "text": "[Mock excerpt] Goods sold should be of reasonable quality and match their description. "
                "A buyer may ask for a repair, replacement or refund for faulty goods.",
        "steps": [
            "Keep your receipt or proof of payment.",
            "Return to the seller quickly and explain the fault.",
            "Complain to the relevant consumer protection body if refused.",
        ],
    },
]

_STOPWORDS = set(
    "a an the is are was were be been am i me my we our you your it its of to in on at for "
    "and or but with from by as that this these those can do does did not no what how when "
    "where who why which will would should could may might have has had if then so out up".split()
)

URGENT_WORDS = ["arrested", "detained", "beaten", "beating", "violence", "threatened",
                "evict tomorrow", "out tomorrow", "tonight", "police station", "in custody"]
HARMFUL_PHRASES = ["evade the law", "avoid the police", "hide evidence", "destroy evidence",
                   "bribe", "forge", "fake document", "get away with"]
INJECTION_PHRASES = ["ignore previous instructions", "ignore all instructions",
                     "ignore your instructions", "reveal your system prompt", "you are now"]

URGENT_TEXT = (
    "If you or someone else is in immediate danger, contact the emergency services now. "
    "If you have been arrested or detained, ask to contact a lawyer or a legal aid office as soon as you can."
)


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _tokens(text: str) -> set:
    words = re.findall(r"[a-z]+", text.lower())
    return {_stem(w) for w in words if w not in _STOPWORDS and len(w) > 2}


# ----------------------------------------------------------------------------
# Pipeline stages
# ----------------------------------------------------------------------------
def _input_guardrails(question: str):
    """Returns (ok, reason). Group 2 will provide the real version."""
    q = question.lower()
    if any(p in q for p in INJECTION_PHRASES):
        return False, "I can't follow instructions that try to change how I work."
    if any(p in q for p in HARMFUL_PHRASES):
        return False, ("I can't help with avoiding the law or harming others. "
                       "I can explain your rights or what the law says if you tell me more about the situation.")
    return True, ""


def _rewrite_query(question: str, history: list) -> str:
    """Make short follow-ups standalone by borrowing the last user question."""
    if history and len(question.split()) < 5:
        prev = [m["content"] for m in history if m.get("role") == "user"]
        if prev:
            return f"{prev[-1]} {question}"
    return question


def _mock_retrieve(query: str, k: int, filters: dict | None) -> list:
    q = _tokens(query)
    if not q:
        return []
    results = []
    for ch in MOCK_CHUNKS:
        if filters and filters.get("topic") and filters["topic"] not in ch["topics"]:
            continue
        hits = q & (_tokens(ch["keywords"]) | _tokens(ch["heading"]))
        if hits:
            results.append({**ch, "score": len(hits) / len(q)})
    results.sort(key=lambda c: c["score"], reverse=True)
    return [c for c in results if c["score"] >= config.MIN_SIMILARITY][:k]


def _retrieve(query: str, k: int, filters: dict | None) -> list:
    if config.USE_MOCK:
        return _mock_retrieve(query, k, filters)
    from retrieval.retrieve import retrieve  # Group 1: retrieve(query, k, filters) -> list[chunk dict]
    return retrieve(query, k, filters)


def _basic_prompt(question: str, chunks: list) -> str:
    """Fallback prompt. Replace with Group 2's assistant/prompts.py when ready."""
    passages = "\n\n".join(
        f"[{i}] {c['doc_title']}, {c['section']}: {c['text']}" for i, c in enumerate(chunks, 1)
    )
    return (
        "You are a legal information assistant. Answer ONLY from the passages below. "
        "Cite every claim like [1]. If the passages do not cover the question, say so. "
        "Use plain language. Do not give guarantees.\n\n"
        f"PASSAGES:\n{passages}\n\nQUESTION: {question}\n\nANSWER:"
    )


def _generate(prompt: str) -> str:
    """Call the local model through Ollama (no external API)."""
    import urllib.request

    payload = json.dumps({"model": config.LLM_MODEL, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{config.OLLAMA_URL}/api/generate", data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=config.REQUEST_TIMEOUT_S) as resp:
        return json.loads(resp.read())["response"].strip()


def _mock_answer(chunks: list) -> str:
    lead = chunks[0]
    law_lines = "\n".join(f"- {c['heading']} ({c['section']}) [{i}]" for i, c in enumerate(chunks, 1))
    steps = []
    for c in chunks[:2]:
        for s in c["steps"]:
            if s not in steps:
                steps.append(s)
    step_lines = "\n".join(f"- {s}" for s in steps)
    return (
        f"**In short:** your question is covered by *{lead['heading'].lower()}* ({lead['section']}) [1].\n\n"
        f"**What the law says**\n{law_lines}\n\n"
        f"**What you can do**\n{step_lines}\n\n"
        "**Where to get help**\nA qualified lawyer, or a legal aid office such as the Legal Aid Council of Nigeria."
    )


def _log(**event) -> None:
    """Analytics log. Stores counts and timings only, never the question text."""
    try:
        config.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        event["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with open(config.LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except OSError:
        pass  # logging must never break the app


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

def _search_areas(question, problem_areas, top_k):
    """Search each area separately so the Constitution gets its own slot; total hits = top_k."""
    from retrieval import search
    areas = problem_areas or [None]
    base, extra = divmod(top_k, len(areas))
    hits, seen = [], set()
    for i, area in enumerate(areas):
        k = max(1, base + (1 if i < extra else 0))
        for h in search(question, case_area=area, k=k):
            key = (h["metadata"]["doc_id"], h["text"][:80])
            if key not in seen:
                seen.add(key)
                hits.append(h)
    # Constitution first (supreme law), then by similarity
    hits.sort(key=lambda h: (h["metadata"]["doc_id"] != "constitution_1999", h["distance"]))
    return hits

SUPPORTED_HELP_WORDS = ("lawyer", "legal aid", "legal help", "legal advice", "my rights",
                        "constitution", "section ", "court")

UNSUPPORTED_TOPIC_MESSAGE = (
    "I couldn't match your question to the topics covered by the available legal documents: "
    "arrest and police, tenants and housing, employment, consumer protection and loans, land, "
    "and marriage and family. Please rephrase your question, or consult a lawyer or the "
    "Legal Aid Council."
)

def ask(question: str, history: list | None = None, filters: dict | None = None) -> dict:
    """Entry point for the UI. Returns the Answer fields as a dict."""
    from assistant.guidance_pipeline import answer_question, prepare_question

    topic = (filters or {}).get("topic")      # from the sidebar topic picker

    # Extra scope gate: the question passed the safety checks but matches none of the
    # supported topics, so the documents can't answer it. Don't search at all.
    prep = prepare_question(question, history)
    if (prep["allowed"] and not prep["classification"]["topics"]
            and not any(w in question.lower() for w in SUPPORTED_HELP_WORDS)):
        _log(topic=topic or "all", retrieval_ms=0, generation_ms=0, grounded=False, refused=False)
        return asdict(Answer(answer=UNSUPPORTED_TOPIC_MESSAGE, grounded=False))

    spent = {"retrieval": 0.0}
    # ... the rest of the function stays exactly as it was

    def retrieve(q, areas, top_k):
        if topic and areas:                   # areas == [] is the "try everything" fallback
            areas = [topic, "all_areas"]
        t0 = time.perf_counter()
        try:
            return _search_areas(q, areas, top_k)
        finally:
            spent["retrieval"] += time.perf_counter() - t0

    t0 = time.perf_counter()
    r = answer_question(question, history, retrieve_fn=retrieve)
    total_ms = int((time.perf_counter() - t0) * 1000)
    retrieval_ms = int(spent["retrieval"] * 1000)

    status = r["status"]
    out = Answer(
        answer=r["answer"],
        citations=r["ui_citations"],
        grounded=(status == "ok"),
        warnings=r["warnings"],
        urgent=any("emergency services" in w.lower() for w in r["warnings"]),
    )
    _log(topic=topic or "all", retrieval_ms=retrieval_ms,
         generation_ms=max(total_ms - retrieval_ms, 0),
         grounded=out.grounded, refused=status in ("refused", "redirected"))
    return asdict(out)

def explain_document(text: str) -> dict:
    """Explain an uploaded document in plain language."""
    text = text.strip()
    if not text:
        return asdict(Answer(answer="There is no text to explain.", grounded=False))
    if config.USE_MOCK:
        sentences = re.split(r"(?<=[.!?])\s+", text)[:3]
        body = "\n".join(f"- {s}" for s in sentences)
        return asdict(Answer(
            answer=f"**What this document says (plain language)**\n{body}\n\n"
                   "**Things to check**\n- Dates and deadlines\n- Amounts you must pay or receive\n"
                   "- Anything you are asked to sign",
            grounded=False,
            warnings=["Demo mode: this is a placeholder summary, not a real explanation."]))
    prompt = ("Explain the following legal document in simple language for a non-expert. "
              "List key points, deadlines, amounts and obligations. Do not give legal advice.\n\n"
              f"DOCUMENT:\n{text[:6000]}\n\nEXPLANATION:")
    try:
        return asdict(Answer(answer=_generate(prompt), grounded=False))
    except Exception as exc:
        return asdict(Answer(answer="The local language model did not respond.",
                             grounded=False, warnings=[f"LLM error: {exc}"]))
