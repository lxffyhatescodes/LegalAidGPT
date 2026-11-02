"""Group 3.2 backend. Self-contained: it only READS from the other groups' code (assistant.config, assistant.llm)."""
from .pipeline import Answer, ask  # noqa: F401,E402  ->  from backend import ask
