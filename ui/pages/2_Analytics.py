"""Usage analytics built from the query log (no question text is stored)."""
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from assistant import config
from ui import theme

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
theme.setup("analytics")       # shared look and sidebar links (see ui/theme.py)
theme.back_to_home()       # the "← Back to home" button
st.title("Analytics")
st.caption("Counts and timings only. Question text is never stored.")


def load_log() -> pd.DataFrame:
    if not config.LOG_PATH.exists():
        return pd.DataFrame()
    rows = []
    with open(config.LOG_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    df = pd.DataFrame(rows)
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"])
    return df


def add_sample_data(n: int = 60) -> None:
    topics = [t for t in config.TOPICS.values() if t] + ["all"]
    config.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    with open(config.LOG_PATH, "a", encoding="utf-8") as f:
        for _ in range(n):
            grounded = random.random() > 0.2
            refused = (not grounded) and random.random() < 0.3
            ev = {
                "ts": (now - timedelta(days=random.randint(0, 13), hours=random.randint(0, 23))).isoformat(timespec="seconds"),
                "topic": random.choice(topics), "grounded": grounded, "refused": refused,
                "urgent": random.random() < 0.15, "n_chunks": random.randint(1, 4) if grounded else 0,
                "retrieval_ms": random.randint(20, 150),
                "generation_ms": random.randint(2000, 9000) if grounded else 0,
                "synthetic": True,
            }
            ev["latency_ms"] = ev["retrieval_ms"] + ev["generation_ms"]
            f.write(json.dumps(ev) + "\n")


def remove_sample_data() -> None:
    if not config.LOG_PATH.exists():
        return
    keep = []
    with open(config.LOG_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                if not json.loads(line).get("synthetic"):
                    keep.append(line)
            except json.JSONDecodeError:
                continue
    config.LOG_PATH.write_text("".join(keep), encoding="utf-8")


c1, c2, _ = st.columns([1, 1, 3])
if c1.button("Add sample data"):
    add_sample_data()
    st.rerun()
if c2.button("Remove sample data"):
    remove_sample_data()
    st.rerun()

df = load_log()
if df.empty:
    st.info("No questions logged yet. Ask something on the main page, or add sample data to preview the charts.")
    st.stop()

if "synthetic" in df.columns and df["synthetic"].fillna(False).any():
    st.warning("This view includes synthetic sample data.")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Questions", len(df))
m2.metric("Answered from sources", f"{df['grounded'].mean():.0%}")
m3.metric("Refused", int(df["refused"].fillna(False).sum()))
m4.metric("Median response time", f"{df['latency_ms'].median() / 1000:.1f} s")

left, right = st.columns(2)
with left:
    st.subheader("Questions by topic")
    st.bar_chart(df["topic"].value_counts())
with right:
    st.subheader("Questions per day")
    st.line_chart(df.set_index("ts").resample("D").size())

st.subheader("Response time per stage (average, ms)")
stages = df[["retrieval_ms", "generation_ms"]].mean().fillna(0)
st.bar_chart(stages)

st.subheader("Outcomes")
outcome = pd.Series({
    "Answered from sources": int(df["grounded"].sum()),
    "Not covered": int((~df["grounded"] & ~df["refused"].fillna(False)).sum()),
    "Refused": int(df["refused"].fillna(False).sum()),
})
st.bar_chart(outcome)
