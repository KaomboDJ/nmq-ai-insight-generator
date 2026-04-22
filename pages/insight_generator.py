"""
NMQ AI Insight Generator — Generic
Upload any CSV or Excel file and get Claude-powered insights.
"""

import io
import pandas as pd
import streamlit as st

from src.generator import generate_generic_insights, MODEL

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="NMQ AI Insight Generator",
    page_icon="https://nmqdigital.com/favicon.ico",
    layout="wide",
)

# ── Styling ───────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0f172a; color: #e2e8f0; }
    [data-testid="stHeader"] { background-color: transparent; }
    [data-testid="stSidebar"] { background-color: #1e293b; }
    h1, h2, h3 { color: #f8fafc; }
    .stButton > button {
        background-color: #6366f1;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton > button:hover { background-color: #4f46e5; color: white; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ────────────────────────────────────────────────────────────────────

col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image(
        "https://nmqdigital.com/hs-fs/hubfs/nmq-digital-logo.png?width=294&height=116&name=nmq-digital-logo.png",
        width=160,
    )
with col_title:
    st.title("NMQ AI Insight Generator")
    st.caption("Upload any data file and let Claude find what matters.")

st.divider()

# ── File upload ───────────────────────────────────────────────────────────────

uploaded = st.file_uploader(
    "Upload your data file (Excel or CSV)",
    type=["xlsx", "xls", "csv"],
)

if uploaded is None:
    st.info("Upload a file to get started.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Reading file...")
def load_file(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    if file_name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        df = pd.read_excel(io.BytesIO(file_bytes))
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


file_bytes = uploaded.read()
df = load_file(file_bytes, uploaded.name)

st.success(
    f"Loaded **{len(df):,} rows** and **{len(df.columns)} columns** from `{uploaded.name}`."
)

with st.expander("Preview data (first 10 rows)"):
    st.dataframe(df.head(10), use_container_width=True)

st.divider()

# ── AI Insights ───────────────────────────────────────────────────────────────

st.subheader("AI Insights")

deep_mode = st.toggle(
    "Deep mode (Sonnet)",
    value=False,
    help="Uses claude-sonnet-4-6 instead of Haiku — slower but more thorough.",
)
model_to_use = "claude-sonnet-4-6" if deep_mode else MODEL

col_btn, _ = st.columns([1, 4])
with col_btn:
    generate = st.button("Generate insights", type="primary")
    regenerate = st.button("Regenerate", help="Force a fresh response from Claude.")

if generate or regenerate:
    with st.spinner("Claude is thinking..."):
        result = generate_generic_insights(df, model=model_to_use)
    st.session_state["generic_insight_result"] = result

if "generic_insight_result" in st.session_state:
    st.markdown(st.session_state["generic_insight_result"])
