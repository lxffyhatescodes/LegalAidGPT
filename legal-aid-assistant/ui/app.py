"""P1/P2: Streamlit chat UI. Run with: streamlit run ui/app.py"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant import config
from assistant.pipeline import ask

st.set_page_config(page_title="Legal Aid Assistant", layout="centered")
st.title("Legal Aid Assistant")
st.caption(config.DISCLAIMER)

if "messages" not in st.session_state:
    st.session_state.messages = []


def show_sources(citations):
    if not citations:
        return
    with st.expander("Sources"):
        for c in citations:
            st.markdown(f"**{c.get('doc_title', '')}, {c.get('section', '')}**")
            st.caption(c.get("excerpt", ""))


for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        show_sources(m.get("citations"))

if question := st.chat_input("Describe your legal question"):
    history = list(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching the legal documents..."):
            answer = ask(question, history)
        st.markdown(answer.answer)
        for w in answer.warnings:
            st.warning(w)
        show_sources(answer.citations)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer.answer, "citations": answer.citations}
    )
