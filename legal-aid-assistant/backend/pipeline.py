"""P8: backend. `ask()` is the single entry point the UI calls.

    guardrails(input) -> retrieve -> prompt+LLM -> guardrails(output) -> Answer

Contract (never changes, even on errors): ask() always returns an `Answer`.
Nothing is written to disk and user questions are never logged (privacy).
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field

from . import guardrails
from . import settings as config

log = logging.getLogger("legal_aid")
LLM_TIMEOUT_SECONDS = 180   # first call can be slow while Ollama loads the model
_pool = ThreadPoolExecutor(max_workers=1)

NO_SOURCE = (
    "I could not find this in the available legal documents. "
    "Please consult a qualified lawyer or the Legal Aid Council."
)


@dataclass
class Answer:
    answer: str
    citations: list = field(default_factory=list)   # [{"chunk_id", "doc_title", "section", "excerpt"}]
    grounded: bool = False
    warnings: list = field(default_factory=list)
    disclaimer: str = config.DISCLAIMER
    latency_s: float = 0.0       # for the analytics dashboard (3.4)
    status: str = "ok"           # ok | no_source | blocked | error  (for evaluation + UI styling)


def _excerpt(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= config.EXCERPT_CHARS else text[: config.EXCERPT_CHARS].rsplit(" ", 1)[0] + " ..."


def _citation(h: dict) -> dict:
    m = h["metadata"]
    return {"chunk_id": m.get("chunk_id", ""), "doc_title": m.get("source", ""),
            "section": m.get("section", ""), "excerpt": _excerpt(h["text"])}


def _retrieval_query(question: str, history: list | None) -> str:
    """Short follow-ups ("and what about bail?") are searched together with the previous question."""
    if history and len(question.split()) < 8:
        prev = [m["content"] for m in history if m.get("role") == "user"]
        if prev:
            return f"{prev[-1]} {question}"
    return question


STRONG_MATCH = 0.55


def _strong_match(hits: list[dict]) -> bool:
    from .retriever import get_retriever
    return get_retriever().name == "dense" and hits[0].get("score", 0) >= STRONG_MATCH


def _finish(ans: Answer, t0: float) -> Answer:
    ans.latency_s = round(time.perf_counter() - t0, 2)
    return ans


def ask(question: str, history: list | None = None) -> Answer:
    t0 = time.perf_counter()

    # 1. input guardrails
    chk = guardrails.check_input(question)
    if not chk.ok:
        return _finish(Answer(chk.message, status="blocked"), t0)
    warnings = list(chk.warnings)

    # 2. retrieval
    try:
        from .retriever import retrieve
        hits = retrieve(_retrieval_query(chk.question, history), config.TOP_K)
    except FileNotFoundError:
        return _finish(Answer(
            "The legal knowledge base has not been prepared yet. "
            "Run `python -m backend.chunker` (and `python -m backend.build_index`), then try again.",
            status="error", warnings=["Knowledge base missing."]), t0)
    except Exception as e:
        log.error("retrieval failed: %s", type(e).__name__)
        return _finish(Answer("Sorry, searching the legal documents failed. Please try again.",
                              status="error", warnings=["Retrieval error."]), t0)

    if not hits:       # nothing relevant: never let the model guess
        return _finish(Answer(NO_SOURCE, status="no_source", warnings=warnings), t0)

    # 3. local LLM (in a worker thread so a hung model cannot freeze the UI forever)
    try:
        from assistant import llm
        text = _pool.submit(llm.answer, chk.question, hits).result(timeout=LLM_TIMEOUT_SECONDS)
    except FutureTimeout:
        return _finish(Answer("The model took too long to answer. Please try a shorter question.",
                              status="error", warnings=["Model timeout."]), t0)
    except ImportError:
        return _finish(Answer("The local language model library is not installed. Run `pip install ollama`.",
                              status="error", warnings=["Model library missing."]), t0)
    except Exception as e:
        kind = type(e).__name__
        log.error("llm failed: %s", kind)
        msg = ("The language model is not responding. Make sure Ollama is running and the model is "
               f"downloaded (`ollama pull {config.OLLAMA_MODEL}`).")
        return _finish(Answer(msg, status="error", warnings=["Model unavailable."]), t0)

    # 3b. Group 2's prompt said "not found" although retrieval matched strongly: ask once more with the
    #     backup prompt (still passages-only). Only for the dense retriever, whose scores are comparable.
    if text.strip() == NO_SOURCE and _strong_match(hits):
        try:
            from . import prompts
            text = _pool.submit(prompts.fallback_answer, chk.question, hits, NO_SOURCE).result(
                timeout=LLM_TIMEOUT_SECONDS)
        except Exception as e:
            log.error("fallback prompt failed: %s", type(e).__name__)

    # 4. the model itself said "not found" (llm.py normalises that message)
    if text.strip() == NO_SOURCE:
        return _finish(Answer(NO_SOURCE, status="no_source", warnings=warnings), t0)

    # 5. output guardrails: are the citations real? are the numbers in the sources?
    out = guardrails.check_output(text, hits)
    cited = [hits[i] for i in out.used] or hits      # if nothing was cited, show what was retrieved
    return _finish(Answer(
        answer=text,
        citations=[_citation(h) for h in cited],
        grounded=out.grounded,
        warnings=warnings + out.warnings,
    ), t0)
