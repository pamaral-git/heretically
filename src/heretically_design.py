"""Heretically design system — unslop pass.
Quiet chrome, rich chart. One warm neutral ramp, one ember accent.
Usage: from src.heretically_design import inject_heretically_design
Call it right after st.set_page_config().
"""
import streamlit as st

TOKENS = {
    "paper": "#F7F4EE", "card": "#FDFBF7", "raised": "#EFE9DF",
    "hairline": "rgba(31, 27, 22, 0.10)", "ink": "#1F1B16",
    "secondary": "#5E554A", "muted": "#7B7266",
    "ember": "#C2410C", "ember_bright": "#E8480C", "ember_hover": "#9A3412",
    "green": "#16A34A", "red": "#DC2626", "on_ember": "#FDFBF7",
    "font_title": "'Newsreader', Georgia, serif",
    "font_ui": "'Instrument Sans', Arial, sans-serif",
    "font_mono": "'JetBrains Mono', Consolas, monospace",
    "easing": "cubic-bezier(0.22, 1, 0.36, 1)",
}


def marginalia(text: str) -> str:
    t = (text or "").strip()
    if not t or t == "—":
        return "—"
    return t if t.startswith("§") else f"§ {t}"


def inject_heretically_design() -> None:
    st.markdown(
        """
<link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap" rel="stylesheet">
<style>
:root { --paper:#F7F4EE; --card:#FDFBF7; --raised:#EFE9DF; --hairline:rgba(31,27,22,0.10);
  --ink:#1F1B16; --secondary:#5E554A; --muted:#7B7266; --ember:#C2410C; --ember-hover:#9A3412;
  --easing:cubic-bezier(0.22,1,0.36,1); }
html, body, .stApp { background: var(--paper) !important; color: var(--ink) !important;
  font-family: 'Instrument Sans', Arial, sans-serif !important; }
.stApp { font-variant-numeric: tabular-nums; }
.block-container { max-width: 1440px; padding: 24px 32px 48px 32px; }
h1 { font-family: 'Newsreader', Georgia, serif !important; font-weight: 500 !important;
  font-size: 36px !important; line-height: 1.1 !important; color: var(--ink) !important; }
h2, h3 { font-family: 'Instrument Sans', sans-serif !important; font-weight: 500 !important; color: var(--ink) !important; }
.heretically-kicker { font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; color: var(--muted) !important; }
.heretically-lede { font-size: 16px !important; line-height: 24px !important; color: var(--secondary) !important; max-width: 72ch; }
.heretically-marginalia { font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; color: var(--muted) !important; }
.heretically-figure { font-family: 'JetBrains Mono', monospace !important; font-variant-numeric: tabular-nums !important; }
[data-testid="stVerticalBlockBorderWrapper"] { background: var(--card) !important;
  border: 1px solid var(--hairline) !important; border-radius: 16px !important; box-shadow: none !important; }
button[data-testid="stTab"] p { font-size: 14px !important; font-weight: 500 !important; color: var(--secondary) !important; }
button[data-testid="stTab"][aria-selected="true"] p { color: var(--ink) !important; }
button[data-testid="stTab"][aria-selected="true"] { border-bottom: 2px solid var(--ember) !important; }
[data-testid="stButton"] > button { border-radius: 8px !important; min-height: 40px !important; padding: 0 16px !important;
  font-weight: 500 !important; font-size: 14px !important; box-shadow: none !important;
  transition: background-color 160ms var(--easing), border-color 160ms var(--easing), transform 120ms var(--easing) !important; }
[data-testid="stButton"] > button[kind="primary"] { background: var(--ember) !important; color: var(--card) !important; border: 1px solid var(--ember) !important; }
[data-testid="stButton"] > button[kind="primary"]:hover { background: var(--ember-hover) !important; }
[data-testid="stButton"] > button[kind="secondary"] { background: var(--raised) !important; color: var(--ink) !important; border: 1px solid var(--hairline) !important; }
[data-testid="stButton"] > button:active { transform: scale(0.98); }
[data-testid="stButton"] > button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--ember) !important; outline-offset: 2px !important; }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] > div > div { background: var(--card) !important; border: 1px solid var(--hairline) !important; border-radius: 8px !important; color: var(--ink) !important; }
[data-testid="stWidgetLabel"] p { font-weight: 500 !important; color: var(--ink) !important; font-size: 13px !important; }
[data-testid="stDataFrame"], [data-testid="stTable"] { font-variant-numeric: tabular-nums !important; }
[data-testid="stDataFrame"] thead th { font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; color: var(--muted) !important; font-weight: 400 !important; }
[data-testid="stMetric"] { background: var(--card); border: 1px solid var(--hairline); border-radius: 14px; padding: 16px 20px; }
[data-testid="stMetricLabel"] p { font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; color: var(--muted) !important; }
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; font-size: 30px !important; color: var(--ink) !important; }
* { animation: none !important; }
</style>
""",
        unsafe_allow_html=True,
    )
