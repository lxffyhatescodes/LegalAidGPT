# Joining 2.3 and 2.4

**File:** `assistant/guidance_pipeline.py`   **Demo:** `scripts/demo_guidance.py`

Order of events:
1. `prepare_question`: check the question, classify it, pick modes, build the extra prompt text.
2. Search (P6) and model (P7/P8): passed in as functions.
3. `process_answer`: check the answer's citations, figures and tone, then return a result.

Statuses: `ok`, `review_required` (no citation), `blocked` (invented citation/figure or over-confident),
`no_sources`, `out_of_scope`, `refused`, `redirected`.

## Before you add these files: delete the older versions
These came from an earlier draft and are replaced by the new files:
    assistant/modes.py        assistant/citations.py     assistant/sources.py     assistant/guided.py
    tests/test_modes.py       tests/test_citations.py    tests/test_guided.py
    scripts/demo_guided.py    docs/guidance_and_guardrails.md
(`assistant/guardrails.py`, `tests/test_guardrails.py`, `tests/helpers.py` and `tests/conftest.py` are overwritten.)

## For P8 (assistant/pipeline.py)
    from assistant.guidance_pipeline import guided_ask

    def ask(question, history=None):
        return guided_ask(question, history, retrieve_fn=<P6 search function>)

`retrieve_fn(question, problem_areas, top_k)` returns chunks like
`{"text": "...", "metadata": {"source": "...", "section": "..."}, "similarity": 0.8}`.
Use `answer_question(...)` instead if you want the full result dict (status, warnings...).

## Settings (put in config.py to change)
- `SHOW_UNVERIFIED_ANSWERS = False` (default): answers with an invented citation or figure are hidden.
  Set `True` to show them with `[UNVERIFIED CITATION]` marks and a warning.

## To confirm with the team
1. P6: does each chunk carry `similarity` or `distance`? (Distance is converted as 1 - distance.)
2. P6/P7: chunk metadata must have `source` and `section` (as llm.py uses).
3. The 112 emergency wording in `guardrails.py` before release.

## Run
    python -m pytest tests
    python scripts/demo_guidance.py
