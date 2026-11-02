# Backend (Group 3.2: backend and integration)

Everything for the backend lives in this folder. No file owned by another group was changed;
the backend only READS `assistant/config.py` and calls `assistant/llm.py`.

## Flow
    backend.ask(question, history) -> Answer
      1. guardrails.check_input   empty / too long / personal data / prompt injection / harmful requests
      2. retriever.retrieve       top-k passages above the threshold ([] = not covered)
      3. assistant.llm.answer     local Ollama model (Group 2's code)
      4. guardrails.check_output  citations must match retrieved passages; numbers must appear in them
`ask()` always returns an `Answer` (answer, citations, grounded, warnings, disclaimer, latency_s, status).
status: ok | no_source | blocked | error. Nothing is saved to disk and questions are not logged.

## Retrieval details
- Lay words are expanded with legal vocabulary before searching (`EXPANSIONS` in retriever.py); the LLM still sees the original question.
- At most 2 chunks per section; the best 3 hits are merged with the next chunk of their section so the model sees whole provisions.
- If the model says "not found" although the best match is strong (score >= 0.55), the question is retried once with a backup prompt (prompts.py).
- `python -m backend.try_retrieval "your question"` shows what the search returns, without the LLM.

## Setup (run from the repo root)
    pip install ollama
    # backend/data/chunks.jsonl is already included (python -m backend.chunker rebuilds it from data/clean)
    python -m backend.build_index    # optional but recommended: embeddings + FAISS (internet needed once)
    ollama pull llama3.2:3b
Without the FAISS index it falls back to keyword (TF-IDF) search.

## Test
    pytest -q backend/tests          # LLM is faked, Ollama not needed

## Connecting the UI (one line, done only when the group agrees)
The UI calls `assistant.pipeline.ask`. To use this backend, `assistant/pipeline.py` can simply do:
    from backend import ask, Answer   # noqa
Until then, try it directly:  python -c "from backend import ask; print(ask('How long can police hold me?'))"
