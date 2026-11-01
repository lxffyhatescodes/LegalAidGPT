# 2.4 Citations and guardrails

**Files:** `assistant/guardrails.py`, `assistant/citation_validator.py`
**Tests:** `tests/test_guardrails.py`, `tests/test_citation_validator.py`

## guardrails.py
Before the model:
- `check_question`: refuses empty questions, personal data (phone, BVN/NIN, bank or card number, email) and prompt tricks; answers self-harm messages with a support message; adds urgent notices (danger, custody, eviction/court papers).
- `check_scope`: stops questions that are not legal.
- `check_retrieval_sufficiency` / `filter_weak_chunks`: stops if nothing relevant was found (uses `MIN_SIMILARITY` from config).

After the model:
- `check_response_guardrails`: flags over-confident answers ("you will win") and claims to be a lawyer.
- `add_legal_notice`: adds the "not legal advice" line if the model forgot it.

## citation_validator.py
- `validate_citations`: every `[Source, section 35]` in the answer must match a passage that was really retrieved.
- `remove_invalid_citations`: replaces bad ones with `[UNVERIFIED CITATION]`.
- `find_unsupported_figures`: time limits, amounts and percentages must appear in the sources (or the question).
- `citations_for_ui`: builds the list the Sources box in `ui/app.py` shows.

The citation format matches `llm.py`: `[Source name, section N]`. If P7 changes that format, change `CITATION_PATTERN`.

## Run the tests
    python -m pytest tests/test_guardrails.py tests/test_citation_validator.py
