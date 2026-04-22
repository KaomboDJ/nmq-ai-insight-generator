"""
NMQ AI Insight Generator — Campaign Intelligence Dashboard
Upload paid media data, select funnel phases, get KPI cards, charts, and AI insights.
"""

import io
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.generator import (
    generate_phase_insights,
    generate_insights_vs_benchmark,
    generate_generic_insights,
    MODEL,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="NMQ AI Insight Generator",
    page_icon="https://nmqdigital.com/favicon.ico",
    layout="wide",
)


# ── Styling ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  .stApp {
    background-color: #f8fafc;
    color: #0f172a;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  [data-testid="stHeader"] {
    background-color: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
  }
  [data-testid="stSidebar"]        { display: none; }
  [data-testid="collapsedControl"] { display: none; }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {
    background-color: #f1f5f9;
    border-radius: 12px;
    padding: 4px;
    gap: 2px;
    border: 1px solid #e2e8f0;
  }
  .stTabs [data-baseweb="tab"] {
    color: #64748b;
    font-size: 13px;
    font-weight: 500;
    border-radius: 8px !important;
    padding: 6px 16px !important;
    transition: all 0.15s ease;
    border: none !important;
  }
  .stTabs [data-baseweb="tab"]:hover {
    color: #0f172a !important;
    background-color: rgba(99, 102, 241, 0.1) !important;
  }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #6366f1 0%, #818cf8 100%) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 12px rgba(99, 102, 241, 0.4) !important;
  }

  /* ── Typography ── */
  h1, h2, h3 {
    color: #0f172a !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em;
  }
  h1 { font-size: 1.6rem !important; }
  h2 { font-size: 1.2rem !important; }
  h3 { font-size: 1rem !important; }
  p, label, span { color: #0f172a !important; }

  /* ── Dataframe ── */
  .stDataFrame {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    overflow: hidden;
  }

  /* ── Divider ── */
  hr {
    border-color: #e2e8f0 !important;
    margin: 16px 0 !important;
    opacity: 0.5;
  }

  /* ── Insights output ── */
  .insights-output {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-left: 3px solid #6366f1;
    border-radius: 12px;
    padding: 24px 28px;
    margin-top: 12px;
    line-height: 1.7;
  }

  /* ── Inputs ── */
  [data-baseweb="input"], [data-baseweb="textarea"] {
    background-color: #ffffff !important;
    border-color: #e2e8f0 !important;
    border-radius: 8px !important;
  }
  [data-baseweb="input"] input,
  [data-baseweb="textarea"] textarea {
    background-color: #ffffff !important;
    color: #0f172a !important;
  }
  [data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border-color: #e2e8f0 !important;
    color: #0f172a !important;
    border-radius: 8px !important;
  }
  [data-baseweb="select"] span { color: #0f172a !important; }
  [data-testid="stFileUploader"],
  [data-testid="stFileUploaderDropzone"],
  [data-testid="stFileUploaderDropzoneInstructions"],
  section[data-testid="stFileUploaderDropzone"] {
    background-color: #ffffff !important;
    border-color: #e2e8f0 !important;
    border-radius: 10px !important;
  }
  [data-testid="stFileUploader"] *,
  [data-testid="stFileUploaderDropzone"] * { color: #0f172a !important; }
  [data-testid="stFileUploaderDropzone"] button,
  [data-testid="stFileUploaderDropzone"] button * {
    background-color: #f1f5f9 !important;
    color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 6px !important;
  }
  [data-baseweb="popover"] ul {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
  }
  [data-baseweb="popover"] li { color: #0f172a !important; }
  [data-baseweb="popover"] li:hover {
    background-color: rgba(99, 102, 241, 0.1) !important;
  }

  /* ── Primary button ── */
  div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #818cf8 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    padding: 10px 24px !important;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35) !important;
  }
  div.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5) !important;
  }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────

PHASE_COLORS = {
    "awareness": "#7F77DD",
    "consideration": "#1D9E75",
    "purchase": "#D85A30",
}

PHASE_LABELS = {
    "awareness": "Awareness",
    "consideration": "Consideration",
    "purchase": "Purchase / Lead",
}

COLUMN_ALIASES = {
    "date":               ["date", "day", "week", "month", "period"],
    "channel":            ["channel", "platform", "network", "source", "medium"],
    "campaign":           ["campaign", "campaign_name", "ad_set", "adset", "ad set"],
    "impressions":        ["impressions", "impr", "impression", "total_impressions"],
    "reach":              ["reach", "unique_reach", "unique_users", "people_reached"],
    "spend":              ["spend", "cost", "amount_spent", "total_cost", "budget_spent"],
    "clicks":             ["clicks", "link_clicks", "total_clicks", "website_clicks"],
    "video_views":        ["video_views", "views", "3s_views", "video_plays", "video views"],
    "video_completions":  ["video_completions", "thruplay", "completed_views", "video completions"],
    "engagements":        ["engagements", "post_engagements", "interactions", "total_engagements"],
    "sessions":           ["sessions", "website_sessions", "ga_sessions"],
    "landing_page_views": ["landing_page_views", "lpv", "lp_views", "landing page views"],
    "bounce_rate":        ["bounce_rate", "bounce rate", "bounces"],
    "conversions":        ["conversions", "results", "purchases", "total_conversions"],
    "leads":              ["leads", "lead_submissions", "form_submissions"],
    "revenue":            ["revenue", "purchase_value", "conversion_value", "total_revenue"],
}

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
        raise ValueError("Could not find a sheet ID in that URL.")
    sheet_id = match.group(1)
    gid_match = re.search(r"[#&?]gid=(\d+)", url)
    gid = gid_match.group(1) if gid_match else "0"
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    out = pd.read_csv(export_url)
    out.columns = [c.strip().lower().replace(" ", "_") for c in out.columns]
    return out.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)


def detect_columns(df: pd.DataFrame) -> dict:
    """Map canonical KPI names to actual column names in the DataFrame."""
    lower_cols = {c.lower(): c for c in df.columns}
    detected = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            norm = alias.lower().replace(" ", "_")
            if norm in lower_cols:
                detected[canonical] = lower_cols[norm]
                break
    return detected


def _sum(df: pd.DataFrame, col: str) -> float | None:
    if col in df.columns:
        v = pd.to_numeric(df[col], errors="coerce").sum()
        return float(v) if v == v else None
    return None


def _avg(df: pd.DataFrame, col: str) -> float | None:
    if col in df.columns:
        v = pd.to_numeric(df[col], errors="coerce").mean()
        return float(v) if v == v else None
    return None


def calculate_kpis(df: pd.DataFrame, col_map: dict) -> dict:
    """Return { phase: { label: (value, fmt) } } for all available KPIs."""
    def s(key):
        col = col_map.get(key)
        return _sum(df, col) if col else None

    def a(key):
        col = col_map.get(key)
        return _avg(df, col) if col else None

    imp   = s("impressions")
    reach = s("reach")
    spend = s("spend")
    clicks = s("clicks")
    vv    = s("video_views")
    vc    = s("video_completions")
    eng   = s("engagements")
    sess  = s("sessions")
    lpv   = s("landing_page_views")
    conv  = s("conversions")
    leads = s("leads")
    rev   = s("revenue")
    br    = a("bounce_rate")

    def safe_div(a, b):
        return a / b if (a is not None and b is not None and b != 0) else None

    kpis = {
        "awareness": {},
        "consideration": {},
        "purchase": {},
    }

    # Awareness
    if imp   is not None: kpis["awareness"]["Impressions"]  = (imp,   "number")
    if reach is not None: kpis["awareness"]["Reach"]        = (reach, "number")
    freq = safe_div(imp, reach)
    if freq  is not None: kpis["awareness"]["Frequency"]    = (freq,  "decimal")
    cpm  = safe_div(spend, imp and imp / 1000)
    if spend is not None and imp is not None and imp > 0:
        kpis["awareness"]["CPM"] = (spend / imp * 1000, "currency")
    if vv    is not None: kpis["awareness"]["Video Views"]  = (vv,    "number")
    vtr = safe_div(vc, vv)
    if vtr   is not None: kpis["awareness"]["VTR"]          = (vtr * 100, "percent")

    # Consideration
    if clicks is not None: kpis["consideration"]["Clicks"] = (clicks, "number")
    ctr = safe_div(clicks, imp)
    if ctr   is not None: kpis["consideration"]["CTR"]     = (ctr * 100, "percent")
    cpc = safe_div(spend, clicks)
    if cpc   is not None: kpis["consideration"]["CPC"]     = (cpc, "currency")
    er  = safe_div(eng, imp)
    if er    is not None: kpis["consideration"]["Engagement Rate"] = (er * 100, "percent")
    if sess  is not None: kpis["consideration"]["Sessions"]        = (sess, "number")
    if lpv   is not None: kpis["consideration"]["Landing Page Views"] = (lpv, "number")
    if br    is not None: kpis["consideration"]["Bounce Rate"]     = (br, "percent")

    # Purchase
    if conv  is not None: kpis["purchase"]["Conversions"] = (conv, "number")
    if leads is not None: kpis["purchase"]["Leads"]       = (leads, "number")
    if rev   is not None: kpis["purchase"]["Revenue"]     = (rev,  "currency")
    roas = safe_div(rev, spend)
    if roas  is not None: kpis["purchase"]["ROAS"]        = (roas, "decimal")
    cpa  = safe_div(spend, conv)
    if cpa   is not None: kpis["purchase"]["CPA"]         = (cpa,  "currency")
    cpl  = safe_div(spend, leads)
    if cpl   is not None: kpis["purchase"]["CPL"]         = (cpl,  "currency")
    cvr  = safe_div(conv, clicks)
    if cvr   is not None: kpis["purchase"]["CVR"]         = (cvr * 100, "percent")

    return kpis


def fmt_val(value: float, fmt: str) -> str:
    if fmt == "number":   return f"{value:,.0f}"
    if fmt == "currency": return f"€{value:,.2f}"
    if fmt == "percent":  return f"{value:.2f}%"
    if fmt == "decimal":  return f"{value:.2f}"
    return str(value)


def render_kpi_section(phases: list, kpis: dict) -> None:
    for phase in phases:
        phase_kpis = kpis.get(phase, {})
        if not phase_kpis:
            continue
        st.markdown(f"#### {PHASE_LABELS[phase]}")
        cols = st.columns(min(len(phase_kpis), 4))
        for i, (name, (value, fmt)) in enumerate(phase_kpis.items()):
            cols[i % 4].metric(name, fmt_val(value, fmt))
        st.write("")


def _style_fig(fig, height: int = 300) -> None:
    """Apply clean, consistent light-theme styling to any Plotly figure."""
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=36, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, -apple-system, sans-serif", color="#0f172a", size=12),
        title_font=dict(size=13, color="#0f172a", family="Inter, sans-serif"),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            font=dict(color="#64748b", size=11),
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            tickfont=dict(color="#64748b", size=11),
            linecolor="#e2e8f0",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.05)",
            zeroline=False,
            tickfont=dict(color="#64748b", size=11),
            linecolor="rgba(0,0,0,0)",
        ),
    )
    fig.update_traces(marker_line_width=0)


def _get_col(df: pd.DataFrame, col_map: dict, key: str) -> pd.Series | None:
    col = col_map.get(key)
    if col and col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return None


def render_charts(phases: list, df: pd.DataFrame, col_map: dict) -> None:
    date_col  = col_map.get("date")
    ch_col    = col_map.get("channel")
    camp_col  = col_map.get("campaign")
    has_date  = date_col and date_col in df.columns
    has_ch    = ch_col and ch_col in df.columns
    has_camp  = camp_col and camp_col in df.columns

    def num(key):
        col = col_map.get(key)
        return col if (col and col in df.columns) else None

    # ── Awareness charts ──────────────────────────────────────────────────────
    if "awareness" in phases:
        st.markdown("#### Awareness Charts")

        imp_col   = num("impressions")
        reach_col = num("reach")
        spend_col = num("spend")

        col_a, col_b = st.columns(2)

        with col_a:
            if has_date and imp_col:
                tmp = df.copy()
                tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
                grp_cols = [date_col] + ([ch_col] if has_ch else [])
                agg = {imp_col: "sum"}
                if reach_col: agg[reach_col] = "sum"
                grp = tmp.groupby(grp_cols, as_index=False).agg(agg)
                y_cols = [c for c in [imp_col, reach_col] if c]
                fig = px.line(grp, x=date_col, y=y_cols,
                              color=ch_col if has_ch and ch_col in grp.columns else None,
                              title="Impressions & Reach Over Time",
                              color_discrete_sequence=[PHASE_COLORS["awareness"], "#b0aae8"])
                fig.update_layout(legend_title_text="")
                _style_fig(fig)
                st.plotly_chart(fig, use_container_width=True)
            elif imp_col:
                st.info("No date column detected — time series unavailable.")

        with col_b:
            if has_ch and imp_col and spend_col:
                tmp = df.copy()
                tmp[imp_col]   = pd.to_numeric(tmp[imp_col], errors="coerce")
                tmp[spend_col] = pd.to_numeric(tmp[spend_col], errors="coerce")
                grp = tmp.groupby(ch_col, as_index=False).agg({imp_col: "sum", spend_col: "sum"})
                grp = grp[grp[imp_col] > 0]
                grp["CPM"] = grp[spend_col] / grp[imp_col] * 1000
                fig = px.bar(grp, x=ch_col, y="CPM", title="CPM by Channel",
                             color_discrete_sequence=[PHASE_COLORS["awareness"]])
                _style_fig(fig)
                st.plotly_chart(fig, use_container_width=True)

        if has_ch and imp_col and reach_col:
            tmp = df.copy()
            tmp[imp_col]   = pd.to_numeric(tmp[imp_col], errors="coerce")
            tmp[reach_col] = pd.to_numeric(tmp[reach_col], errors="coerce")
            grp = tmp.groupby(ch_col, as_index=False).agg({imp_col: "sum", reach_col: "sum"})
            grp = grp[grp[reach_col] > 0]
            grp["Frequency"] = grp[imp_col] / grp[reach_col]
            fig = px.bar(grp, x=ch_col, y="Frequency", title="Frequency by Channel",
                         color_discrete_sequence=[PHASE_COLORS["awareness"]])
            fig.add_hline(y=5, line_dash="dash", line_color="red",
                          annotation_text="Overexposure warning (>5)")
            _style_fig(fig)
            st.plotly_chart(fig, use_container_width=True)

    # ── Consideration charts ──────────────────────────────────────────────────
    if "consideration" in phases:
        st.markdown("#### Consideration Charts")

        clicks_col = num("clicks")
        imp_col    = num("impressions")
        spend_col  = num("spend")
        eng_col    = num("engagements")

        col_a, col_b = st.columns(2)

        with col_a:
            if has_date and clicks_col and imp_col:
                tmp = df.copy()
                tmp[date_col]   = pd.to_datetime(tmp[date_col], errors="coerce")
                tmp[clicks_col] = pd.to_numeric(tmp[clicks_col], errors="coerce")
                tmp[imp_col]    = pd.to_numeric(tmp[imp_col], errors="coerce")
                grp_cols = [date_col] + ([ch_col] if has_ch else [])
                grp = tmp.groupby(grp_cols, as_index=False).agg({clicks_col: "sum", imp_col: "sum"})
                grp = grp[grp[imp_col] > 0]
                grp["CTR (%)"] = grp[clicks_col] / grp[imp_col] * 100
                fig = px.line(grp, x=date_col, y="CTR (%)",
                              color=ch_col if has_ch and ch_col in grp.columns else None,
                              title="CTR Over Time by Channel",
                              color_discrete_sequence=[PHASE_COLORS["consideration"]])
                fig.update_layout(legend_title_text="")
                _style_fig(fig)
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            if has_camp and spend_col and clicks_col:
                tmp = df.copy()
                tmp[spend_col]  = pd.to_numeric(tmp[spend_col], errors="coerce")
                tmp[clicks_col] = pd.to_numeric(tmp[clicks_col], errors="coerce")
                grp = tmp.groupby(camp_col, as_index=False).agg({spend_col: "sum", clicks_col: "sum"})
                grp = grp[grp[clicks_col] > 0]
                grp["CPC"] = grp[spend_col] / grp[clicks_col]
                grp = grp.sort_values("CPC", ascending=False)
                fig = px.bar(grp, x=camp_col, y="CPC", title="CPC by Campaign (high to low)",
                             color_discrete_sequence=[PHASE_COLORS["consideration"]])
                fig.update_layout(xaxis_tickangle=-30)
                _style_fig(fig)
                st.plotly_chart(fig, use_container_width=True)

        if has_ch and eng_col and imp_col:
            tmp = df.copy()
            tmp[eng_col] = pd.to_numeric(tmp[eng_col], errors="coerce")
            tmp[imp_col] = pd.to_numeric(tmp[imp_col], errors="coerce")
            grp = tmp.groupby(ch_col, as_index=False).agg({eng_col: "sum", imp_col: "sum"})
            grp = grp[grp[imp_col] > 0]
            grp["Engagement Rate (%)"] = grp[eng_col] / grp[imp_col] * 100
            fig = px.bar(grp, x=ch_col, y="Engagement Rate (%)", title="Engagement Rate by Channel",
                         color_discrete_sequence=[PHASE_COLORS["consideration"]])
            _style_fig(fig)
            st.plotly_chart(fig, use_container_width=True)

    # ── Purchase / Lead charts ────────────────────────────────────────────────
    if "purchase" in phases:
        st.markdown("#### Purchase / Lead Charts")

        conv_col  = num("conversions")
        rev_col   = num("revenue")
        spend_col = num("spend")
        clicks_col = num("clicks")
        imp_col   = num("impressions")

        col_a, col_b = st.columns(2)

        with col_a:
            if has_date and conv_col:
                tmp = df.copy()
                tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
                tmp[conv_col] = pd.to_numeric(tmp[conv_col], errors="coerce")
                y_cols = [conv_col]
                if rev_col:
                    tmp[rev_col] = pd.to_numeric(tmp[rev_col], errors="coerce")
                    y_cols.append(rev_col)
                grp = tmp.groupby(date_col, as_index=False)[y_cols].sum()
                fig = px.line(grp, x=date_col, y=y_cols, title="Conversions & Revenue Over Time",
                              color_discrete_sequence=[PHASE_COLORS["purchase"], "#e8956e"])
                fig.update_layout(legend_title_text="")
                _style_fig(fig)
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            if has_camp and rev_col and spend_col:
                tmp = df.copy()
                tmp[rev_col]   = pd.to_numeric(tmp[rev_col], errors="coerce")
                tmp[spend_col] = pd.to_numeric(tmp[spend_col], errors="coerce")
                grp = tmp.groupby(camp_col, as_index=False).agg({rev_col: "sum", spend_col: "sum"})
                grp = grp[grp[spend_col] > 0]
                grp["ROAS"] = grp[rev_col] / grp[spend_col]
                fig = px.bar(grp, x=camp_col, y="ROAS", title="ROAS by Campaign",
                             color_discrete_sequence=[PHASE_COLORS["purchase"]])
                fig.add_hline(y=1, line_dash="dash", line_color="red",
                              annotation_text="Break-even (ROAS = 1)")
                fig.add_hline(y=3, line_dash="dash", line_color="green",
                              annotation_text="Target (ROAS = 3)")
                fig.update_layout(xaxis_tickangle=-30)
                _style_fig(fig)
                st.plotly_chart(fig, use_container_width=True)

        # Funnel drop-off
        imp_total  = _sum(df, imp_col)   if imp_col   else None
        clk_total  = _sum(df, clicks_col) if clicks_col else None
        conv_total = _sum(df, conv_col)  if conv_col  else None
        funnel_data = [(s, v) for s, v in [("Impressions", imp_total), ("Clicks", clk_total), ("Conversions", conv_total)] if v is not None and v > 0]
        if len(funnel_data) >= 2:
            stages, values = zip(*funnel_data)
            pcts = [100.0] + [round(values[i] / values[0] * 100, 1) for i in range(1, len(values))]
            fig = go.Figure(go.Funnel(
                y=list(stages),
                x=list(values),
                textinfo="value+percent previous",
                marker_color=[PHASE_COLORS["awareness"], PHASE_COLORS["consideration"], PHASE_COLORS["purchase"]][:len(stages)],
            ))
            fig.update_layout(title="Funnel: Impressions → Clicks → Conversions")
            _style_fig(fig, height=320)
            st.plotly_chart(fig, use_container_width=True)

    # ── Cross-phase normalised timeline ───────────────────────────────────────
    if len(phases) >= 2 and has_date:
        st.markdown("**Cross-phase performance timeline** (normalised 0–100)", unsafe_allow_html=False)
        primary = {"awareness": "impressions", "consideration": "clicks", "purchase": "conversions"}
        tmp = df.copy()
        tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
        timeline_df = pd.DataFrame()
        for phase in phases:
            key = primary.get(phase)
            col = num(key) if key else None
            if col:
                tmp[col] = pd.to_numeric(tmp[col], errors="coerce")
                grp = tmp.groupby(date_col, as_index=False)[col].sum()
                if grp[col].max() > 0:
                    grp[PHASE_LABELS[phase]] = grp[col] / grp[col].max() * 100
                    if timeline_df.empty:
                        timeline_df = grp[[date_col, PHASE_LABELS[phase]]]
                    else:
                        timeline_df = timeline_df.merge(grp[[date_col, PHASE_LABELS[phase]]], on=date_col, how="outer")
        if not timeline_df.empty:
            y_cols = [PHASE_LABELS[p] for p in phases if PHASE_LABELS[p] in timeline_df.columns]
            fig = px.line(timeline_df, x=date_col, y=y_cols, title="Normalised Performance by Phase",
                          color_discrete_sequence=[PHASE_COLORS[p] for p in phases])
            fig.update_layout(legend_title_text="", yaxis_title="Index (0–100)")
            _style_fig(fig)
            st.plotly_chart(fig, use_container_width=True)


def render_insights_panel(df: pd.DataFrame, state_key: str, phases: list, kpis: dict) -> None:
    st.subheader("AI Insights")

    bench_key = f"bench_{state_key}"
    with st.expander("Add benchmark / media plan (optional)"):
        bench_file = st.file_uploader(
            "Upload benchmark file (Excel or CSV)",
            type=["xlsx", "xls", "csv"],
            key=f"bench_upload_{state_key}",
        )
        if bench_file is not None:
            df_bench = load_file(bench_file.read(), bench_file.name)
            st.session_state[bench_key] = df_bench
            st.success(f"Benchmark loaded: **{len(df_bench):,} rows** × **{len(df_bench.columns)} columns**.")
        elif bench_key in st.session_state:
            st.info("Benchmark already loaded. Upload a new file to replace it.")

    df_benchmark = st.session_state.get(bench_key)
    has_benchmark = df_benchmark is not None

    deep_mode = st.toggle(
        "Deep mode (Sonnet)",
        value=False,
        key=f"deep_{state_key}",
        help="Uses claude-sonnet-4-6 instead of Haiku — slower but more thorough.",
    )
    model_to_use = "claude-sonnet-4-6" if deep_mode else MODEL

    if phases:
        btn_label = "Generate insights vs benchmark" if has_benchmark else "Generate phase insights"
    else:
        btn_label = "Generate insights"

    col_btn, _ = st.columns([2, 3])
    with col_btn:
        generate  = st.button(btn_label, type="primary", key=f"gen_{state_key}")
        regenerate = st.button("Regenerate", key=f"regen_{state_key}")

    if generate or regenerate:
        with st.spinner("Claude is thinking..."):
            if has_benchmark:
                result = generate_insights_vs_benchmark(df, df_benchmark, model=model_to_use)
            elif phases and kpis:
                kpi_summary = {
                    phase: {name: fmt_val(value, fmt) for name, (value, fmt) in kpis.get(phase, {}).items()}
                    for phase in phases
                }
                result = generate_phase_insights(phases, kpi_summary, model=model_to_use)
            else:
                result = generate_generic_insights(df, model=model_to_use)
        st.session_state[state_key] = result

    if state_key in st.session_state:
        st.markdown(st.session_state[state_key])


# ── Header ────────────────────────────────────────────────────────────────────

st.title("NMQ AI Insight Generator")
st.caption("Upload your data, pick your funnel phases, get KPIs, charts, and AI insights.")

st.divider()

# ── Data source tabs ──────────────────────────────────────────────────────────

tab_upload, tab_sheets = st.tabs(["Upload file", "Google Sheet"])

with tab_upload:
    uploaded = st.file_uploader(
        "Upload your data file (Excel or CSV)",
        type=["xlsx", "xls", "csv"],
    )
    if uploaded is not None:
        df_file = load_file(uploaded.read(), uploaded.name)
        source_label = uploaded.name

        st.success(f"Loaded **{len(df_file):,} rows** × **{len(df_file.columns)} columns** from `{source_label}`.")
        with st.expander("Preview data (first 10 rows)"):
            st.dataframe(df_file.head(10), use_container_width=True)

        st.divider()

        # ── Phase selector ────────────────────────────────────────────────────
        st.subheader("Funnel Phases")
        pc1, pc2, pc3, pc_all = st.columns([2, 2, 2, 1])
        with pc1:
            aw_file = st.toggle("🟣 Awareness",       value=True, key="aw_file")
        with pc2:
            co_file = st.toggle("🟢 Consideration",   value=True, key="co_file")
        with pc3:
            pu_file = st.toggle("🟠 Purchase / Lead", value=True, key="pu_file")
        with pc_all:
            st.write("")
            if st.button("All", key="all_file"):
                st.session_state["aw_file"] = True
                st.session_state["co_file"] = True
                st.session_state["pu_file"] = True
                st.rerun()

        active_phases_file = [p for p, on in [("awareness", aw_file), ("consideration", co_file), ("purchase", pu_file)] if on]

        if not active_phases_file:
            st.warning("Select at least one funnel phase to see the dashboard.")
        else:
            col_map = detect_columns(df_file)
            kpis    = calculate_kpis(df_file, col_map)

            with st.expander(f"Detected columns ({len(col_map)} matched)"):
                st.write(", ".join(f"`{k}` → `{v}`" for k, v in col_map.items()))

            st.divider()
            st.subheader("KPIs")
            render_kpi_section(active_phases_file, kpis)

            st.divider()
            st.subheader("Charts")
            render_charts(active_phases_file, df_file, col_map)

            st.divider()
            render_insights_panel(df_file, "insight_file", active_phases_file, kpis)
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
            st.success(f"Loaded **{len(df_sheet):,} rows** × **{len(df_sheet.columns)} columns** from Google Sheet.")
            with st.expander("Preview data (first 10 rows)"):
                st.dataframe(df_sheet.head(10), use_container_width=True)

            st.divider()

            # ── Phase selector ────────────────────────────────────────────────
            st.subheader("Funnel Phases")
            ps1, ps2, ps3, ps_all = st.columns([2, 2, 2, 1])
            with ps1:
                aw_sheet = st.toggle("🟣 Awareness",       value=True, key="aw_sheet")
            with ps2:
                co_sheet = st.toggle("🟢 Consideration",   value=True, key="co_sheet")
            with ps3:
                pu_sheet = st.toggle("🟠 Purchase / Lead", value=True, key="pu_sheet")
            with ps_all:
                st.write("")
                if st.button("All", key="all_sheet"):
                    st.session_state["aw_sheet"] = True
                    st.session_state["co_sheet"] = True
                    st.session_state["pu_sheet"] = True
                    st.rerun()

            active_phases_sheet = [p for p, on in [("awareness", aw_sheet), ("consideration", co_sheet), ("purchase", pu_sheet)] if on]

            if not active_phases_sheet:
                st.warning("Select at least one funnel phase to see the dashboard.")
            else:
                col_map = detect_columns(df_sheet)
                kpis    = calculate_kpis(df_sheet, col_map)

                with st.expander(f"Detected columns ({len(col_map)} matched)"):
                    st.write(", ".join(f"`{k}` → `{v}`" for k, v in col_map.items()))

                st.divider()
                st.subheader("KPIs")
                render_kpi_section(active_phases_sheet, kpis)

                st.divider()
                st.subheader("Charts")
                render_charts(active_phases_sheet, df_sheet, col_map)

                st.divider()
                render_insights_panel(df_sheet, "insight_sheet", active_phases_sheet, kpis)

        except Exception as e:
            st.error(f"Could not load the sheet: {e}")
    else:
        st.info("Paste a Google Sheet URL to get started.")
