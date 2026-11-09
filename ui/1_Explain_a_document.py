"""Explain a legal document in plain language."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from assistant import config
from assistant.pipeline import explain_document
from ui import theme

st.set_page_config(page_title="Explain a document", page_icon="📄", layout="wide")
theme.setup("doc")       # shared look and sidebar links (see ui/theme.py)
theme.back_to_home()       # the "← Back to home" button
st.title("Explain a document")
st.caption("Paste text or upload a file and get a plain-language explanation.")
st.info("Please do not include ID numbers, bank details or other sensitive personal information.")

uploaded = st.file_uploader("Upload a file", type=["txt", "pdf"])
text = ""

if uploaded is not None:
    if uploaded.name.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader

            reader = PdfReader(uploaded)
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            if not text.strip():
                st.warning("This PDF has no readable text. It may be a scan, which needs OCR.")
        except ImportError:
            st.error("PDF support needs the pypdf package. Run: pip install pypdf")
    else:
        text = uploaded.read().decode("utf-8", errors="ignore")

text = st.text_area("Or paste the text here", value=text, height=240)

if st.button("Explain in plain language", type="primary", disabled=not text.strip()):
    with st.spinner("Reading the document..."):
        result = explain_document(text)
    st.markdown(result["answer"])
    for w in result["warnings"]:
        st.warning(w)
    st.caption(config.DISCLAIMER)
