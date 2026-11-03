"""Joins 2.3 (guidance modes) and 2.4 (guardrails + citations) into one flow.

    question
      -> prepare_question()   BEFORE the model: check question, classify, pick modes
      -> retrieve + model     (written by the other groups; passed in as functions)
      -> process_answer()     AFTER the model: check citations, figures and tone

P8 connects it in assistant/pipeline.py with:

    from assistant.guidance_pipeline import guided_ask
    def ask(question, history=None):
        return guided_ask(question, history, retrieve_fn=<P6 search function>)

retrieve_fn(question, problem_areas, top_k) -> list of chunks, each like
    {"text": "...", "metadata": {"source": "...", "section": "..."}, "similarity": 0.8}
(problem_areas is a list such as ["tenant", "all_areas"]; empty list = search everything)
"""
from assistant.guidance_modes import (
    classify_question,
    select_guidance_modes,
    build_mode_instructions,
)
from assistant.citation_validator import (
    validate_citations,
    remove_invalid_citations,
    citations_for_ui,
    find_unsupported_figures,
    chunk_info,
)
from assistant.guardrails import (
    NO_SOURCE_MESSAGE,
    OUT_OF_SCOPE_MESSAGE,
    UNSAFE_ANSWER_MESSAGE,
    check_question,
    check_scope,
    filter_weak_chunks,
    is_no_source_answer,
    run_guardrails,
    add_legal_notice,
)

try:
    from assistant import config
    TOP_K = config.TOP_K
    SHOW_UNVERIFIED_ANSWERS = getattr(config, "SHOW_UNVERIFIED_ANSWERS", False)
except ImportError:
    TOP_K = 4
    SHOW_UNVERIFIED_ANSWERS = False
# SHOW_UNVERIFIED_ANSWERS = False (default, safer): an answer with a citation or figure that is
#   not in the sources is hidden. True: it is shown with [UNVERIFIED CITATION] marks and a warning.


# ---------------------------------------------------------------------------
# BEFORE the model
# ---------------------------------------------------------------------------
def prepare_question(question, history=None):
    """Checks the question and decides how to answer it. Nothing here calls the model."""
    check = check_question(question)
    if check["action"] == "refuse":
        return {"allowed": False, "status": "refused", "message": check["message"]}
    if check["action"] == "redirect":
        return {"allowed": False, "status": "redirected", "message": check["message"]}

    classification = classify_question(question, history)
    if not check_scope(classification)["allowed"]:
        return {"allowed": False, "status": "out_of_scope", "message": OUT_OF_SCOPE_MESSAGE,
                "classification": classification}

    modes = select_guidance_modes(classification)
    return {
        "allowed": True,
        "classification": classification,
        "modes": modes,
        "mode_instructions": build_mode_instructions(modes),
        "problem_areas": classification["problem_areas"],
        "notices": check["notices"],
    }


# ---------------------------------------------------------------------------
# AFTER the model
# ---------------------------------------------------------------------------
def _blocked_message(retrieved_chunks):
    sources = []
    for chunk in retrieved_chunks:
        source, section = chunk_info(chunk)
        line = f"- {source}, section {section}"
        if line not in sources:
            sources.append(line)
    return ("I couldn't confirm that the generated answer matches the legal documents, so I am "
            "not showing it. These are the passages I found:\n" + "\n".join(sources) +
            "\n\nPlease read them or consult a qualified lawyer.")


def process_answer(classification, retrieved_chunks, answer, question="", notices=None):

    notices = list(notices or [])

    # 1. Select guidance modes
    modes = select_guidance_modes(classification)

    # 2. Run guardrails
    checks = run_guardrails(
        classification,
        retrieved_chunks,
        answer
    )

    def result(status, text, citations=None, warnings=(), ui=()):
        return {
            "status": status,
            "answer": text,
            "guidance_modes": modes,
            "citations": citations,
            "guardrails": checks,
            "warnings": notices + list(warnings),
            "ui_citations": list(ui),
        }

    if not checks["allowed_to_answer"]:
        message = OUT_OF_SCOPE_MESSAGE if not checks["scope"]["allowed"] else NO_SOURCE_MESSAGE
        status = "out_of_scope" if not checks["scope"]["allowed"] else "no_sources"
        return result(status, message)

    if not checks["response"]["passed"]:
        return result("blocked", UNSAFE_ANSWER_MESSAGE,
                      warnings=["The answer was withheld because it sounded too certain."])

    # 3. Validate citations and figures
    citations = validate_citations(answer, retrieved_chunks)
    figures = find_unsupported_figures(answer, retrieved_chunks, question)

    # 4. Remove unverified citation markers
    cleaned_answer = remove_invalid_citations(answer, citations)

    warnings = []
    if citations["invalid_citations"]:
        warnings.append("Some references could not be matched to the sources: "
                        + "; ".join(citations["invalid_citations"]))
    if figures:
        warnings.append("These figures are not in the retrieved sources, please verify: "
                        + "; ".join(figures))

    if not citations["has_citations"]:
        warnings.append("This answer could not be linked to a specific source section. "
                        "Please check it against the sources or consult a lawyer.")
    if warnings and not SHOW_UNVERIFIED_ANSWERS:
            return result("blocked", _blocked_message(retrieved_chunks), citations,
                          ["The answer was withheld because it was not fully supported by the sources."])
    

    ui = citations_for_ui(citations, retrieved_chunks)
    return result("ok" if citations["is_valid"] and not figures else "review_required",
                  add_legal_notice(cleaned_answer), citations, warnings, ui)


# ---------------------------------------------------------------------------
# The whole flow
# ---------------------------------------------------------------------------
def _default_retrieve(question, problem_areas, top_k):
    raise NotImplementedError(
        "Pass retrieve_fn: retrieve_fn(question, problem_areas, top_k) -> list of chunks.")


def _default_llm(question, chunks, mode_instructions):
    from assistant import llm      # imported here so tests do not need ollama installed
    if mode_instructions:          # llm.answer has no slot for extra instructions, so add them to the question
        question = f"{question}\n\n[{mode_instructions}]"
    return llm.answer(question, chunks)


def answer_question(question, history=None, retrieve_fn=None, llm_fn=None):
    """Runs everything and returns the result dict (status, answer, warnings, ...)."""
    retrieve_fn = retrieve_fn or _default_retrieve
    llm_fn = llm_fn or _default_llm

    prep = prepare_question(question, history)
    if not prep["allowed"]:
        return {"status": prep["status"], "answer": prep["message"], "warnings": [],
                "ui_citations": [], "guidance_modes": [], "citations": None, "guardrails": None}

    def stop(status, message):
        return {"status": status, "answer": message, "warnings": prep["notices"],
                "ui_citations": [], "guidance_modes": prep["modes"], "citations": None,
                "guardrails": None}

    chunks = filter_weak_chunks(retrieve_fn(question, prep["problem_areas"], TOP_K))
    if not chunks and prep["problem_areas"]:      # the topic guess may be wrong: try everything once
        chunks = filter_weak_chunks(retrieve_fn(question, [], TOP_K))
    if not chunks:
        return stop("no_sources", NO_SOURCE_MESSAGE)

    raw = (llm_fn(question, chunks, prep["mode_instructions"]) or "").strip()
    if not raw or is_no_source_answer(raw):
        return stop("no_sources", NO_SOURCE_MESSAGE)

    return process_answer(prep["classification"], chunks, raw, question, prep["notices"])


def guided_ask(question, history=None, retrieve_fn=None, llm_fn=None):
    """Same flow, but returns the Answer object that ui/app.py already expects."""
    from assistant.pipeline import Answer   # imported here to avoid a circular import
    result = answer_question(question, history, retrieve_fn, llm_fn)
    return Answer(
        answer=result["answer"],
        citations=result["ui_citations"],
        grounded=result["status"] == "ok",
        warnings=result["warnings"],
    )
