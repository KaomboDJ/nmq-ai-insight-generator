"""
AI Insights generator — NMQ AI Insight Generator (generic, multi-client).

Summarizes the uploaded DataFrame into a compact structure and sends it
to the Claude API for campaign optimization analysis.

Supports two modes:
  - Single period: performance review + recommendations
  - Period comparison: side-by-side analysis of two date ranges

Model defaults to claude-haiku-4-5 for speed. Pass model="claude-sonnet-4-6"
for a deeper analysis.
"""

import anthropic
import pandas as pd
import streamlit as st

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are a senior paid media strategist with deep expertise in
Facebook, Instagram, YouTube, and Google Ads campaign optimization.

You are analyzing campaign performance data for a brand running paid media
across one or more markets.

When given performance data, you will:
1. Identify what is performing well and why
2. Flag what needs immediate attention (underperformers, inefficiencies, budget misallocations)
3. Give specific, actionable recommendations — not generic advice

Be direct and concrete. Reference actual numbers from the data. Prioritize your recommendations
by impact. Format your response with clear sections using markdown headers.

Never say "based on the data provided" — just state the insight directly."""

COMPARISON_SYSTEM_PROMPT = """You are a senior paid media strategist with deep expertise in
Facebook, Instagram, YouTube, and Google Ads campaign optimization.

You are comparing two performance periods for a brand running paid media
across one or more markets.

When given two periods of data, you will:
1. Summarize the key metric changes (what went up, what went down, by how much)
2. Identify what drove the changes — product mix, channel shifts, market differences
3. Flag anything that needs immediate attention based on the trend
4. Give specific, actionable recommendations for the next period

Be direct and concrete. Reference actual numbers and percentage changes.
Use arrows (↑ ↓ →) to indicate direction of change. Format clearly with markdown headers.

Never say "based on the data provided" — just state the insight directly."""


def _build_period_summary(df: pd.DataFrame, label: str) -> str:
    if df.empty:
        return f"### {label}\nNo data available.\n"

    total_spend       = df["spend"].sum()          if "spend"       in df.columns else 0
    total_impressions = df["impressions"].sum()     if "impressions" in df.columns else 0
    total_clicks      = df["clicks"].sum()          if "clicks"      in df.columns else 0
    total_engagements = df["engagements"].sum()     if "engagements" in df.columns else 0
    avg_ctr           = (total_clicks / total_impressions * 100) if total_impressions else 0
    avg_cpc           = (total_spend / total_clicks)             if total_clicks      else 0
    avg_cpm           = (total_spend / total_impressions * 1000) if total_impressions else 0

    date_min = df["date"].min().strftime("%d %b %Y") if "date" in df.columns else "N/A"
    date_max = df["date"].max().strftime("%d %b %Y") if "date" in df.columns else "N/A"

    lines = [
        f"### {label} ({date_min} → {date_max})",
        f"Spend: €{total_spend:,.2f}",
        f"Impressions: {total_impressions:,.0f}",
        f"Clicks: {total_clicks:,.0f}",
        f"Engagements: {total_engagements:,.0f}",
        f"CTR: {avg_ctr:.2f}%",
        f"CPC: €{avg_cpc:.2f}",
        f"CPM: €{avg_cpm:.2f}",
        "",
    ]

    if "channel" in df.columns:
        ch = df.groupby("channel")["spend"].sum().sort_values(ascending=False) if "spend" in df.columns else df.groupby("channel").size()
        lines.append("Spend by channel:")
        for name, val in ch.items():
            lines.append(f"  - {name}: €{val:,.2f}")
        lines.append("")

    if "market" in df.columns:
        mkt = (
            df.groupby("market")
            .agg(spend=("spend", "sum"), clicks=("clicks", "sum"), impressions=("impressions", "sum"))
            .assign(ctr=lambda x: (x["clicks"] / x["impressions"].replace(0, float("nan")) * 100).fillna(0))
            .sort_values("spend", ascending=False)
        )
        lines.append("Performance by market:")
        for market, row in mkt.iterrows():
            lines.append(f"  - {market}: €{row['spend']:,.2f} spend | CTR {row['ctr']:.2f}%")
        lines.append("")

    if "funnel_stage" in df.columns and "spend" in df.columns:
        funnel = df.groupby("funnel_stage")["spend"].sum().sort_values(ascending=False)
        if not funnel.empty:
            lines.append("Spend by funnel stage:")
            for stage, spend in funnel.items():
                pct = spend / total_spend * 100 if total_spend else 0
                lines.append(f"  - {stage}: €{spend:,.2f} ({pct:.1f}%)")
            lines.append("")

    if "campaign_name" in df.columns and "spend" in df.columns:
        top = (
            df.groupby("campaign_name")["spend"].sum()
            .sort_values(ascending=False)
            .head(5)
        )
        lines.append("Top 5 campaigns by spend:")
        for name, val in top.items():
            lines.append(f"  - {name}: €{val:,.2f}")
        lines.append("")

    return "\n".join(lines)


def summarize(df: pd.DataFrame, filters: dict) -> str:
    if df.empty:
        return "No data available for the selected filters."

    date_min = df["date"].min().strftime("%d %b %Y") if "date" in df.columns else "N/A"
    date_max = df["date"].max().strftime("%d %b %Y") if "date" in df.columns else "N/A"

    header = [
        "## CAMPAIGN PERFORMANCE SUMMARY",
        f"Period: {date_min} to {date_max}",
    ]
    for k, v in filters.items():
        header.append(f"{k.replace('_', ' ').title()}: {v}")
    header.append("")

    return "\n".join(header) + _build_period_summary(df, "Performance")


def summarize_comparison(df_a: pd.DataFrame, df_b: pd.DataFrame, filters: dict) -> str:
    header = ["## PERIOD COMPARISON"]
    for k, v in filters.items():
        header.append(f"{k.replace('_', ' ').title()}: {v}")
    header.append("")

    block_a = _build_period_summary(df_a, "Period A (current)")
    block_b = _build_period_summary(df_b, "Period B (comparison)")
    return "\n".join(header) + block_a + "\n---\n\n" + block_b


def generate_insights(df: pd.DataFrame, filters: dict, model: str = None) -> str:
    summary = summarize(df, filters)
    return _call_claude(
        system=SYSTEM_PROMPT,
        user_prompt=(
            f"{summary}\n\n"
            "Give me:\n"
            "1. What is performing well\n"
            "2. What needs immediate attention\n"
            "3. Specific optimization recommendations (prioritized by impact)\n\n"
            "Be specific. Reference actual numbers. Keep it actionable."
        ),
        model=model,
    )


def generate_comparison(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    filters: dict,
    model: str = None,
) -> str:
    summary = summarize_comparison(df_a, df_b, filters)
    return _call_claude(
        system=COMPARISON_SYSTEM_PROMPT,
        user_prompt=(
            f"{summary}\n\n"
            "Compare these two periods and give me:\n"
            "1. Key metric changes (with % change where possible)\n"
            "2. What drove the changes\n"
            "3. What needs attention based on the trend\n"
            "4. Specific recommendations for the next period\n\n"
            "Use ↑ ↓ → to show direction. Be specific and reference actual numbers."
        ),
        model=model,
    )


GENERIC_SYSTEM_PROMPT = """You are a sharp data analyst. You will be given a structured summary of a dataset.

When analysing the data, you will:
1. Describe what the dataset appears to be about
2. Highlight the most interesting patterns, trends, or outliers
3. Flag anything unusual, incomplete, or worth investigating
4. Suggest 2-3 specific questions this data could help answer

Be direct and specific. Reference actual column names and numbers. Format clearly with markdown headers.

Never say "based on the data provided" — just state the insight directly."""


def _build_generic_summary(df: pd.DataFrame) -> str:
    lines = [
        f"Dataset: {len(df):,} rows × {len(df.columns)} columns",
        f"Columns: {', '.join(df.columns.tolist())}",
        "",
    ]

    num_cols = df.select_dtypes(include="number").columns.tolist()
    if num_cols:
        lines.append("Numeric columns:")
        for col in num_cols:
            s = df[col].dropna()
            nulls = int(df[col].isna().sum())
            lines.append(
                f"  - {col}: min={s.min():.2f}, max={s.max():.2f}, "
                f"mean={s.mean():.2f}, median={s.median():.2f}, nulls={nulls}"
            )
        lines.append("")

    cat_cols = df.select_dtypes(exclude="number").columns.tolist()
    if cat_cols:
        lines.append("Text/categorical columns:")
        for col in cat_cols:
            nulls = int(df[col].isna().sum())
            unique = df[col].nunique()
            top = df[col].value_counts().head(5)
            top_str = ", ".join(f"{v} ({c})" for v, c in top.items())
            lines.append(f"  - {col}: {unique} unique values, nulls={nulls}. Top: {top_str}")
        lines.append("")

    lines.append("Sample rows (first 5):")
    lines.append(df.head(5).to_string(index=False))

    return "\n".join(lines)


BENCHMARK_SYSTEM_PROMPT = """You are a senior media strategist. You will be given two datasets: actual campaign results and a benchmark or media plan.

Your job is to do a clear gap analysis between the two.

When analysing, you will:
1. Compare actual performance vs the benchmark metric by metric
2. Highlight where results exceeded the benchmark and why
3. Flag where results fell short of the benchmark and why
4. Give specific, prioritised recommendations for the next period

Use ↑ ↓ → to show direction vs benchmark. Be direct. Reference actual numbers and percentage differences.
Format clearly with markdown headers. Never say "based on the data provided" — just state the insight directly."""


def generate_insights_vs_benchmark(
    df_actual: pd.DataFrame,
    df_benchmark: pd.DataFrame,
    model: str = None,
) -> str:
    def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        return df

    df_actual = _normalize_cols(df_actual)
    df_benchmark = _normalize_cols(df_benchmark)

    actual_summary = _build_generic_summary(df_actual)
    benchmark_summary = _build_generic_summary(df_benchmark)
    return _call_claude(
        system=BENCHMARK_SYSTEM_PROMPT,
        user_prompt=(
            f"## ACTUAL RESULTS\n{actual_summary}\n\n"
            f"## BENCHMARK / MEDIA PLAN\n{benchmark_summary}\n\n"
            "Column names in both datasets have been normalised to lowercase, so 'Impressions', "
            "'IMPRESSIONS', and 'impressions' are all the same metric. Match columns by their "
            "meaning, not their exact name.\n\n"
            "Compare actual vs benchmark and give me:\n"
            "1. How did we perform vs the plan — metric by metric\n"
            "2. Where did we exceed expectations and why\n"
            "3. Where did we fall short and why\n"
            "4. Specific recommendations for the next period\n\n"
            "Use ↑ ↓ → to show direction. Reference actual numbers and % differences."
        ),
        model=model,
    )


def generate_generic_insights(df: pd.DataFrame, model: str = None) -> str:
    summary = _build_generic_summary(df)
    return _call_claude(
        system=GENERIC_SYSTEM_PROMPT,
        user_prompt=(
            f"{summary}\n\n"
            "Give me:\n"
            "1. What this dataset is about\n"
            "2. The most interesting patterns or findings\n"
            "3. Anything unusual or worth investigating\n"
            "4. 2-3 questions this data could help answer\n\n"
            "Be specific. Reference actual column names and numbers."
        ),
        model=model,
    )


PHASE_INSIGHT_SYSTEM_PROMPT = """You are a senior paid media strategist. You will receive campaign KPI data broken down by funnel phase.

For each active phase, produce a focused insight block with:
- A short headline summarising performance for that phase
- 2 highlights (what is working, with specific numbers)
- 2 lowlights (what needs attention, with specific numbers)
- 1–2 concrete recommendations tied to that phase's goals

If multiple phases are active, add a cross-phase section at the end:
- Where is the biggest funnel drop-off between phases?
- One cross-phase recommendation

Awareness benchmarks: good CPM < €5, good VTR > 30%, healthy Frequency 2–4, warning Frequency > 6
Consideration benchmarks: good CTR > 1%, warning CPC above average by 30%+
Purchase benchmarks: good ROAS > 3, warning ROAS < 1, good CVR > 3%

Use ↑ ↓ → to show direction. Be direct and specific. Format with markdown headers per phase.
Never say "based on the data provided" — just state the insight."""


def generate_phase_insights(
    phases: list,
    kpi_summary: dict,
    model: str = None,
) -> str:
    """Generate phase-scoped insights from pre-computed KPI summaries.

    kpi_summary: { 'awareness': {'Impressions': 1200000, 'CPM': 4.2, ...}, ... }
    """
    lines = ["## CAMPAIGN KPI SUMMARY BY PHASE\n"]
    for phase in phases:
        label = {"awareness": "Awareness", "consideration": "Consideration", "purchase": "Purchase / Lead"}.get(phase, phase)
        lines.append(f"### {label}")
        phase_kpis = kpi_summary.get(phase, {})
        if phase_kpis:
            for name, value in phase_kpis.items():
                lines.append(f"  - {name}: {value}")
        else:
            lines.append("  No data available for this phase.")
        lines.append("")

    prompt_body = "\n".join(lines)
    phase_labels = [{"awareness": "Awareness", "consideration": "Consideration", "purchase": "Purchase / Lead"}.get(p, p) for p in phases]

    return _call_claude(
        system=PHASE_INSIGHT_SYSTEM_PROMPT,
        user_prompt=(
            f"{prompt_body}\n\n"
            f"Active phases: {', '.join(phase_labels)}\n\n"
            "Generate the insight blocks as described. Be specific, reference the actual numbers above."
        ),
        model=model,
    )


def _call_claude(system: str, user_prompt: str, model: str = None) -> str:
    api_key = st.secrets.get("anthropic", {}).get("api_key", "")
    if not api_key:
        return "Claude API key not found. Add it to .streamlit/secrets.toml under [anthropic]."

    active_model = model or MODEL
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=active_model,
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text
