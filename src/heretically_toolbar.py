"""Heretically toolbar + table — v2 (fixed).
Fix: render_model_table now derives Sample Size / Refusal Drop from
Refusals / Initial Refusals when they are missing. The main parse
(get_model_data) does NOT produce those columns — only
core._add_leaderboard_columns does. v1 silently dropped them.
Session keys (same as app.py): query, date_range, unknowns, heretic_gen,
show_quants, scope_limit, sort_by, kl_range, refusal_range, min_likes, min_downloads
"""
import re
import streamlit as st
import pandas as pd
from src.heretically_design import marginalia


def _parse_fraction(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return (None, None)
    m = re.search(r"(\d+)\s*/\s*(\d+)", str(s))
    if not m:
        return (None, None)
    try:
        return (int(m.group(1)), int(m.group(2)))
    except (ValueError, ZeroDivisionError):
        return (None, None)


def _ensure_derived(df: pd.DataFrame) -> pd.DataFrame:
    view = df.copy()
    if "Sample Size" not in view.columns and "Refusals" in view.columns:
        view["Sample Size"] = view["Refusals"].apply(lambda v: _parse_fraction(v)[1])
    if "Refusal Drop" not in view.columns and "Refusals" in view.columns and "Initial Refusals" in view.columns:
        def _drop(row):
            ref_num, _ = _parse_fraction(row.get("Refusals"))
            init_num, _ = _parse_fraction(row.get("Initial Refusals"))
            if ref_num is None or init_num is None:
                return None
            return float(init_num - ref_num)
        view["Refusal Drop"] = view.apply(_drop, axis=1)
    return view


def render_toolbar():
    with st.container(border=True):
        r1 = st.columns([3, 2, 2, 1], vertical_alignment="bottom")
        with r1[0]:
            st.text_input("Search model ID", key="query", placeholder="Search")
        with r1[1]:
            st.selectbox("Sort by", options=[
                "Downloads (high → low)", "Likes (high → low)",
                "KL Divergence (low → high)", "KL Divergence (high → low)",
                "Refusal Rate (%) (low → high)", "Refusal Rate (%) (high → low)",
                "Heretic version (new → old)", "Model (A → Z)",
            ], key="sort_by")
        with r1[2]:
            st.selectbox("Scope", options=[
                "25 (Top past month)", "10 (Trending 7d)", "50", "100", "All",
            ], key="scope_limit",
                help="Top 25 from the past month is the cold-start default. It keeps the first screen full.")
        with r1[3]:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("Reset filters", key="reset_filters", type="secondary"):
                for k, v in {
                    "query": "", "date_range": "Last month",
                    "unknowns": "Include unknowns", "heretic_gen": "All",
                    "show_quants": False, "scope_limit": "25 (Top past month)",
                    "sort_by": "Downloads (high → low)",
                    "kl_range": (0.0, 0.5), "refusal_range": (0.0, 100.0),
                    "min_likes": 0, "min_downloads": 0,
                }.items():
                    st.session_state[k] = v
                st.rerun()
        r2 = st.columns([2, 2, 2, 1], vertical_alignment="bottom")
        with r2[0]:
            st.segmented_control("Release date", options=[
                "All time", "Last week", "Last month", "Last 6 months", "Last year",
            ], key="date_range")
        with r2[1]:
            st.segmented_control("Unknown dates", options=[
                "Include unknowns", "Hide unknowns", "Only unknowns",
            ], key="unknowns")
        with r2[2]:
            st.segmented_control("Heretic generation", options=[
                "All", "2.x", "1.x", "Unknown",
            ], key="heretic_gen")
        with r2[3]:
            st.toggle("Include quantised", key="show_quants",
                      help="Quantised builds (GGUF, MLX, AWQ, GPTQ, EXL2/3, INT8/INT4) are hidden by default.")
        with st.expander("Advanced metric filters & actions"):
            c = st.columns([2, 2, 1, 1])
            with c[0]:
                st.slider("KL Divergence", min_value=0.0, max_value=0.5, step=0.01, key="kl_range")
            with c[1]:
                st.slider("Refusal rate", min_value=0.0, max_value=100.0, step=1.0, key="refusal_range")
            with c[2]:
                st.number_input("Min likes", min_value=0, step=1, key="min_likes")
            with c[3]:
                st.number_input("Min downloads", min_value=0, step=1, key="min_downloads")
            b = st.columns([1, 1, 2])
            with b[0]:
                st.button("Refresh metrics", key="refresh_metrics", type="primary")
            with b[1]:
                st.button("Refresh popularity", key="refresh_popularity", type="secondary")


def render_model_table(df: pd.DataFrame):
    if df is None or len(df) == 0:
        st.markdown("No models in this scope. Try widening the date range or clearing the search.")
        return
    view = _ensure_derived(df)
    if "Note" not in view.columns and "Compare" in view.columns:
        view["Note"] = view["Compare"].apply(marginalia)
    elif "Note" in view.columns:
        view["Note"] = view["Note"].apply(marginalia)
    view["Model"] = view["Model ID"].astype(str)
    cols = [c for c in ["Model", "KL Divergence", "Refusal Rate (%)", "Refusal Drop",
                        "Sample Size", "Likes", "Downloads", "Heretic Gen",
                        "Heretic Version", "Note"] if c in view.columns]
    st.dataframe(
        view[cols],
        hide_index=True,
        height=min(640, 40 + 36 * min(len(view), 25)),
        column_config={
            "Model": st.column_config.TextColumn("Model", width="medium"),
            "KL Divergence": st.column_config.NumberColumn("KL", format="%.3f"),
            "Refusal Rate (%)": st.column_config.NumberColumn("Refusal %", format="%.1f"),
            "Refusal Drop": st.column_config.NumberColumn("Drop", format="%.0f"),
            "Sample Size": st.column_config.NumberColumn("Sample", format="%d"),
            "Likes": st.column_config.NumberColumn("Likes", format="%d"),
            "Downloads": st.column_config.NumberColumn("Downloads", format="%d"),
            "Heretic Gen": st.column_config.TextColumn("Gen"),
            "Heretic Version": st.column_config.TextColumn("Version"),
            "Note": st.column_config.TextColumn("Note", width="large"),
        },
    )
    st.caption("Numbers use tabular figures. KL bands adapt to models in scope (tertiles). "
               "§ notes are grain-of-salt marginalia, not verdicts.")
