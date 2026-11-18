"""Heretically charts — Pareto + Radar. v2 (fixed).

Fixes over v1:
- Pareto domain is ADAPTIVE: max(0.25, max KL * 1.1) and max(30, max refusal * 1.1).
  Real data has KL 0.30 / refusal 60% in core tests — v1 hard domain clipped those.
- Percentile uses core formula (rank-1)/(n-1), not rank/n. Radar and
  leaderboard now agree: [0.0, 0.5, 1.0] for [1,2,3], missing -> 0.5.
- Cap line stays at 0.20 even when domain expands.
"""
import math
import altair as alt
import pandas as pd

INK = "#1F1B16"
SECONDARY = "#5E554A"
MUTED = "#7B7266"
EMBER = "#C2410C"
HAIRLINE = "#E5E0D6"
PAPER = "#F7F4EE"
CARD = "#FDFBF7"
RED = "#DC2626"
MONO = "JetBrains Mono"
SANS = "Instrument Sans"
KL_CAP = 0.20


def _parse_fraction(s):
    import re
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return (None, None)
    m = re.search(r"(\d+)\s*/\s*(\d+)", str(s))
    if not m:
        return (None, None)
    try:
        return (int(m.group(1)), int(m.group(2)))
    except (ValueError, ZeroDivisionError):
        return (None, None)


def pareto_frontier(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return pd.DataFrame()
    pts = df.dropna(subset=["KL Divergence", "Refusal Rate (%)"]).copy()
    pts = pts.sort_values(["KL Divergence", "Refusal Rate (%)"])
    frontier, best = [], float("inf")
    for _, row in pts.iterrows():
        r = float(row["Refusal Rate (%)"])
        if r < best:
            frontier.append(row)
            best = r
    return pd.DataFrame(frontier) if frontier else pd.DataFrame()


def _base(chart):
    return chart.configure_axis(
        labelFont=MONO, labelFontSize=11, labelColor=MUTED,
        titleFont=SANS, titleFontSize=13, titleColor=SECONDARY,
        gridColor=HAIRLINE, tickColor=HAIRLINE,
    ).configure_view(strokeWidth=0, fill=CARD).configure(background=PAPER)


def _adaptive_domain(series, floor: float) -> float:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    if len(vals) == 0:
        return floor
    return max(floor, float(vals.max()) * 1.1)


def pareto_chart(df: pd.DataFrame):
    if df is None or len(df) == 0:
        return None
    pts = df.dropna(subset=["KL Divergence", "Refusal Rate (%)"]).copy()
    frontier = pareto_frontier(df)
    kl_max = _adaptive_domain(pts["KL Divergence"], 0.25)
    rr_max = _adaptive_domain(pts["Refusal Rate (%)"], 30.0)
    dots = alt.Chart(pts).mark_circle(size=64, opacity=0.55, color=INK).encode(
        x=alt.X("KL Divergence:Q", title="KL Divergence", scale=alt.Scale(domain=[0, kl_max])),
        y=alt.Y("Refusal Rate (%):Q", title="Refusal Rate (%)", scale=alt.Scale(domain=[0, rr_max])),
        tooltip=["Model ID:N", "KL Divergence:Q", "Refusal Rate (%):Q", "Likes:Q", "Downloads:Q"],
    )
    line = alt.Chart(frontier).mark_line(color=EMBER, strokeWidth=2).encode(
        x="KL Divergence:Q", y="Refusal Rate (%):Q") if len(frontier) else alt.Chart(pd.DataFrame()).mark_point()
    fpts = alt.Chart(frontier).mark_circle(size=90, color=EMBER).encode(
        x="KL Divergence:Q", y="Refusal Rate (%):Q",
        tooltip=["Model ID:N", "KL Divergence:Q", "Refusal Rate (%):Q"]) if len(frontier) else alt.Chart(pd.DataFrame()).mark_point()
    cap = alt.Chart(pd.DataFrame({"x": [KL_CAP]})).mark_rule(color=RED, strokeDash=[4, 4], strokeWidth=1.5).encode(x="x:Q")
    cap_label = alt.Chart(pd.DataFrame({"x": [KL_CAP], "y": [rr_max * 0.97], "t": ["KL cap <=0.20"]})).mark_text(
        align="left", dx=6, font=MONO, fontSize=11, color=RED).encode(x="x:Q", y="y:Q", text="t:N")
    note = alt.Chart(pd.DataFrame({"x": [0.01], "y": [rr_max * 0.93], "t": ["Sample sweet spot 128-256 - Refusal change -85% to -95% - lambda 0.8-1.0"]})).mark_text(
        align="left", font=MONO, fontSize=11, color=MUTED).encode(x="x:Q", y="y:Q", text="t:N")
    return _base((dots + line + fpts + cap + cap_label + note).properties(
        height=320, title="Pareto frontier — lower KL and lower refusal is better"))


def _pct_core(series, higher=True):
    """Match hf_space/heretically_core._percentile_score exactly."""
    values = pd.to_numeric(series, errors="coerce")
    valid = int(values.notna().sum())
    if valid == 0:
        return pd.Series(0.5, index=series.index, dtype="float64")
    ranks = values.rank(method="average", ascending=higher, na_option="keep")
    if valid > 1:
        scaled = (ranks - 1) / (valid - 1)
    else:
        scaled = ranks.apply(lambda v: 1.0 if pd.notna(v) else 0.5)
    return scaled.fillna(0.5)


def radar_chart(df: pd.DataFrame, selected_ids: list):
    if df is None or len(df) == 0 or not selected_ids:
        return None
    sub = df[df["Model ID"].isin(selected_ids)].copy()
    if len(sub) == 0:
        return None
    sub["Low refusal"] = 100 - pd.to_numeric(sub["Refusal Rate (%)"], errors="coerce").fillna(50)
    sub["Low KL"] = _pct_core(sub["KL Divergence"], higher=False) * 100
    ref_num = sub["Refusals"].apply(lambda v: _parse_fraction(v)[0])
    init_num = sub["Initial Refusals"].apply(lambda v: _parse_fraction(v)[0])
    sub["Refusal drop"] = _pct_core((init_num - ref_num).fillna(0), True) * 100
    sub["Sample size"] = _pct_core(sub["Refusals"].apply(lambda v: _parse_fraction(v)[1]).fillna(0), True) * 100
    sub["Likes"] = _pct_core(sub["Likes"].apply(lambda v: math.log1p(max(0, float(v or 0)))), True) * 100
    sub["Downloads"] = _pct_core(sub["Downloads"].apply(lambda v: math.log1p(max(0, float(v or 0)))), True) * 100
    axes = ["Low refusal", "Low KL", "Refusal drop", "Sample size", "Likes", "Downloads"]
    rows, colors = [], [EMBER, INK, SECONDARY, MUTED]
    for i, (_, row) in enumerate(sub.iterrows()):
        short = str(row["Model ID"]).split("/")[-1][:24]
        for j, ax in enumerate(axes):
            angle = 2 * math.pi * j / len(axes) - math.pi / 2
            r = float(row[ax]) / 100.0
            rows.append({"model": short, "axis": ax, "x": r * math.cos(angle),
                         "y": r * math.sin(angle), "value": float(row[ax]),
                         "color": colors[i % len(colors)]})
    long = pd.DataFrame(rows)
    close = long.groupby("model").head(1).copy()
    long = pd.concat([long, close], ignore_index=True)
    line = alt.Chart(long).mark_line(point=True).encode(
        x=alt.X("x:Q", axis=None, scale=alt.Scale(domain=[-1.15, 1.15])),
        y=alt.Y("y:Q", axis=None, scale=alt.Scale(domain=[-1.15, 1.15])),
        color=alt.Color("model:N", scale=None), detail="model:N",
        tooltip=["model:N", "axis:N", "value:Q"])
    labels = alt.Chart(pd.DataFrame([
        {"axis": ax, "x": 1.08 * math.cos(2 * math.pi * j / len(axes) - math.pi / 2),
         "y": 1.08 * math.sin(2 * math.pi * j / len(axes) - math.pi / 2)}
        for j, ax in enumerate(axes)])).mark_text(
        font=MONO, fontSize=11, color=MUTED, align="center").encode(x="x:Q", y="y:Q", text="axis:N")
    return _base((line + labels).properties(height=280, title="Compare — radar"))
