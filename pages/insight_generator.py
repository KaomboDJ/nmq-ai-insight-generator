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
    [data-testid="stAppViewContainer"] { background-color: #ffffff; color: #111111; }
    [data-testid="stHeader"] { background-color: transparent; }
    [data-testid="stSidebar"] { background-color: #f5f5f5; }
    h1, h2, h3 { color: #000000; }
    .stButton > button {
        background-color: #E8531F;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton > button:hover { background-color: #c94418; color: white; }
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

# ── Data source ───────────────────────────────────────────────────────────────

tab_upload, tab_sheets = st.tabs(["Upload file", "Google Sheet"])

df = None
source_label = ""

with tab_upload:
    uploaded = st.file_uploader(
        "Upload your data file (Excel or CSV)",
        type=["xlsx", "xls", "csv"],
    )

    @st.cache_data(show_spinner="Reading file...")
    def load_file(file_bytes: bytes, file_name: str) -> pd.DataFrame:
        if file_name.endswith(".csv"):
            out = pd.read_csv(io.BytesIO(file_bytes))
        else:
            out = pd.read_excel(io.BytesIO(file_bytes))
        out.columns = [c.strip().lower().replace(" ", "_") for c in out.columns]
        return out

    if uploaded is not None:
        df = load_file(uploaded.read(), uploaded.name)
        source_label = uploaded.name

with tab_sheets:
    st.caption("The sheet must be shared as **Anyone with the link can view**.")
    sheet_url = st.text_input("Paste your Google Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/...")

    @st.cache_data(show_spinner="Loading sheet...")
    def load_sheet(url: str) -> pd.DataFrame:
        import re
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
        if not match:
            raise ValueError("Could not find a sheet ID in that URL. Make sure you paste the full Google Sheets link.")
        sheet_id = match.group(1)
        gid_match = re.search(r"[#&?]gid=(\d+)", url)
        gid = gid_match.group(1) if gid_match else "0"
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        out = pd.read_csv(export_url)
        out.columns = [c.strip().lower().replace(" ", "_") for c in out.columns]
        return out

    if sheet_url:
        try:
            df = load_sheet(sheet_url)
            source_label = "Google Sheet"
        except Exception as e:
            st.error(f"Could not load the sheet: {e}")
            df = None

if df is None:
    st.info("Upload a file or paste a Google Sheet URL to get started.")
    st.stop()

st.success(
    f"Loaded **{len(df):,} rows** and **{len(df.columns)} columns** from `{source_label}`."
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
