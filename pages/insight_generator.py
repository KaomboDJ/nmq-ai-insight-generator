"""
NMQ AI Insight Generator — Generic
Upload any CSV or Excel file and get Claude-powered insights.
"""

import io
import re
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
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    h1, h2, h3 { color: #000000; }
    .stButton > button,
    button[kind="primary"],
    button[kind="secondary"] {
        background-color: #E8531F !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover,
    button[kind="primary"]:hover,
    button[kind="secondary"]:hover {
        background-color: #c94418 !important;
        color: white !important;
    }
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

# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Reading file...")
def load_file(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    if file_name.endswith(".csv"):
        out = pd.read_csv(io.BytesIO(file_bytes))
    else:
        out = pd.read_excel(io.BytesIO(file_bytes))
    out.columns = [c.strip().lower().replace(" ", "_") for c in out.columns]
    return out.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)


@st.cache_data(show_spinner="Loading sheet...")
def load_sheet(url: str) -> pd.DataFrame:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        raise ValueError("Could not find a sheet ID in that URL. Make sure you paste the full Google Sheets link.")
    sheet_id = match.group(1)
    gid_match = re.search(r"[#&?]gid=(\d+)", url)
    gid = gid_match.group(1) if gid_match else "0"
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    out = pd.read_csv(export_url)
    out.columns = [c.strip().lower().replace(" ", "_") for c in out.columns]
    return out.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)


def render_insights_panel(df: pd.DataFrame, state_key: str) -> None:
    st.subheader("AI Insights")
    deep_mode = st.toggle(
        "Deep mode (Sonnet)",
        value=False,
        key=f"deep_{state_key}",
        help="Uses claude-sonnet-4-6 instead of Haiku — slower but more thorough.",
    )
    model_to_use = "claude-sonnet-4-6" if deep_mode else MODEL

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        generate = st.button("Generate insights", type="primary", key=f"gen_{state_key}")
        regenerate = st.button("Regenerate", key=f"regen_{state_key}", help="Force a fresh response from Claude.")

    if generate or regenerate:
        with st.spinner("Claude is thinking..."):
            result = generate_generic_insights(df, model=model_to_use)
        st.session_state[state_key] = result

    if state_key in st.session_state:
        st.markdown(st.session_state[state_key])


# ── Data source tabs ──────────────────────────────────────────────────────────

tab_upload, tab_sheets = st.tabs(["Upload file", "Google Sheet"])

with tab_upload:
    uploaded = st.file_uploader(
        "Upload your data file (Excel or CSV)",
        type=["xlsx", "xls", "csv"],
    )

    if uploaded is not None:
        df_file = load_file(uploaded.read(), uploaded.name)
        st.success(f"Loaded **{len(df_file):,} rows** and **{len(df_file.columns)} columns** from `{uploaded.name}`.")
        with st.expander("Preview data (first 10 rows)"):
            st.dataframe(df_file.head(10), use_container_width=True)
        st.divider()
        render_insights_panel(df_file, state_key="insight_file")
    else:
        st.info("Upload a file to get started.")

with tab_sheets:
    st.caption("The sheet must be shared as **Anyone with the link can view**.")
    sheet_url = st.text_input(
        "Paste your Google Sheet URL",
        placeholder="https://docs.google.com/spreadsheets/d/...",
    )

    if sheet_url:
        try:
            df_sheet = load_sheet(sheet_url)
            st.success(f"Loaded **{len(df_sheet):,} rows** and **{len(df_sheet.columns)} columns** from Google Sheet.")
            with st.expander("Preview data (first 10 rows)"):
                st.dataframe(df_sheet.head(10), use_container_width=True)
            st.divider()
            render_insights_panel(df_sheet, state_key="insight_sheet")
        except Exception as e:
            st.error(f"Could not load the sheet: {e}")
    else:
        st.info("Paste a Google Sheet URL to get started.")
