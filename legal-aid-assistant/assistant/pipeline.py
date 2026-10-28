"""P8 owns this file. `ask()` is the single entry point the UI calls.
This is a stub: replace the body with guardrails -> retrieve -> prompt -> LLM -> output checks."""
from dataclasses import dataclass, field

from assistant import config


@dataclass
class Answer:
    answer: str
    citations: list = field(default_factory=list)   # [{"chunk_id", "doc_title", "section", "excerpt"}]
    grounded: bool = False
    warnings: list = field(default_factory=list)
    disclaimer: str = config.DISCLAIMER


def ask(question: str, history: list | None = None) -> Answer:
    # Tip: load the embedding model, index and LLM once (module-level singleton or
    # @st.cache_resource) so they are not reloaded on every Streamlit rerun.
    return Answer(answer=f"(stub) The pipeline is not connected yet. You asked: {question}")
