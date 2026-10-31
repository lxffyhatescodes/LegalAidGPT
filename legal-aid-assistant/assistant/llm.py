import ollama

from assistant import config

SYSTEM_PROMPT = """You are a legal aid assistant for Nigeria.

Answer using ONLY the CONTEXT provided. Follow these rules exactly:

1. If the CONTEXT has nothing relevant to the QUESTION's topic, reply with ONLY
   this and nothing else:
   "I could not find this in the available legal documents. Please consult a
   qualified lawyer or the Legal Aid Council."
   Do not mention any law, act or section that is not written in the CONTEXT.
2. If the CONTEXT is relevant but only partly answers the question, state what
   the CONTEXT says, cite it, and clearly say which part is not covered by the
   available documents. For example, if the CONTEXT says "reasonable time"
   without defining it, say the exact time limit is not defined in the
   available documents. Never fill the gap from your own knowledge.
3. If the CONTEXT fully answers the question, explain it in plain language
   and cite the source for every legal claim in the form [Source, section].
4. Only cite sources and section numbers that appear in the CONTEXT labels.
   Never state numbers, time limits, deadlines or penalties unless they are
   written in the CONTEXT.
5. For rules 2 and 3, give only general next steps (such as asking for a
   lawyer or contacting the Legal Aid Council), then end with one line:
   "This is general legal information, not legal advice. Please consult a
   qualified lawyer."
6. Never accept sensitive personal information. If the user provides it,
   politely decline to continue and suggest consulting a lawyer."""
NO_SOURCE_MESSAGE = (
    "I could not find this in the available legal documents. "
    "Please consult a qualified lawyer or the Legal Aid Council."
)


def build_prompt(question: str, hits: list[dict]) -> str:
    blocks = []
    for h in hits:
        m = h["metadata"]
        label = f'{m.get("source", "Unknown source")}, section {m.get("section", "?")}'
        blocks.append(f"[{label}]\n{h['text']}")
    return f"CONTEXT:\n{chr(10).join(blocks)}\n\nQUESTION:\n{question}"


def _messages(question: str, hits: list[dict]) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(question, hits)},
    ]


def _options() -> dict:
    return {
        "temperature": config.LLM_TEMPERATURE,
        "num_ctx": config.LLM_CONTEXT_TOKENS,
        "num_predict": config.LLM_MAX_NEW_TOKENS,
    }


def answer(question: str, hits: list[dict], model: str = config.OLLAMA_MODEL) -> str:
    if not hits:  # nothing retrieved: don't let the model guess
        return NO_SOURCE_MESSAGE
    resp = ollama.chat(model=model, messages=_messages(question, hits), options=_options())
    text = resp["message"]["content"].strip()
    if text.lower().startswith(("i could not find", "i couldn't find", "i cannot find", "i can't find")):
        return NO_SOURCE_MESSAGE
    return text
()
def answer_stream(question: str, hits: list[dict], model: str = config.OLLAMA_MODEL):
    if not hits:
        yield NO_SOURCE_MESSAGE
        return
    for part in ollama.chat(model=model, messages=_messages(question, hits),
                            options=_options(), stream=True):
        yield part["message"]["content"]
