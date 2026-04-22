"""
NMQ AI Insight Generator
Standalone Streamlit app — upload an Excel/CSV, get Claude-powered paid media insights.
"""

import io
import pandas as pd
import streamlit as st

from src.generator import generate_insights, generate_comparison, MODEL

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
    st.caption("Upload your paid media export and let Claude do the heavy lifting.")

st.divider()

# ── Required columns ─────────────────────────────────────────────────────────

REQUIRED_COLS = {"date", "spend"}
OPTIONAL_COLS = {"impressions", "clicks", "engagements", "channel", "market",
                 "funnel_stage", "campaign_name", "platform"}

# ── File upload ───────────────────────────────────────────────────────────────

uploaded = st.file_uploader(
    "Upload your data file (Excel or CSV)",
    type=["xlsx", "xls", "csv"],
    help="Must include at least a 'date' column and a 'spend' column. See template for the full column list.",
)

if uploaded is None:
    st.info("Upload a file to get started. Download the template below if you need a starting point.")

    template_cols = [
        "date", "spend", "impressions", "clicks", "engagements",
        "channel", "market", "funnel_stage", "campaign_name", "platform",
    ]
    template_df = pd.DataFrame(columns=template_cols)
    buf = io.BytesIO()
    template_df.to_excel(buf, index=False)
    buf.seek(0)
    st.download_button(
        label="Download template (.xlsx)",
        data=buf,
        file_name="nmq_paid_media_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Reading file...")
def load_file(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    if file_name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        df = pd.read_excel(io.BytesIO(file_bytes))

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    numeric_cols = ["spend", "impressions", "clicks", "engagements",
                    "link_clicks", "landing_page_views", "video_plays"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", ""), errors="coerce"
            ).fillna(0)

    return df


file_bytes = uploaded.read()
df_raw = load_file(file_bytes, uploaded.name)

missing = REQUIRED_COLS - set(df_raw.columns)
if missing:
    st.error(f"Missing required columns: {', '.join(missing)}. Check your file against the template.")
    st.stop()

detected = OPTIONAL_COLS & set(df_raw.columns)
st.success(
    f"Loaded **{len(df_raw):,} rows** from `{uploaded.name}`. "
    f"Detected columns: {', '.join(sorted(detected | REQUIRED_COLS))}."
)

# ── Filters ───────────────────────────────────────────────────────────────────

st.subheader("Filters")

filter_cols = st.columns(4)

with filter_cols[0]:
    if "date" in df_raw.columns:
        min_date = df_raw["date"].min().date()
        max_date = df_raw["date"].max().date()
        date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    else:
        date_range = None

with filter_cols[1]:
    if "platform" in df_raw.columns:
        platforms = ["All"] + sorted(df_raw["platform"].dropna().unique().tolist())
        sel_platform = st.selectbox("Platform", platforms)
    else:
        sel_platform = "All"

with filter_cols[2]:
    if "market" in df_raw.columns:
        markets = ["All"] + sorted(df_raw["market"].dropna().unique().tolist())
        sel_market = st.selectbox("Market", markets)
    else:
        sel_market = "All"

with filter_cols[3]:
    if "channel" in df_raw.columns:
        channels = ["All"] + sorted(df_raw["channel"].dropna().unique().tolist())
        sel_channel = st.selectbox("Channel", channels)
    else:
        sel_channel = "All"

# Apply filters
df = df_raw.copy()

if date_range and len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    df = df[(df["date"] >= start) & (df["date"] <= end)]

if sel_platform != "All" and "platform" in df.columns:
    df = df[df["platform"] == sel_platform]

if sel_market != "All" and "market" in df.columns:
    df = df[df["market"] == sel_market]

if sel_channel != "All" and "channel" in df.columns:
    df = df[df["channel"] == sel_channel]

st.caption(f"{len(df):,} rows after filters.")

st.divider()

# ── Metrics overview ──────────────────────────────────────────────────────────

st.subheader("Overview")

m1, m2, m3, m4, m5 = st.columns(5)
total_spend  = df["spend"].sum()       if "spend"       in df.columns else 0
total_impr   = df["impressions"].sum() if "impressions" in df.columns else 0
total_clicks = df["clicks"].sum()      if "clicks"      in df.columns else 0
ctr = (total_clicks / total_impr * 100) if total_impr else 0
cpc = (total_spend / total_clicks)      if total_clicks else 0

m1.metric("Spend",       f"€{total_spend:,.2f}")
m2.metric("Impressions", f"{total_impr:,.0f}")
m3.metric("Clicks",      f"{total_clicks:,.0f}")
m4.metric("CTR",         f"{ctr:.2f}%")
m5.metric("CPC",         f"€{cpc:.2f}")

st.divider()

# ── AI Insights ───────────────────────────────────────────────────────────────

st.subheader("AI Insights")

mode = st.radio("Mode", ["Single period", "Period comparison"], horizontal=True)
deep_mode = st.toggle("Deep mode (Sonnet)", value=False, help="Uses claude-sonnet-4-6 instead of Haiku — slower but more thorough.")
model_to_use = "claude-sonnet-4-6" if deep_mode else MODEL

filters_dict = {
    "platform":     sel_platform,
    "market":       sel_market,
    "channel":      sel_channel,
}

cache_key = f"{uploaded.name}|{date_range}|{sel_platform}|{sel_market}|{sel_channel}|{mode}|{deep_mode}"

if mode == "Single period":
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        generate = st.button("Generate insights", type="primary")
        regenerate = st.button("Regenerate", help="Force a fresh response from Claude.")

    if generate or regenerate:
        if df.empty:
            st.warning("No data matches the current filters.")
        else:
            with st.spinner("Claude is thinking..."):
                result = generate_insights(df, filters_dict, model=model_to_use)
            st.session_state["insight_result"] = result
            st.session_state["insight_key"] = cache_key

    if "insight_result" in st.session_state:
        st.markdown(st.session_state["insight_result"])

else:
    st.markdown("Pick two date windows to compare.")
    ca, cb = st.columns(2)
    with ca:
        date_a = st.date_input("Period A", key="date_a",
                               value=(df_raw["date"].min().date(), df_raw["date"].max().date()))
    with cb:
        date_b = st.date_input("Period B", key="date_b",
                               value=(df_raw["date"].min().date(), df_raw["date"].max().date()))

    col_btn2, _ = st.columns([1, 4])
    with col_btn2:
        compare = st.button("Compare periods", type="primary")

    if compare:
        df_a = df_raw.copy()
        df_b = df_raw.copy()

        if len(date_a) == 2:
            df_a = df_a[(df_a["date"] >= pd.Timestamp(date_a[0])) & (df_a["date"] <= pd.Timestamp(date_a[1]))]
        if len(date_b) == 2:
            df_b = df_b[(df_b["date"] >= pd.Timestamp(date_b[0])) & (df_b["date"] <= pd.Timestamp(date_b[1]))]

        if sel_platform != "All" and "platform" in df_a.columns:
            df_a = df_a[df_a["platform"] == sel_platform]
            df_b = df_b[df_b["platform"] == sel_platform]

        if sel_market != "All" and "market" in df_a.columns:
            df_a = df_a[df_a["market"] == sel_market]
            df_b = df_b[df_b["market"] == sel_market]

        if df_a.empty and df_b.empty:
            st.warning("No data for either period.")
        else:
            with st.spinner("Claude is thinking..."):
                result = generate_comparison(df_a, df_b, filters_dict, model=model_to_use)
            st.session_state["compare_result"] = result

    if "compare_result" in st.session_state:
        st.markdown(st.session_state["compare_result"])
