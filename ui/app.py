"""Legal-AI chat page (ChatGPT-style). Run from the project root:  streamlit run ui/app.py"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from assistant import config
from assistant.pipeline import ask

st.set_page_config(page_title="Legal-AI", page_icon="⚖️", layout="centered")

CSS = """
<style>
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}
.block-container {max-width: 760px; padding-top: 2rem; padding-bottom: 7rem;}

/* sidebar */
section[data-testid="stSidebar"] {background: #F9F9F9; border-right: 1px solid #ECECEC;}
section[data-testid="stSidebar"] .stButton button {
    border-radius: 10px; border: none; background: transparent; text-align: left;
    justify-content: flex-start; font-weight: 500;}
section[data-testid="stSidebar"] .stButton button:hover {background: #ECECEC;}

/* messages: no avatars, assistant plain text, user in a grey bubble on the right */
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {display: none;}
[data-testid="stChatMessage"] {background: transparent; padding: .4rem 0;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {flex-direction: row-reverse;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
    background: #F4F4F4; border-radius: 20px; padding: .6rem 1.1rem; width: fit-content;
    max-width: 80%; margin-left: auto;}
[data-testid="stChatMessageContent"] {font-size: 1rem; line-height: 1.7;}

/* input: rounded pill with a soft shadow, disclaimer line under it */
[data-testid="stBottom"] > div {background: #FFFFFF;}
[data-testid="stChatInput"] {border-radius: 28px; border: 1px solid #E5E5E5;
    box-shadow: 0 2px 10px rgba(0,0,0,.06);}
[data-testid="stChatInput"] textarea {font-size: 1rem;}
[data-testid="stBottom"]::after {content: "__DISCLAIMER__"; display: block; text-align: center;
    font-size: .75rem; color: #6B6B6B; padding: .5rem 1rem .8rem;}

/* pill buttons for suggestions */
.stButton button {border-radius: 999px; border: 1px solid #E5E5E5; background: #FFFFFF;}
.stButton button:hover {background: #F4F4F4; border-color: #D4D4D4;}

/* sources and urgent notice */
[data-testid="stExpander"] {border: 1px solid #ECECEC; border-radius: 12px;}
.urgent {border-left: 4px solid #B45309; padding: .6rem .9rem; background: #FEF3C7;
         border-radius: 8px; margin-bottom: .75rem; font-size: .95rem;}
.hero {text-align: center; font-size: 2rem; font-weight: 600; padding: 16vh 0 1.5rem;}
</style>
"""
st.markdown(CSS.replace("__DISCLAIMER__", config.DISCLAIMER), unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []


def stream_words(text: str):
    for part in re.split(r"(\s+)", text):
        yield part
        time.sleep(0.008)


def render_assistant(m: dict, stream: bool = False) -> None:
    if m.get("urgent"):
        st.markdown(
            "<div class='urgent'><strong>Need help right now?</strong><br>"
            "If you are in danger, contact the emergency services. If you have been arrested, "
            "ask to speak to a lawyer or a legal aid office as soon as you can.</div>",
            unsafe_allow_html=True,
        )
    if stream:
        st.write_stream(stream_words(m["content"]))
    else:
        st.markdown(m["content"])
    for w in m.get("warnings", []):
        st.warning(w)
    if m.get("citations"):
        st.caption("Sources")
        for i, c in enumerate(m["citations"], 1):
            with st.expander(f"[{i}] {c['doc_title']}, {c['section']}"):
                st.write(c["excerpt"])
                st.caption(f"Reference: {c['chunk_id']}")
    elif not m.get("grounded", True):
        st.info("No matching source was found, so no answer was generated from the law.")
    if m.get("seconds") is not None:
        st.caption(f"⏱ Answered in {m['seconds']:.1f} s")


# ---- Sidebar (top part) ----------------------------------------------------
with st.sidebar:
    if st.button("✏️  New chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.markdown("**Legal-AI**")
    topic_label = st.selectbox("Topic", list(config.TOPICS.keys()))
    topic_tag = config.TOPICS[topic_label]

# ---- Main ------------------------------------------------------------------
typed = st.chat_input("Ask anything about your legal situation")
question = st.session_state.pop("pending", None) or typed

if not st.session_state.messages and not question:
    st.markdown("<div class='hero'>What can I help with?</div>", unsafe_allow_html=True)
    for q in config.SAMPLE_QUESTIONS:
        if st.button(q, use_container_width=True):
            st.session_state.pending = q
            st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m["role"] == "assistant":
            render_assistant(m)
        else:
            st.markdown(m["content"])

if question:
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Searching the legal documents..."):
            started = time.perf_counter()
            result = ask(question, history, {"topic": topic_tag} if topic_tag else None)
            elapsed = time.perf_counter() - started
        msg = {
            "role": "assistant",
            "content": result["answer"],
            "citations": result["citations"],
            "grounded": result["grounded"],
            "warnings": result["warnings"],
            "urgent": result.get("urgent", False),
            "seconds": elapsed,
        }
        render_assistant(msg, stream=True)
    st.session_state.messages.append(msg)
# ---- Sidebar (bottom part, runs after the answer so it is always current) --
with st.sidebar:
    last = next((m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
    st.markdown("**Sources in last answer**")
    if last and last.get("citations"):
        for c in last["citations"]:
            st.caption(f"{c['doc_title']}, {c['section']}")
    else:
        st.caption("Nothing yet.")
    st.divider()
    st.caption("Please do not enter ID numbers, bank details or other sensitive personal information.")
    if config.USE_MOCK:
        st.caption("Demo mode: placeholder data.")
