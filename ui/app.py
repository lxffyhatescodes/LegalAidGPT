"""
LegalAidGPT : the chat page.   Run from the project root:   streamlit run ui/app.py

Streamlit runs this whole file again from the top every time you click or type.
Anything that must survive between runs (the chats) is kept in st.session_state.

How the file is organised, top to bottom:
  1. Page setup            tab title, icon, layout
  2. Look and feel         loads the colours (light and dark) and chat.css
  3. Chat history          how chats are stored and how "New chat" works
  4. Helpers               small functions that draw an answer
  5. Sidebar (top)         logo, New chat, topic picker
  6. The question handler  sends a question to the backend and shows the answer
  7. Main area             welcome screen, past messages, the message box
  8. Sidebar (bottom)      recent chats, links, appearance switch

The backend is only touched in two places: `ask(...)` in section 6, and the values
read from assistant/config.py (topics, sample questions, disclaimer, demo mode).
"""
import html
import re
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # lets us import `assistant` and `ui`

import streamlit as st

from assistant import config
from assistant.pipeline import ask
from ui import theme

HERE = Path(__file__).resolve().parent
MAX_STARTER_CARDS = 4          # suggestion cards on the welcome screen (cards are laid out in one row)


# 1. PAGE SETUP (must be the first Streamlit call)
_favicon = HERE / "assets" / "favicon.png"
st.set_page_config(
    page_title="LegalAidGPT",
    page_icon=str(_favicon) if _favicon.exists() else "⚖️",
    layout="centered",
    initial_sidebar_state="expanded",
)


# 2. LOOK AND FEEL
#    Colours and shared styling: ui/theme.py and ui/styles/base.css
#    Chat-page styling:          ui/styles/chat.css
# Small icons drawn on the suggestion cards (in order: arrest, home, work, money).
_ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#008751" '
         'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{}</svg>')
CARD_ICONS = [
    _ICON.format('<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z"/>'),
    _ICON.format('<path d="M4 11l8-7 8 7v9H4z"/><path d="M10 20v-6h4v6"/>'),
    _ICON.format('<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5h6v2M3 13h18"/>'),
    _ICON.format('<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18M7 15h4"/>'),
]
# One CSS rule per card: "card number N gets icon N".
CARD_ICON_CSS = "".join(
    f'[data-testid="stHorizontalBlock"] > div:nth-child({i + 1}) .stButton button::after'
    f'{{background-image: url("data:image/svg+xml;utf8,{quote(svg, safe="")}");}}\n'
    for i, svg in enumerate(CARD_ICONS)
)

chat_css = (HERE / "styles" / "chat.css").read_text(encoding="utf-8")
_disclaimer = config.DISCLAIMER.replace("\\", "\\\\").replace('"', '\\"')
dynamic_css = (
    f':root {{--disclaimer: "{_disclaimer}";}}\n'                                              # text under the message box
    f'[data-testid="stChatMessageAvatarAssistant"] {{background-image: url("{theme.MARK_URI}") !important;}}\n'  # logo avatar
    f"{CARD_ICON_CSS}"                                                                         # icons on the cards
)
theme.inject(chat_css + "\n" + dynamic_css)


# 3. CHAT HISTORY
#    st.session_state.chats   all chats, e.g. {"a1b2c3d4": {"title": ..., "messages": [...]}}
#    st.session_state.order   chat ids, newest first
#    st.session_state.current id of the chat being shown
#    History lasts for the browser session only (a refresh starts empty).
def start_new_chat() -> None:
    """Switch to an empty chat, creating one only if there is no empty chat already."""
    chats = st.session_state.chats
    for chat_id in st.session_state.order:
        if not chats[chat_id]["messages"]:
            st.session_state.current = chat_id
            return
    chat_id = uuid.uuid4().hex[:8]
    chats[chat_id] = {"title": "New chat", "messages": []}
    st.session_state.order.insert(0, chat_id)
    st.session_state.current = chat_id


if "chats" not in st.session_state:        # very first run of this browser session
    st.session_state.chats, st.session_state.order = {}, []
    start_new_chat()

chat = st.session_state.chats[st.session_state.current]
messages = chat["messages"]                # [{"role": "user" | "assistant", "content": ...}, ...]


# 4. HELPERS THAT DRAW AN ANSWER
def stream_words(text: str):
    """Hand the answer out a word at a time so it appears as if it is being typed."""
    for part in re.split(r"(\s+)", text):
        yield part
        time.sleep(0.008)


def show_notice(text: str, kind: str = "info") -> None:
    """A soft coloured box. kind is "info" (green) or "warn" (amber)."""
    st.markdown(f"<div class='callout {kind}'>{html.escape(text)}</div>", unsafe_allow_html=True)


def show_answer(m: dict, stream: bool = False) -> None:
    """Draw one assistant message: urgent box, text, warnings, sources.

    stream=True types the answer out (used for a brand-new answer);
    stream=False just shows it (used when redrawing earlier messages).
    """
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

    for warning in m.get("warnings", []):
        show_notice(warning, "warn")

    if m.get("citations"):
        st.markdown(
            f"<div class='src-label'>Sources<span class='count'>{len(m['citations'])}</span></div>",
            unsafe_allow_html=True,
        )
        for number, c in enumerate(m["citations"], 1):
            with st.expander(f"[{number}] {c['doc_title']}, {c['section']}"):
                st.write(c["excerpt"])
                st.caption(f"Reference: {c['chunk_id']}")
    elif not m.get("grounded", True):
        show_notice("No matching source was found, so no answer was generated from the law.", "info")


# 5. SIDEBAR (TOP PART)
#    The recent chats are filled in later,
#    in section 8, through the empty containers created here.
with st.sidebar:
    theme.brand()
    if st.button("+  New chat", use_container_width=True, type="primary"):
        start_new_chat()
        st.rerun()

    history_slot = st.container()          # "Recent" chats go here (section 8)

    st.markdown("<div class='side-title'>Topic</div>", unsafe_allow_html=True)
    topic_label = st.selectbox("Topic", list(config.TOPICS.keys()), label_visibility="collapsed")
    topic_tag = config.TOPICS[topic_label]  # None means "all topics"

    links_slot = st.container()            # links and the appearance switch go here (section 8)


# 6. THE QUESTION HANDLER  (the only place that calls the backend)
def answer_question(question: str) -> None:
    """Show the question, ask the backend, show and remember the answer."""
    history = [{"role": m["role"], "content": m["content"]} for m in messages]   # earlier turns, for context
    if not messages:                                                             # first message names the chat
        chat["title"] = question.strip()[:40] + ("…" if len(question.strip()) > 40 else "")

    messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching the legal documents..."):
            result = ask(question, history, {"topic": topic_tag} if topic_tag else None)   # <- BACKEND

        answer = {
            "role": "assistant",
            "content": result["answer"],
            "citations": result["citations"],
            "grounded": result["grounded"],
            "warnings": result["warnings"],
            "urgent": result.get("urgent", False),
        }
        show_answer(answer, stream=True)
    messages.append(answer)


# 7. MAIN AREA
typed = st.chat_input("Ask anything about your legal situation")
# A suggestion card stores its question in "pending" and reruns the page; pick it up here.
question = st.session_state.pop("pending", None) or typed

# --- Welcome screen: only for an empty chat -----------------------------------
if not messages and not question:
    st.markdown(
        f"<div class='welcome'><div class='w-mark'>{theme.MARK_SVG}</div>"
        "<div class='w-hi'>Hi, I'm LegalAidGPT</div>"
        "<div class='w-sub'>How can I help with your legal situation today?</div></div>",
        unsafe_allow_html=True,
    )

    starters = config.SAMPLE_QUESTIONS[:MAX_STARTER_CARDS]
    columns = st.columns(len(starters))
    for i, starter in enumerate(starters):
        with columns[i]:
            if st.button(starter, use_container_width=True, key=f"sample_{i}"):
                st.session_state.pending = starter
                st.rerun()

    st.markdown(
        "<div class='w-note'>Answers come from Nigerian legal texts and show where they are from.</div>",
        unsafe_allow_html=True,
    )

# --- Messages already in this chat ---------------------------------------------
for m in messages:
    with st.chat_message(m["role"]):
        if m["role"] == "assistant":
            show_answer(m)
        else:
            st.markdown(m["content"])

# --- A new question, if there is one --------------------------------------------
if question:
    answer_question(question)


# 8. SIDEBAR (BOTTOM PART)
#    Runs after the answer so it always shows the latest chat.
with history_slot:
    chats_with_messages = [cid for cid in st.session_state.order if st.session_state.chats[cid]["messages"]]
    if chats_with_messages:
        st.markdown("<div class='side-title'>Recent</div>", unsafe_allow_html=True)
        for chat_id in chats_with_messages:
            title = st.session_state.chats[chat_id]["title"]
            if chat_id == st.session_state.current:
                st.markdown(f"<div class='hist-active'>{html.escape(title)}</div>", unsafe_allow_html=True)
            elif st.button(re.sub(r"[*_`#\[\]]", "", title), key=f"chat_{chat_id}", use_container_width=True):
                st.session_state.current = chat_id
                st.rerun()

with links_slot:
    st.markdown("<div class='side-title' style='margin-top:1.2rem'>More</div>", unsafe_allow_html=True)
    theme.nav_links(skip="home")           # links to Explain a document and Analytics

    st.markdown(
        "<div class='side-note' style='margin-top:1.2rem'>Please do not enter ID numbers, bank details or "
        "other sensitive personal information.</div>",
        unsafe_allow_html=True,
    )
    theme.appearance_picker()
    if config.USE_MOCK:
        st.markdown("<div class='side-note' style='margin-top:.5rem'>Demo mode: placeholder data.</div>",
                    unsafe_allow_html=True)
