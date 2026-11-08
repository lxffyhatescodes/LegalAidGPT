"""
theme.py : the look shared by every page.

What lives here
  1. The logo
  2. The colours (green and white, light and dark), the one place to change them
  3. Loading the CSS files and applying light / dark mode
  4. The Appearance switch (System / Light / Dark)
  5. Sidebar pieces: brand, links to other pages, the "Back to home" button

How to use it from a page
  Chat page:        theme.inject(extra_css)  then  theme.brand() ...
  Other pages:      theme.setup("doc")  then  theme.back_to_home()
"""
from pathlib import Path
from urllib.parse import quote

import streamlit as st

STYLES_DIR = Path(__file__).resolve().parent / "styles"


# 1. LOGO  (a balanced scale on a green tile)
MARK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
    '<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#00A86B"/><stop offset="1" stop-color="#006B3F"/></linearGradient></defs>'
    '<rect width="48" height="48" rx="14" fill="url(#lg)"/>'
    '<g fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M24 10v28"/><path d="M16 38h16"/><path d="M11 15h26"/>'
    '<path d="M11 15 6.5 26M11 15l4.5 11M37 15l-4.5 11M37 15l4.5 11"/></g>'
    '<g fill="#fff"><circle cx="24" cy="9" r="2.2"/>'
    '<path d="M5.5 26h11a5.5 5.5 0 0 1-11 0zM31.5 26h11a5.5 5.5 0 0 1-11 0z"/></g></svg>'
)
# Same logo as an image address, used as the assistant's little avatar in the chat.
MARK_URI = "data:image/svg+xml;utf8," + quote(MARK_SVG, safe="")


# 2. COLOURS: change a colour here and it changes on every page.
#    Each line is  --name:#colour;  and the CSS files use it as var(--name).
LIGHT_VARS = """
    --bg:#FFFFFF;            /* page background */
    --side:#F1F8F4;          /* sidebar background */
    --surface:#F1F8F4;       /* soft boxes: message bubbles, cards, input bar */
    --surface-hover:#E0F0E7; /* a surface when the mouse is over it */
    --active:#CDE9D8;        /* highlighted item (current chat or page) */
    --active-ink:#0B3D24;    /* text on a highlighted item */
    --ink:#1A1F1C;           /* main text */
    --muted:#5B6660;         /* quieter text */
    --line:#DDE7E1;          /* thin borders */
    --card:#FFFFFF; --field:#FFFFFF; --pop:#FFFFFF;   /* white boxes, input fields, dropdown menus */
    --focus-bg:#FFFFFF;      /* chat box while typing */
    --circle:#FFFFFF;        /* small round icon on a suggestion card */
    --link:#008751;          /* links (Nigerian flag green) */
    --green:#008751; --green-dark:#006B3F;            /* main button colour and its hover colour */
    --urgent-bg:#FCE8E6; --urgent-ink:#5F1812; --urgent-strong:#B3261E;   /* red "need help now" box */
    --info-bg:#E6F4EC; --info-ink:#0B3D24;             /* green notice */
    --warn-bg:#FEF7E0; --warn-ink:#4A3500;             /* amber notice */
    --shadow:rgba(0,135,81,.16);                       /* glow around the chat box */
    --chart-filter:none;                               /* charts are drawn as they are in light mode */
    color-scheme: light;
"""

DARK_VARS = """
    --bg:#0F1512; --side:#16201B; --surface:#16201B; --surface-hover:#1F2D26;
    --active:#1E4D36; --active-ink:#D8F3E4;
    --ink:#E6EDE9; --muted:#9AA8A0; --line:#26332C;
    --card:#121B16; --field:#0F1512; --pop:#16201B;
    --focus-bg:#16201B; --circle:#0F1512;
    --link:#4CC38A;
    --green:#00A86B; --green-dark:#00C27A;
    --urgent-bg:#3B1B19; --urgent-ink:#F4C7C3; --urgent-strong:#FF8A80;
    --info-bg:#17382A; --info-ink:#CFEFDD; --warn-bg:#3A3015; --warn-ink:#F6E3A1;
    --shadow:rgba(0,0,0,.5);
    --chart-filter:invert(1) hue-rotate(180deg);       /* flips the Analytics charts so text is light on dark */
    color-scheme: dark;
"""


# 3. LOADING THE CSS AND APPLYING LIGHT / DARK
FONT_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');"
FONT_STACK = "'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', sans-serif"


def inject(extra_css: str = "") -> None:
    """Put the shared look on the page.

    extra_css is CSS for one page only (the chat page passes the contents of chat.css).
    """
    base_css = (STYLES_DIR / "base.css").read_text(encoding="utf-8")
    # The font import must be the very first thing in the style block, then the colour lists.
    head_css = (
        f"{FONT_IMPORT}\n"
        f":root {{{LIGHT_VARS}\n    --font: {FONT_STACK};}}\n"
        f"@media (prefers-color-scheme: dark) {{:root {{{DARK_VARS}}}}}\n"
    )

    # System = follow the device (head_css above does that with a media query).
    # Light / Dark = the person chose, so we add the colours again at the very end to win.
    forced = {"Light": LIGHT_VARS, "Dark": DARK_VARS}.get(current_mode())
    forced_css = f":root {{{forced}}}" if forced else ""

    st.markdown(f"<style>{head_css}{base_css}\n{extra_css}\n{forced_css}</style>", unsafe_allow_html=True)


# 4. THE APPEARANCE SWITCH
OPTIONS = ["System", "Light", "Dark"]


def current_mode() -> str:
    """Which mode is on right now: 'System', 'Light' or 'Dark'.

    The choice is saved in two places on purpose. "appearance_w" belongs to the radio
    button and is the freshest value right after a click. Streamlit throws a radio's value
    away when you open a page that has no such radio, so "_appearance" keeps a copy that
    survives moving between pages.
    """
    return st.session_state.get("appearance_w") or st.session_state.get("_appearance", "System")


def appearance_picker() -> None:
    """Draw the System / Light / Dark switch in the sidebar."""
    st.markdown("<div class='side-title' style='margin-top:1.2rem'>Appearance</div>", unsafe_allow_html=True)
    saved = st.session_state.get("_appearance", "System")
    choice = st.radio(
        "Appearance", OPTIONS,
        index=OPTIONS.index(saved) if saved in OPTIONS else 0,
        key="appearance_w", horizontal=True, label_visibility="collapsed",
    )
    st.session_state["_appearance"] = choice


# 5. SIDEBAR PIECES AND PAGE HELPERS
# Pages shown in the sidebar: (key, file path relative to ui/app.py, label shown)
NAV = [
    ("home", "app.py", "Home"),
    ("doc", "pages/1_Explain_a_document.py", "Explain a document"),
    ("analytics", "pages/2_Analytics.py", "Analytics"),
]


def brand() -> None:
    """Logo and name at the top of the sidebar."""
    st.markdown(
        f"<div class='brand'><span class='mark'>{MARK_SVG}</span><div class='wordmark'>LegalAidGPT</div></div>",
        unsafe_allow_html=True,
    )


def nav_links(skip: str = "") -> None:
    """Links to the other pages. skip="home" leaves out the Home link."""
    for key, path, label in NAV:
        if key != skip:
            _link(path, label)


def setup(active: str) -> None:
    """Everything a secondary page needs. Call it right after st.set_page_config().

    active is the page's key from NAV, so that page is highlighted instead of linked.
    """
    inject()
    with st.sidebar:
        brand()
        for key, path, label in NAV:
            if key == active:
                st.markdown(f"<div class='hist-active'>{label}</div>", unsafe_allow_html=True)
            else:
                _link(path, label)
        appearance_picker()


def back_to_home() -> None:
    """The '← Back to home' button at the top of a secondary page."""
    _link("app.py", "← Back to home")


def _link(path: str, label: str) -> None:
    """st.page_link, but a renamed or missing page file is skipped instead of crashing the page."""
    try:
        st.page_link(path, label=label)
    except Exception:
        pass
