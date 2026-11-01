"""P8 owns this file. `ask()` is the single entry point the UI calls.

The real pipeline (guardrails -> retrieval -> local LLM -> output checks) lives in backend/.
See backend/README.md. Answer fields: answer, citations, grounded, warnings, disclaimer, latency_s, status.
"""
from backend import Answer, ask  # noqa: F401
