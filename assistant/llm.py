import re

import ollama

from assistant import config

SYSTEM_PROMPT = """You are a legal aid assistant for Nigeria. You explain the law in plain, everyday English for someone with no legal training.

Use ONLY the passages under CONTEXT. Each passage starts with a label line in square brackets, for example [Sample Act 2000, section 5].

Write your answer in three short parts:
Short answer: one or two plain sentences that answer the question.
What the law says: for each passage that helps, write its label line exactly as given, then explain in simple words what it means for the person.
What you can do: one or two general next steps, such as keeping written records, contacting the Legal Aid Council, or seeing a lawyer.

Rules:
- Square brackets are only for labels. Never put the text of a law inside square brackets. If you explain a hard word, use round brackets, for example: recognizance (a promise to appear in court).
- Explain only what the passages say. Do not add details, numbers, time limits, penalties or definitions that are not written in them. For example, do not say "working days" unless the passage does.
- The passages were chosen because they relate to the question. Use the ones that help. If they only partly answer it, say what they cover and what they do not.
- Speak to the person as "you". Never write as if you are the person, for example never say "my boss" or "I was".
- Never say what the person will win or lose.
- Do not ask the user for more information or documents.
- Keep the answer under 150 words (200 when asked to explain a section).
- Do not use the words "CONTEXT" or "passage". Say "the available legal documents".
- If the user shares sensitive personal information, politely decline to continue and suggest a lawyer.
- Only if the passages are about a completely different subject from the question, reply with just: "I could not find this in the available legal documents. Please consult a qualified lawyer or the Legal Aid Council.
- Cite only the passages that directly answer the question. Skip any passage that does not, even if it was provided. One passage is enough.
- Do not mention facts about the person's situation that they did not tell you, such as income, dependants or how long something lasted.
- Do not say what a court may or may not grant or order in the person's case. Only say what the law says.\""""

NO_SOURCE_MESSAGE = (
    "I could not find this in the available legal documents. "
    "Please consult a qualified lawyer or the Legal Aid Council."
)

DISCLAIMER_LINE = "This is general legal information, not legal advice. Please consult a qualified lawyer."

# Blocks outcome predictions only; plain statements of what the law says are allowed.
PREDICTION_PATTERN = re.compile(
    r"you (?:will|would) (?:win|lose|get|receive|be awarded)"
    r"|you are likely to"
    r"|entitled to (?:the entire|all of|everything)"
    r"|(?:may|might|will|would) not (?:grant|award) you"
    r"|you (?:may|might) not (?:get|receive)",
    re.IGNORECASE,
)

LAST_RAW = ""   # the model's text before any filter, for debugging


def build_prompt(question: str, hits: list[dict]) -> str:
    blocks = []
    for h in hits:
        m = h["metadata"]
        label = f'{m.get("source", "Unknown source")}, section {m.get("section", "?")}'
        blocks.append(f"[{label}]\n{h['text']}")
    strong = any(h.get("distance", 1.0) <= 0.25 for h in hits)
    note = "\n\nThese passages are directly relevant to the QUESTION. Answer from them." if strong else ""
    return f"CONTEXT:\n{chr(10).join(blocks)}{note}\n\nQUESTION:\n{question}"


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
        "num_thread": 4,
    }


def answer(question: str, hits: list[dict], model: str = config.OLLAMA_MODEL) -> str:
    global LAST_RAW
    if not hits:
        return NO_SOURCE_MESSAGE
    resp = ollama.chat(
        model=model,
        messages=_messages(question, hits),
        options=_options(),
        keep_alive="30m",
    )
    text = resp["message"]["content"].strip()
    LAST_RAW = text
    if text.lower().startswith(("i could not find", "i couldn't find", "i cannot find", "i can't find")):
        return NO_SOURCE_MESSAGE
    if PREDICTION_PATTERN.search(text):
        return NO_SOURCE_MESSAGE
    if "not legal advice" not in text.lower():
        text += "\n\n" + DISCLAIMER_LINE
    return text


def answer_stream(question: str, hits: list[dict], model: str = config.OLLAMA_MODEL):
    if not hits:
        yield NO_SOURCE_MESSAGE
        return
    stream = ollama.chat(
        model=model,
        messages=_messages(question, hits),
        options=_options(),
        stream=True,
        keep_alive="30m",
    )
    for part in stream:
        yield part["message"]["content"]