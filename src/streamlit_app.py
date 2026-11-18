import html
import streamlit as st
import pandas as pd
from huggingface_hub import HfApi
import requests
from requests.adapters import HTTPAdapter
import re
import concurrent.futures
import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

# Configure the Streamlit page
st.set_page_config(page_title="Heretically", page_icon="🔥", layout="wide")

st.markdown(
    """<style>
    @import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=Instrument+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --paper: #F7F4EE;
        --card: #FDFBF7;
        --raised: #EFE9DF;
        --hairline: rgba(31, 27, 22, 0.10);
        --ink: #1F1B16;
        --secondary: #5E554A;
        --muted: #7B7266;
        --ember: #C2410C;
        --ember-hover: #A83509;
        --green: #16A34A;
        --red: #DC2626;
    }

    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: var(--paper) !important;
        color: var(--ink) !important;
        font-family: "Instrument Sans", system-ui, -apple-system, sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
        border-bottom: none !important;
        pointer-events: none !important;
    }
    [data-testid="stHeader"] * {
        pointer-events: auto;
    }

    .block-container {
        max-width: 1440px;
        padding: 3.5rem 2rem 3.5rem !important;
    }

    /* Editorial header bar */
    .heretic-brand-row {
        display: flex;
        align-items: baseline;
        gap: 0.75rem;
        flex-wrap: wrap;
    }
    .heretic-brand-title {
        font-family: "Newsreader", Georgia, serif;
        font-size: 1.85rem;
        font-weight: 600;
        letter-spacing: -0.02em;
        line-height: 1.15;
        white-space: nowrap;
        color: var(--ink);
        margin: 0;
        padding: 0.1rem 0;
    }
    .heretic-brand-tag {
        font-family: "JetBrains Mono", ui-monospace, monospace;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--muted);
        white-space: nowrap;
    }
    .heretic-hero {
        display: flex;
        flex-wrap: wrap;
        align-items: flex-end;
        justify-content: space-between;
        gap: 1rem 2rem;
        margin-bottom: 1.25rem;
    }
    .heretic-kicker {
        font-family: "JetBrains Mono", ui-monospace, monospace;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: var(--muted);
        margin-bottom: 0.45rem;
    }
    .heretic-hero-h1 {
        font-family: "Newsreader", Georgia, serif !important;
        font-size: 2.85rem !important;
        font-weight: 500 !important;
        line-height: 1.08 !important;
        letter-spacing: -0.03em !important;
        color: var(--ink) !important;
        margin: 0 !important;
        padding-bottom: 0.1rem !important;
    }
    .heretic-hero-lede {
        max-width: 440px;
        font-size: 0.92rem;
        line-height: 1.55;
        color: var(--secondary);
    }
    .heretic-hero-lede a {
        color: var(--ember);
        text-decoration: underline;
        text-underline-offset: 2px;
    }

    /* Uppercase mono widget labels matching meta-page.html */
    [data-testid="stWidgetLabel"] label p,
    [data-testid="stWidgetLabel"] p {
        font-family: "JetBrains Mono", ui-monospace, monospace !important;
        font-size: 0.69rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted) !important;
    }

    /* Card containers (--card #FDFBF7, 16px radius, subtle hairline) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: var(--card) !important;
        border: 1px solid var(--hairline) !important;
        border-radius: 16px !important;
        padding: 0.35rem 0.5rem;
        box-shadow: none !important;
    }

    /* Inputs & selects on white/ivory paper */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stMultiSelect"] > div > div {
        background-color: #FFFFFF !important;
        border: 1px solid var(--hairline) !important;
        border-radius: 8px !important;
        color: var(--ink) !important;
        font-size: 0.88rem !important;
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus {
        border-color: rgba(31, 27, 22, 0.30) !important;
        box-shadow: none !important;
    }

    /* Segmented pill track (--raised #EFE9DF with --card active shadow) */
    [data-testid="stSegmentedControl"] [role="radiogroup"],
    [data-baseweb="button-group"] {
        background-color: var(--raised) !important;
        border-radius: 8px !important;
        padding: 3px !important;
        border: none !important;
        gap: 2px !important;
    }
    [data-testid="stSegmentedControl"] button {
        border-radius: 6px !important;
        border: none !important;
        font-size: 0.8rem !important;
        color: var(--secondary) !important;
        background: transparent !important;
        padding: 0.3rem 0.6rem !important;
        min-height: 30px !important;
    }
    [data-testid="stSegmentedControl"] button[aria-checked="true"],
    [data-testid="stSegmentedControl"] button[kind="segmented_controlActive"] {
        background-color: var(--card) !important;
        color: var(--ink) !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08) !important;
        font-weight: 500 !important;
    }

    /* Buttons matching meta-page.html */
    [data-testid="stButton"] > button,
    [data-testid="stPopover"] > div > button,
    [data-testid="stDownloadButton"] > button {
        border-radius: 8px !important;
        font-size: 0.83rem !important;
        font-weight: 500 !important;
        min-height: 38px !important;
        box-shadow: none !important;
        transition: background-color 150ms ease, border-color 150ms ease !important;
    }
    [data-testid="stButton"] > button[kind="secondary"],
    [data-testid="stPopover"] > div > button,
    [data-testid="stDownloadButton"] > button {
        background-color: var(--card) !important;
        border: 1px solid var(--hairline) !important;
        color: var(--ink) !important;
    }
    [data-testid="stButton"] > button[kind="secondary"]:hover,
    [data-testid="stPopover"] > div > button:hover,
    [data-testid="stDownloadButton"] > button:hover {
        background-color: var(--raised) !important;
        border-color: rgba(31, 27, 22, 0.22) !important;
    }
    [data-testid="stButton"] > button[kind="primary"] {
        background-color: var(--ember) !important;
        border: 1px solid var(--ember) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    [data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: var(--ember-hover) !important;
    }

    /* Expander styling */
    [data-testid="stExpander"] {
        background-color: rgba(239, 233, 223, 0.55) !important;
        border: 1px solid var(--hairline) !important;
        border-radius: 14px !important;
    }

    /* Clean underlined tabs with ember active bar */
    [data-baseweb="tab-list"] {
        gap: 1.75rem;
        border-bottom: 1px solid var(--hairline);
        margin-top: 0.75rem;
        margin-bottom: 0.85rem;
        background: transparent !important;
    }
    [data-baseweb="tab"] {
        padding: 0.5rem 0 0.75rem !important;
        font-size: 0.94rem !important;
        font-weight: 400 !important;
        color: var(--secondary) !important;
        background: transparent !important;
    }
    [data-baseweb="tab"][aria-selected="true"] {
        font-weight: 600 !important;
        color: var(--ink) !important;
    }
    [data-baseweb="tab-highlight"] {
        background-color: var(--ember) !important;
        height: 2px !important;
    }

    /* Tabular numerals & mono table headings */
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        font-variant-numeric: tabular-nums;
    }
    [data-testid="stTable"] table {
        background: var(--card);
        border: 1px solid var(--hairline);
        border-radius: 12px;
    }
    [data-testid="stTable"] th {
        font-family: "JetBrains Mono", ui-monospace, monospace !important;
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        color: var(--muted) !important;
        border-bottom: 1px solid var(--hairline) !important;
    }

    /* Hairline horizontal rule */
    .hairline-div {
        border: none;
        border-top: 1px solid var(--hairline);
        margin: 0.95rem 0;
    }

    /* Pre-loader / Scope summary card (meta-page.html style) */
    .scope-banner {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        background: var(--card);
        border: 1px solid var(--hairline);
        border-radius: 16px;
        padding: 1.15rem 1.4rem;
        margin: 0.35rem 0 1rem;
    }
    .scope-banner-eyebrow {
        font-family: "JetBrains Mono", ui-monospace, monospace;
        font-size: 0.69rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--ember);
        margin-bottom: 0.35rem;
    }
    .scope-banner-title {
        font-size: 1.18rem;
        font-weight: 600;
        line-height: 1.3;
        color: var(--ink);
        margin: 0 0 0.3rem;
    }
    .scope-banner-text {
        font-size: 0.88rem;
        line-height: 1.5;
        color: var(--secondary);
        max-width: 760px;
    }
    .scope-banner-pill {
        font-family: "JetBrains Mono", ui-monospace, monospace;
        font-size: 0.73rem;
        color: var(--muted);
        background: var(--raised);
        border-radius: 10px;
        padding: 0.6rem 0.85rem;
        white-space: nowrap;
        line-height: 1.45;
    }
    .scope-banner-pill strong {
        color: var(--ink);
        font-weight: 500;
        display: block;
    }

    /* 4-Card KPI Summary Strip */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.9rem 0 1.25rem;
    }
    @media (max-width: 900px) {
        .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    .kpi-card {
        background: var(--card);
        border: 1px solid var(--hairline);
        border-radius: 14px;
        padding: 1.15rem 1.25rem;
    }
    .kpi-label {
        font-family: "JetBrains Mono", ui-monospace, monospace;
        font-size: 0.75rem;
        color: var(--muted);
    }
    .kpi-value {
        font-family: "JetBrains Mono", ui-monospace, monospace;
        font-variant-numeric: tabular-nums;
        font-size: 2rem;
        font-weight: 500;
        line-height: 1;
        margin: 0.5rem 0 0.7rem;
        color: var(--ink);
    }
    .kpi-value.ember { color: var(--ember); }
    .kpi-sub {
        font-size: 0.75rem;
        color: var(--muted);
    }

    /* Leaderboard Spotlight & Weights Cards */
    .lb-card {
        background: var(--card);
        border: 1px solid var(--hairline);
        border-radius: 16px;
        padding: 1.2rem 1.3rem;
    }
    .lb-row {
        padding: 0.6rem 0;
        border-bottom: 1px solid var(--hairline);
    }
    .lb-row:last-child { border-bottom: none; padding-bottom: 0; }
    .lb-row-top {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 0.75rem;
    }
    .lb-row-name {
        font-size: 0.84rem;
        font-weight: 500;
        color: var(--ink);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .lb-row-meta {
        font-family: "JetBrains Mono", ui-monospace, monospace;
        font-size: 0.7rem;
        color: var(--muted);
        margin-top: 0.2rem;
        margin-left: 1.45rem;
    }
    .lb-row-score {
        font-family: "JetBrains Mono", ui-monospace, monospace;
        font-size: 0.84rem;
        font-weight: 500;
        color: var(--ink);
        flex-shrink: 0;
    }
    .lb-bar-track {
        height: 4px;
        border-radius: 99px;
        background: var(--raised);
        margin-top: 0.4rem;
        margin-left: 1.45rem;
        overflow: hidden;
    }
    .lb-bar-track.full { margin-left: 0; }
    .lb-bar-fill {
        height: 100%;
        border-radius: 99px;
        background: #8A8175;
    }
    .lb-bar-fill.top1 { background: var(--ember); }

    /* Table card header & Pareto legend strip */
    .section-bar {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: baseline;
        gap: 0.5rem;
        margin-bottom: 0.55rem;
    }
    .section-bar-title {
        font-size: 1.08rem;
        font-weight: 600;
        color: var(--ink);
    }
    .mono-note {
        font-family: "JetBrains Mono", ui-monospace, monospace;
        font-size: 0.72rem;
        color: var(--muted);
    }
    .pareto-legend {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 1.15rem;
        border-top: 1px solid var(--hairline);
        padding-top: 0.7rem;
        margin-top: 0.35rem;
        font-size: 0.76rem;
        color: var(--secondary);
    }
    .heretic-footer {
        font-family: "JetBrains Mono", ui-monospace, monospace;
        font-size: 0.71rem;
        color: var(--muted);
        border-top: 1px solid var(--hairline);
        margin-top: 2.5rem;
        padding-top: 1rem;
        line-height: 1.6;
    }
    </style>""",
    unsafe_allow_html=True,
)

# Editorial top header bar
head_l, head_c, head_r = st.columns([2.5, 3.3, 1.2], vertical_alignment="center")
with head_l:
    st.markdown(
        '<div class="heretic-brand-row">'
        '<span class="heretic-brand-title">🔥 Heretically</span>'
        '<span class="heretic-brand-tag">Heretic Models / HF</span>'
        '</div>',
        unsafe_allow_html=True,
    )
with head_c:
    st.markdown(
        '<div style="text-align:center;font-size:0.84rem;color:var(--secondary);">'
        'Explore and Discover Uncensored <a href="https://huggingface.co/models?other=heretic" target="_blank" style="color:var(--ember);text-decoration:underline;">Heretic</a> tagged Models from Hugging Face'
        '</div>',
        unsafe_allow_html=True,
    )
with head_r:
    with st.popover("🧬 Finetuning", width="stretch"):
        st.markdown("**Removing Restrictions & Datasets**")
        st.link_button("Heretic Project", "https://heretic-project.org/", width="stretch")
        st.link_button(
            "Multilingual Harmless-Harmful",
            "https://huggingface.co/datasets/heretic-org/Multilingual-Harmless-Harmful",
            width="stretch",
        )
        st.link_button(
            "The Mind of XORTRON",
            "https://huggingface.co/datasets/darkc0de/The-Mind-of-XORTRON",
            width="stretch",
        )

st.markdown('<hr class="hairline-div" style="margin-top:0.4rem;margin-bottom:1.1rem;">', unsafe_allow_html=True)

st.markdown(
    """
    <div class="heretic-hero">
      <div>
        <div class="heretic-kicker">Model Explorer · Hugging Face Corpus</div>
        <h1 class="heretic-hero-h1">Heretically</h1>
      </div>
      <div class="heretic-hero-lede">
        Explore and Discover Uncensored <a href="https://huggingface.co/models?other=heretic" target="_blank">Heretic</a> tagged Models from Hugging Face.<br>
        🍴 Fork from <a href="https://huggingface.co/spaces/MuXodious/Heretic-Models-Explorer" target="_blank">Heretic Models Explorer</a>.
        Inspired greatly by <a href="https://github.com/p-e-w/heretic" target="_blank">@p-e-w Heretic</a> and <a href="https://heretic-project.org/" target="_blank">Heretic Grimoire</a>.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Filter config (single source of truth)
# ---------------------------------------------------------------------------
HERETIC_GEN_OPTIONS = ("All", "2.x", "1.x", "Unknown")

FILTER_DEFAULTS = {
    "query": "",
    "date_range": "Last month",
    "unknowns": "Include unknowns",
    "kl_range": (0.0, 0.5),
    "refusal_range": (0.0, 100.0),
    "min_likes": 0,
    "min_downloads": 0,
    "show_quants": False,
    "heretic_gen": "All",
    "scope_limit": "25 (Top past month)",
    "sort_by": "Downloads (high → low)",
}

DATE_OPTIONS = {
    "All time": None,
    "Last week": 7,
    "Last month": 30,
    "Last 6 months": 182,
    "Last year": 365,
}

UNKNOWN_OPTIONS = (
    "Include unknowns",
    "Hide unknowns",
    "Only unknowns",
)

SCOPE_LIMIT_OPTIONS = ("25 (Top past month)", "10 (Trending 7d)", "50", "100", "All")
SCOPE_ALIASES = {
    "25": "25 (Top past month)",
    "10": "10 (Trending 7d)",
}

SORT_OPTIONS = {
    "KL Divergence (low → high)": ("KL Divergence", True),
    "KL Divergence (high → low)": ("KL Divergence", False),
    "Refusal Rate (%) (low → high)": ("Refusal Rate (%)", True),
    "Refusal Rate (%) (high → low)": ("Refusal Rate (%)", False),
    "Heretic version (new → old)": ("Heretic Version", False),
    "Likes (high → low)": ("Likes", False),
    "Downloads (high → low)": ("Downloads", False),
    "Model (A → Z)": ("Model", True),
}

QUANT_PATTERNS = re.compile(r'(?i)(?:gguf|mlx|awq|nvfp4|gptq|exl[23]|-quant\b|int8|int4|oq[1-8]|mxfp[48])')
QUANT_RE = r"(?i)(?:gguf|mlx|awq|nvfp4|gptq|exl[23]|-quant\b|int8|int4|oq[1-8]|mxfp[48])"

# Heretic 2.x model cards say "made using [Heretic](https://heretic-project.org) v2.x.y";
# 1.x cards link to the GitHub repository instead. All patterns require an explicit
# Heretic link or the "made using/with" phrase, so stray "vX.Y" text cannot misfire.
HERETIC_VERSION_PATTERNS = (
    re.compile(r"(?i)made\s+(?:using|with)\s+\[heretic\]\([^)]*\)\s*v?([0-9][0-9a-z.+-]*)"),
    re.compile(r"(?i)made\s+(?:using|with)\s+heretic\s+v?([0-9][0-9a-z.+-]*)"),
    re.compile(r"(?i)(?:\[heretic\]\([^)]*\)|heretic-project\.org\)|github\.com/p-e-w/heretic\))\s*v?([0-9][0-9a-z.+-]*)"),
)

# Leaderboard criteria. Scores use percentile ranks, so a single outlier
# cannot dominate the ranking the way raw values or min-max scaling would.
LEADERBOARD_CRITERIA = {
    "Low refusal rate": {
        "column": "Refusal Rate (%)",
        "higher_is_better": False,
        "default_weight": 5.0,
        "help": "Lower refusal rate ranks higher.",
    },
    "Low KL divergence": {
        "column": "KL Divergence",
        "higher_is_better": False,
        "default_weight": 3.0,
        "help": "Lower KL divergence (less drift from the base model) ranks higher.",
    },
    "Refusal drop vs base": {
        "column": "Refusal Drop",
        "higher_is_better": True,
        "default_weight": 1.0,
        "help": "How many more prompts the base model refused than the finetune.",
    },
    "Sample size": {
        "column": "Sample Size",
        "higher_is_better": True,
        "default_weight": 1.0,
        "help": "Evaluation prompt count. Larger n means stronger evidence.",
    },
    "Likes": {
        "column": "Likes",
        "higher_is_better": True,
        "default_weight": 1.0,
        "help": "Hugging Face likes.",
    },
    "Downloads": {
        "column": "Downloads",
        "higher_is_better": True,
        "default_weight": 1.0,
        "help": "Hugging Face downloads.",
    },
    "Heretic 2.x metadata": {
        "column": "Heretic 2.x",
        "higher_is_better": True,
        "default_weight": 0.0,
        "help": "Prefers 2.x metadata over 1.x; unknown metadata is neutral.",
    },
}

# ---------------------------------------------------------------------------
# Network: reused Session + retry
# ---------------------------------------------------------------------------
_SESSION = None


def _get_session():
    global _SESSION
    if _SESSION is None:
        s = requests.Session()
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=0)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        s.headers.update({"User-Agent": "Heretic-Models-Explorer/1.0"})
        _SESSION = s
    return _SESSION


@retry(
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def fetch_url(url):
    response = _get_session().get(url, timeout=(3.05, 5))
    # Raise HTTPError for rate limits (429) or server errors (5xx) to trigger a retry
    if response.status_code in (429, 500, 502, 503, 504):
        response.raise_for_status()
    return response

def _parse_fraction(s) -> tuple:
    """Parse '15/100' → (15, 100). Returns (None, None) on failure."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return (None, None)
    m = re.search(r"(\d+)\s*/\s*(\d+)", str(s))
    if not m:
        return (None, None)
    try:
        return (int(m.group(1)), int(m.group(2)))
    except (ValueError, ZeroDivisionError):
        return (None, None)


def _to_float_or_none(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(f) else f


def _version_major(version):
    if version is None:
        return None
    m = re.match(r"\s*v?(\d+)", str(version))
    return int(m.group(1)) if m else None


def _generation_label(version=None, schema_version=None) -> str:
    """Map a Heretic version (or reproduce.json schema) to 2.x / 1.x.

    Schema v4 of reproduce.json was introduced by the Heretic 2.0 plugin system;
    schemas v1-v3 belong to the 1.x line. An explicit
    environment.heretic.version always takes precedence.
    """
    major = _version_major(version)
    if major is not None:
        # Heretic releases so far only have 1.x and 2.x lines; any other major is
        # either a misparsed version or a future release and stays "Unknown"
        # until the filter options learn about it.
        return f"{major}.x" if major in (1, 2) else "Unknown"
    try:
        schema = int(str(schema_version).strip())
    except (TypeError, ValueError):
        schema = None
    if schema is not None:
        if schema >= 4:
            return "2.x"
        if schema >= 1:
            return "1.x"
    return "Unknown"


def _version_sort_key(version) -> tuple:
    nums = [int(n) for n in re.findall(r"\d+", str(version or ""))][:4]
    return tuple(nums + [0] * (4 - len(nums)))


def _extract_heretic_version(text):
    """Extract 'made using Heretic vX.Y.Z' from a model card, if present."""
    if not text:
        return None
    head = text[:6000]
    for pattern in HERETIC_VERSION_PATTERNS:
        match = pattern.search(head)
        if match:
            version = match.group(1).strip(".,;")
            if _version_major(version) is not None:
                return version
    return None


def _display_text(display):
    if isinstance(display, dict):
        value = display.get("md_display")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _reproduce_version_info(data):
    version = None
    env = data.get("environment")
    if isinstance(env, dict):
        heretic = env.get("heretic")
        if isinstance(heretic, dict):
            raw = heretic.get("version")
            if raw is not None and str(raw).strip():
                version = str(raw).strip()
    schema = data.get("version")
    return version, _generation_label(version, schema)


def _reproduce_source(data) -> str:
    schema = data.get("version")
    if schema is None or str(schema).strip() == "":
        return "reproduce.json"
    return f"reproduce.json (schema v{schema})"


def _row_from_metrics(model, kl_div, initial_refusals, refusals, refusal_rate,
                      version=None, generation=None, source=None):
    return {
        "Model ID": model.id,
        "KL Divergence": float(kl_div),
        "Initial Refusals": initial_refusals,
        "Refusal Rate (%)": refusal_rate,
        "Refusals": refusals,
        "Heretic Version": version or "Unknown",
        "Heretic Gen": generation or _generation_label(version),
        "Version Source": source or "heretic tag",
        "Likes": getattr(model, 'likes', 0) or 0,
        "Downloads": getattr(model, 'downloads', 0) or 0,
        "URL": f"https://huggingface.co/{model.id}",
    }


def _layer_dict(entry, key):
    """entry[key] may be a dict (standard), a number, or a markdown string."""
    if not isinstance(entry, dict) or key is None:
        return {}
    value = entry.get(key)
    return value if isinstance(value, dict) else {}


def _entry_value(entry, key="score"):
    """Numeric value from entry[key]; tolerates non-dict shapes (num/str)."""
    raw = entry.get(key) if isinstance(entry, dict) else None
    if isinstance(raw, dict):
        return _to_float_or_none(raw.get("value"))
    return _to_float_or_none(raw)


def _metrics_from_scores(scores):
    """Parse the plugin-based `scores` list written by Heretic 2.x."""
    if not isinstance(scores, list):
        return None
    kl_entry = None
    refusal_entry = None
    classifier_entry = None
    for item in scores:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").lower()
        if "kl" in name and "divergence" in name:
            if kl_entry is None:
                kl_entry = item
        elif "refus" in name:
            if "classifier" in name:
                if classifier_entry is None:
                    classifier_entry = item
            elif refusal_entry is None:
                refusal_entry = item
    # Some runs only expose the BERT classifier score; use it as a fallback.
    if refusal_entry is None:
        refusal_entry = classifier_entry
    if kl_entry is None or refusal_entry is None:
        return None

    kl_score = _layer_dict(kl_entry, "score")
    kl_div = _to_float_or_none(kl_score.get("value"))
    if kl_div is None:
        kl_div = _to_float_or_none(_display_text(kl_score))
    if kl_div is None:
        # Non-dict score (number or "0.0338" string) tolerates malformed uploads.
        kl_div = _entry_value(kl_entry)
    if kl_div is None:
        return None

    refusal_score = _layer_dict(refusal_entry, "score")
    refusal_baseline = _layer_dict(refusal_entry, "baseline")

    refusals = _display_text(refusal_score)
    initial_refusals = _display_text(refusal_baseline)
    ref_num, ref_den = _parse_fraction(refusals)
    if ref_num is not None and ref_den:
        refusal_rate = (ref_num / ref_den) * 100
    else:
        value = _to_float_or_none(refusal_score.get("value"))
        if value is None:
            value = _entry_value(refusal_entry)
        if value is None:
            refusal_rate = None
        elif 0 <= value <= 1:
            refusal_rate = value * 100
            if refusals is None:
                # Denominator guessed from a fraction value; flag it with "≈".
                refusals = f"≈{round(value * 100)}/100"
        else:
            # Percent-valued score without a display string.
            refusal_rate = value
            if refusals is None:
                refusals = f"≈{value:g}/100"
    if initial_refusals is None:
        base_value = _to_float_or_none(refusal_baseline.get("value"))
        if base_value is None:
            base_value = _entry_value(refusal_entry, "baseline")
        if base_value is not None:
            if 0 <= base_value <= 1:
                initial_refusals = f"≈{round(base_value * 100)}/100"
            else:
                initial_refusals = f"{base_value:g}/100"
    if refusals is None:
        return None
    return kl_div, initial_refusals, refusals, refusal_rate


def _metrics_from_legacy(data):
    """Parse the pre-2.0 `metrics` object written by Heretic 1.x."""
    metrics = data.get("metrics")
    if not isinstance(metrics, dict):
        return None
    kl_raw = metrics.get("kl_divergence")
    if kl_raw is None:
        kl_raw = metrics.get("kl")
    kl_div = _to_float_or_none(kl_raw)
    refusals = metrics.get("refusals")
    base_refusals = metrics.get("base_refusals")
    n_bad = metrics.get("n_bad_prompts")
    if kl_div is None or refusals is None or n_bad is None:
        return None
    try:
        refusals = int(refusals)
        n_bad = int(n_bad)
    except (TypeError, ValueError):
        return None
    if n_bad <= 0:
        return None
    initial_refusals = f"{base_refusals}/{n_bad}" if base_refusals is not None else None
    refusals_str = f"{refusals}/{n_bad}"
    refusal_rate = (refusals / n_bad) * 100
    return kl_div, initial_refusals, refusals_str, refusal_rate


def _metrics_from_reproduce(data):
    metrics = _metrics_from_scores(data.get("scores"))
    if metrics is not None:
        return metrics
    return _metrics_from_legacy(data)


# Fetch model's readme.md file and attempt to parse refusal and KL divergence data.
def fetch_model_info(model, version=None, generation=None, source=None):
    """Fetches the README.md for a given model and dynamically extracts metrics."""
    model_id = model.id
    kl_div = None
    refusals_str = None
    refusal_rate = None
    initial_refusals_str = None
    readme_text = ""

    # Download the README.md via raw URL for high-speed fetching
    url = f"https://huggingface.co/{model_id}/raw/main/README.md"
    try:
        response = fetch_url(url)
        if response.status_code == 200:
            readme_text = response.text

            # Extract KL divergence using Regex
            # Matches formats like: "KL divergence | 0.0033"
            kl_match = re.search(r"(?i)KL\s*divergence[^a-zA-Z\d\n]*?([\d\.]+)", readme_text)
            if kl_match:
                try:
                    kl_div = float(kl_match.group(1))
                except ValueError as e:
                    logging.warning(f"Could not parse KL divergence for {model_id}: {e}")

            # Extract Refusals using Regex
            # Matches formats like: "Refusals | 15/100" or "15 / 100".
            # Table rows list [score, baseline] left → right; prose like
            # "dropped from 28/30 to 3/30" lists [before, after] because
            # "from X to Y" reads oldest first.
            for line in readme_text.split('\n'):
                line_lower = line.lower()
                if 'refusals' in line_lower:
                    fractions = re.findall(r"(\d+)\s*/\s*(\d+)", line)
                    if not fractions:
                        continue

                    if 'initial' in line_lower and initial_refusals_str is None:
                        initial_refusals_str = f"{fractions[0][0]}/{fractions[0][1]}"
                    elif 'initial' not in line_lower and refusals_str is None:
                        is_table_row = '|' in line
                        is_prose_range = (
                            'from' in line_lower
                            and ' to ' in line_lower
                            and len(fractions) >= 2
                        )
                        if is_prose_range:
                            score_frac, init_frac = fractions[1], fractions[0]
                        elif is_table_row and len(fractions) >= 2:
                            score_frac, init_frac = fractions[0], fractions[1]
                        else:
                            score_frac, init_frac = fractions[0], None
                        refusals_str = f"{score_frac[0]}/{score_frac[1]}"
                        try:
                            refusal_rate = (int(score_frac[0]) / int(score_frac[1])) * 100
                        except (ValueError, ZeroDivisionError) as e:
                            logging.warning(f"Could not parse refusals for {model_id}: {e}")
                            continue
                        if init_frac is not None and initial_refusals_str is None:
                            initial_refusals_str = f"{init_frac[0]}/{init_frac[1]}"

    except requests.exceptions.RequestException as e:
        logging.warning(f"Error fetching README for {model_id}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error parsing README for {model_id}: {e}")

    # Use the model card's "made using Heretic vX" line when reproduce.json
    # is missing or does not record a version.
    if version is None:
        version = _extract_heretic_version(readme_text)
        if version is not None:
            generation = _generation_label(version)
            source = "model card"
    if generation is None:
        generation = _generation_label(version)

    # Skip models without explicitly stated KL divergence or refusal data
    if kl_div is None or refusals_str is None:
        return None

    return _row_from_metrics(model, kl_div, initial_refusals_str, refusals_str, refusal_rate,
                             version, generation, source)

# Check for reproducibility record first and then fallback to parsing data from readme.md
def get_model_data(model):
    model_id = model.id
    url = f"https://huggingface.co/{model_id}/raw/main/reproduce/reproduce.json"
    version = None
    generation = None
    source = None
    try:
        response = fetch_url(url)
        if response.status_code == 200:
            data = response.json()
            version, generation = _reproduce_version_info(data)
            source = _reproduce_source(data)
            metrics = _metrics_from_reproduce(data)
            if metrics is not None:
                kl_div, initial_refusals, refusals, refusal_rate = metrics
                return _row_from_metrics(model, kl_div, initial_refusals, refusals, refusal_rate,
                                         version, generation, source)
    except requests.exceptions.RequestException as e:
        logging.warning(f"Error fetching JSON for {model_id}: {e}")
    except (ValueError, KeyError, TypeError) as e:
        logging.warning(f"Formatting error in JSON for {model_id}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error processing JSON for {model_id}: {e}")
    return fetch_model_info(model, version=version, generation=generation, source=source)

# ---------------------------------------------------------------------------
# Two-stage cached loading (faster initial load)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def list_heretic_metadata():
    """Stage 1: HfApi only, no per-model fetch. Cheap and fast.

    Returns ALL models (including quants) with dates so the caller can
    pre-filter by date/query BEFORE the expensive per-model
    README/reproduce.json parsing.

    Date logic: `Created` prefers Hugging Face's `created_at` and falls back
    to `last_modified` when a model carries no creation date, so fewer models
    end up in the unknown-date bucket.
    """
    api = HfApi()
    # Query all models using the Hugging Face Hub `filter` parameter
    models = list(api.list_models(filter="heretic"))
    out = []
    for m in models:
        mid = m.id
        created = getattr(m, "created_at", None)
        modified = getattr(m, "last_modified", None)
        # Normalise to ISO strings (cache-safe, JSON-safe)
        try:
            created_iso = created.isoformat() if hasattr(created, "isoformat") else (str(created) if created else None)
        except Exception:
            created_iso = None
        try:
            modified_iso = modified.isoformat() if hasattr(modified, "isoformat") else (str(modified) if modified else None)
        except Exception:
            modified_iso = None
        # Fallback: last_modified stands in when created_at is missing.
        effective_created = created_iso or modified_iso
        out.append({
            "Model ID": mid,
            "Likes": getattr(m, "likes", 0) or 0,
            "Downloads": getattr(m, "downloads", 0) or 0,
            "URL": f"https://huggingface.co/{mid}",
            "Created": effective_created,
            "LastModified": modified_iso,
        })
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def cached_get_model_data_v2(model_id: str):
    """Stage 2: per-model reasoning cache, keyed by model_id ONLY.

    Popularity is merged afterwards via popularity_store's merge_popularity,
    so a like-spike doesn't invalidate the expensive KL/refusal parse.

    Renamed from `cached_get_model_data` to invalidate caches created before
    Heretic 2.x metadata support was added.
    """
    proxy = SimpleNamespace(id=model_id, likes=0, downloads=0)
    return get_model_data(proxy)


@st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour, back-compat shim
def get_heretic_models():
    """Fetches all heretic models and their metrics concurrently."""
    meta = list_heretic_metadata()
    data = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(
            lambda d: cached_get_model_data_v2(d["Model ID"]),
            meta,
        )
        for res in results:
            if res is not None:
                data.append(res)
    return data

# ---------------------------------------------------------------------------
# Filtering (pure, testable)
# ---------------------------------------------------------------------------
def _model_id_series(df: pd.DataFrame) -> pd.Series:
    col = "Model ID" if "Model ID" in df.columns else "Model"
    if col in df.columns:
        return df[col].astype("string")
    return pd.Series([""] * len(df), index=df.index, dtype="string")


def _parse_created(v):
    """Parse Created ISO string to aware datetime, or None."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, datetime):
        dt = v
    else:
        try:
            dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except Exception:
            return None
    if dt is not None and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def filter_metadata_by_date(metadata: list, date_range_key: str, unknowns_key: str = "Include unknowns") -> list:
    """Pre-filter raw metadata list by Created date BEFORE expensive parsing.

    Unknowns handling is now an explicit user choice (not silently kept):
    - "Include unknowns": keep models with missing Created date (old default).
    - "Hide unknowns": drop them — strictest, smallest parse set.
    - "Only unknowns": parse ONLY models with missing dates (audit mode).
    """
    days = DATE_OPTIONS.get(date_range_key, None)
    if unknowns_key not in UNKNOWN_OPTIONS:
        unknowns_key = "Include unknowns"
    if days is None and unknowns_key == "Include unknowns":
        return list(metadata)
    cutoff = None
    if days is not None:
        cutoff = datetime.now(timezone.utc) - pd.Timedelta(days=days).to_pytimedelta()
    kept = []
    for d in metadata:
        dt = _parse_created(d.get("Created"))
        if dt is None:
            if unknowns_key in ("Include unknowns", "Only unknowns"):
                kept.append(d)
            continue
        if unknowns_key == "Only unknowns":
            # Audit mode keeps ONLY undated models, even when date range is
            # "All time" — dated rows contradict the "unknowns" intent.
            continue
        if cutoff is None or dt >= cutoff:
            kept.append(d)
    return kept


def prefilter_metadata(metadata: list, query: str, show_quants: bool, date_range_key: str, unknowns_key: str = "Include unknowns") -> list:
    """Cheap pre-fetch filter: date (+unknowns handling) + quant + query. No network."""
    out = filter_metadata_by_date(metadata, date_range_key, unknowns_key)
    if not show_quants:
        out = [d for d in out if not QUANT_PATTERNS.search(d.get("Model ID", ""))]
    if query is not None:
        q = str(query).strip().lower()
        if q:
            out = [d for d in out if q in str(d.get("Model ID", "")).lower()]
    return out


def apply_filters(df, query, kl_range, refusal_range,
                  min_likes, min_downloads, show_quants, date_range="All time",
                  unknowns="Include unknowns", heretic_gen="All"):
    """Pure filter. Never mutates input. Handles empty df, NaNs, case-insensitive query."""
    if df is None or len(df) == 0:
        return df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    mask = pd.Series(True, index=df.index)
    if query is not None:
        q = str(query).strip()
        if q:
            ids = _model_id_series(df).fillna("")
            mask &= ids.str.contains(q, case=False, na=False, regex=False)
    if heretic_gen not in (None, "", "All") and "Heretic Gen" in df.columns:
        gens = df["Heretic Gen"].fillna("Unknown").astype(str)
        mask &= gens == str(heretic_gen)
    if kl_range is not None and "KL Divergence" in df.columns:
        try:
            lo, hi = float(kl_range[0]), float(kl_range[1])
            lo, hi = (hi, lo) if lo > hi else (lo, hi)
            kl = pd.to_numeric(df["KL Divergence"], errors="coerce")
            mask &= kl.between(lo, hi, inclusive="both")
        except (TypeError, ValueError, IndexError):
            pass
    if refusal_range is not None and "Refusal Rate (%)" in df.columns:
        try:
            lo, hi = float(refusal_range[0]), float(refusal_range[1])
            lo, hi = (hi, lo) if lo > hi else (lo, hi)
            rr = pd.to_numeric(df["Refusal Rate (%)"], errors="coerce")
            mask &= rr.between(lo, hi, inclusive="both")
        except (TypeError, ValueError, IndexError):
            pass
    for col, thresh in (("Likes", min_likes), ("Downloads", min_downloads)):
        if col in df.columns and thresh is not None:
            try:
                t = float(thresh)
            except (TypeError, ValueError):
                continue
            if pd.isna(t) or t <= 0:
                continue
            vals = pd.to_numeric(df[col], errors="coerce").fillna(0)
            mask &= vals >= t
    if not show_quants:
        ids = _model_id_series(df).fillna("")
        mask &= ~ids.str.contains(QUANT_RE, case=False, na=False, regex=True)
    # Date filter on Created column (post-fetch safety net; main saving is pre-fetch)
    days = DATE_OPTIONS.get(date_range, None)
    if unknowns not in UNKNOWN_OPTIONS:
        unknowns = "Include unknowns"
    if "Created" in df.columns and (days is not None or unknowns != "Include unknowns"):
        try:
            cutoff = None
            if days is not None:
                cutoff = datetime.now(timezone.utc) - pd.Timedelta(days=days).to_pytimedelta()
            parsed = df["Created"].apply(_parse_created)
            if unknowns == "Only unknowns":
                date_mask = parsed.apply(lambda dt: dt is None)
            elif unknowns == "Hide unknowns":
                if cutoff is None:
                    date_mask = parsed.apply(lambda dt: dt is not None)
                else:
                    date_mask = parsed.apply(lambda dt: dt is not None and dt >= cutoff)
            else:  # Include unknowns
                if cutoff is None:
                    date_mask = pd.Series(True, index=df.index)
                else:
                    date_mask = parsed.apply(lambda dt: True if dt is None else dt >= cutoff)
            mask &= date_mask.fillna(True).to_numpy() if hasattr(date_mask, "fillna") else date_mask
        except Exception:
            pass
    return df.loc[mask].copy().reset_index(drop=True)


def _qp_first(key, default=""):
    v = st.query_params.get(key, default)
    return v[0] if isinstance(v, list) and v else v


def _to_float(v, default):
    try:
        f = float(v)
        return f if not pd.isna(f) else default
    except (TypeError, ValueError):
        return default


def _to_int(v, default):
    try:
        return max(0, int(float(v)))
    except (TypeError, ValueError):
        return default


def init_filter_state_from_query_params():
    if st.session_state.get("_qp_init"):
        return
    d = FILTER_DEFAULTS
    kl_lo = _to_float(_qp_first("kl_min", d["kl_range"][0]), d["kl_range"][0])
    kl_hi = _to_float(_qp_first("kl_max", d["kl_range"][1]), d["kl_range"][1])
    rr_lo = _to_float(_qp_first("rr_min", d["refusal_range"][0]), d["refusal_range"][0])
    rr_hi = _to_float(_qp_first("rr_max", d["refusal_range"][1]), d["refusal_range"][1])
    st.session_state.setdefault("query", str(_qp_first("q", d["query"])))
    _dr = str(_qp_first("date_range", d["date_range"]))
    st.session_state.setdefault("date_range", _dr if _dr in DATE_OPTIONS else d["date_range"])
    _unk = str(_qp_first("unknowns", d["unknowns"]))
    st.session_state.setdefault("unknowns", _unk if _unk in UNKNOWN_OPTIONS else d["unknowns"])
    st.session_state.setdefault("kl_range", (min(kl_lo, kl_hi), max(kl_lo, kl_hi)))
    st.session_state.setdefault("refusal_range", (min(rr_lo, rr_hi), max(rr_lo, rr_hi)))
    st.session_state.setdefault("min_likes", _to_int(_qp_first("min_likes", d["min_likes"]), d["min_likes"]))
    st.session_state.setdefault("min_downloads", _to_int(_qp_first("min_downloads", d["min_downloads"]), d["min_downloads"]))
    st.session_state.setdefault("show_quants", str(_qp_first("show_quants", "")).lower() in ("1", "true", "yes"))
    _gen = str(_qp_first("heretic_gen", d["heretic_gen"]))
    st.session_state.setdefault("heretic_gen", _gen if _gen in HERETIC_GEN_OPTIONS else d["heretic_gen"])
    _lim = _normalise_scope_limit(_qp_first("scope_limit", d["scope_limit"]))
    st.session_state.setdefault("scope_limit", _lim)
    sort = str(_qp_first("sort_by", d["sort_by"]))
    st.session_state.setdefault("sort_by", sort if sort in SORT_OPTIONS else d["sort_by"])
    st.session_state["_qp_init"] = True


def sync_filter_state_to_query_params():
    st.query_params["q"] = st.session_state.get("query", "")
    st.query_params["date_range"] = str(st.session_state.get("date_range") or FILTER_DEFAULTS["date_range"])
    st.query_params["unknowns"] = str(st.session_state.get("unknowns") or FILTER_DEFAULTS["unknowns"])
    kl = st.session_state.get("kl_range", FILTER_DEFAULTS["kl_range"])
    rr = st.session_state.get("refusal_range", FILTER_DEFAULTS["refusal_range"])
    st.query_params["kl_min"] = str(float(kl[0]))
    st.query_params["kl_max"] = str(float(kl[1]))
    st.query_params["rr_min"] = str(float(rr[0]))
    st.query_params["rr_max"] = str(float(rr[1]))
    st.query_params["min_likes"] = str(int(st.session_state.get("min_likes", 0) or 0))
    st.query_params["min_downloads"] = str(int(st.session_state.get("min_downloads", 0) or 0))
    st.query_params["show_quants"] = "1" if st.session_state.get("show_quants") else "0"
    st.query_params["heretic_gen"] = str(st.session_state.get("heretic_gen") or FILTER_DEFAULTS["heretic_gen"])
    st.query_params["scope_limit"] = _normalise_scope_limit(st.session_state.get("scope_limit") or FILTER_DEFAULTS["scope_limit"])
    st.query_params["sort_by"] = str(st.session_state.get("sort_by") or FILTER_DEFAULTS["sort_by"])


def _normalise_scope_limit(value: str) -> str:
    v = str(value or "").strip()
    if v in SCOPE_LIMIT_OPTIONS:
        return v
    return SCOPE_ALIASES.get(v, "25 (Top past month)")


def _popularity_sort_key(d: dict) -> tuple:
    return (
        -int(d.get("Downloads") or 0),
        -int(d.get("Likes") or 0),
        str(d.get("Model ID") or "").lower(),
    )


def _apply_scope_limit(
    target_meta: list,
    all_metadata: list,
    scope_limit: str,
    show_quants: bool,
    query: str,
    unknowns: str = "Include unknowns",
) -> list:
    scope_limit = _normalise_scope_limit(scope_limit)
    try:
        from src.heretically_preloader import apply_scope_limit_new
        return apply_scope_limit_new(target_meta, all_metadata, scope_limit, show_quants, query, unknowns)
    except ImportError:
        try:
            from heretically_preloader import apply_scope_limit_new
            return apply_scope_limit_new(target_meta, all_metadata, scope_limit, show_quants, query, unknowns)
        except ImportError:
            pass
    limit_map = {
        "25 (Top past month)": 25,
        "10 (Trending 7d)": 10,
        "50": 50,
        "100": 100,
        "All": None,
    }
    n = limit_map.get(scope_limit, None)
    ordered = sorted(target_meta, key=_popularity_sort_key)
    if n is None:
        return ordered
    selected = ordered[:n]
    if scope_limit in ("25 (Top past month)", "10 (Trending 7d)") and len(selected) < n:
        seen = {d.get("Model ID") for d in selected}
        pool = prefilter_metadata(all_metadata, query, show_quants, "All time", unknowns)
        fill = sorted(
            (d for d in pool if d.get("Model ID") not in seen),
            key=_popularity_sort_key,
        )
        selected.extend(fill[: n - len(selected)])
    return selected


def _short(url: str) -> str:
    s = str(url)
    return s.split("huggingface.co/")[-1] if "huggingface.co/" in s else s


def _kl_thresholds(series):
    """Data-driven KL band cut-points: tertiles of the models currently in scope.

    Returns (t1, t2, t3) or None when the corpus is too small to adapt
    (then callers keep the static 0.01 / 0.05 / 0.15 bands).
    """
    try:
        values = pd.to_numeric(series, errors="coerce").dropna()
        values = values[values > 0]
    except Exception:
        return None
    if len(values) < 12:
        return None
    try:
        t1, t2, t3 = (float(q) for q in values.quantile([1 / 3, 2 / 3, 5 / 6]))
    except Exception:
        return None
    # Degenerate distribution (e.g. hundreds of identical values): fall back.
    if not (0 < t1 < t2 < t3):
        return None
    return (t1, t2, t3)


def _kl_band(kl, thresholds=None) -> str:
    """Rough weight-impact bands. Not a verdict — higher KL = more brain drift.

    `thresholds` (from _kl_thresholds) adapts the bands to the models in
    scope; None keeps the corpus-independent static bands.
    """
    if kl is None or (isinstance(kl, float) and pd.isna(kl)):
        return "unknown"
    try:
        kl = float(kl)
    except (TypeError, ValueError):
        return "unknown"
    if thresholds and all(isinstance(t, (int, float)) and t > 0 for t in thresholds):
        t1, t2, t3 = thresholds
    else:
        t1, t2, t3 = 0.01, 0.05, 0.15
    if kl < t1:
        return "minimal drift"
    if kl < t2:
        return "moderate drift"
    if kl < t3:
        return "high drift"
    return "very high drift"


def _sample_sizes(series):
    """Denominators (n) parsed out of Refusals strings like '3/30' -> 30.0."""
    sizes = [pd.NA if v is None else _parse_fraction(v)[1] for v in series]
    return pd.to_numeric(pd.Series(sizes, index=series.index), errors="coerce")


def _sample_floor(series) -> int:
    """"Small sample" floor adapted to this corpus: half the median n, min 20.

    0 refusals out of n=1200 means more than 0 out of n=30 — a static floor
    either over-warns big audit runs or under-warns tiny ones.
    """
    values = pd.to_numeric(series, errors="coerce").dropna()
    values = values[values > 0]
    if values.empty:
        return 50
    floor = max(20, round(float(values.median()) / 2))
    return int(floor)


def _compare_note(kl, ref_num, ref_den, init_num, init_den, sample_floor=50, kl_thresholds=None) -> str:
    """One-line grain-of-salt note per model. No trophies.

    `sample_floor` and `kl_thresholds` come from the models currently in
    scope so the thresholds adapt to the corpus being compared.
    """
    parts = []
    # Sample-size caution
    if ref_den is None:
        parts.append("unknown sample size — weak evidence")
    elif ref_den < 20:
        parts.append(f"very small sample (n={ref_den}) — take with grain of salt")
    elif ref_den < sample_floor:
        parts.append(f"small sample (n={ref_den} < floor {sample_floor}) — grain of salt")
    # Drop vs base
    if init_num is not None and ref_num is not None and init_den and ref_den:
        drop = init_num - ref_num
        parts.append(f"drop {drop} (base {init_num}/{init_den} → {ref_num}/{ref_den})")
    # KL vs refusal tradeoff — the core complaint: 0% refusal + high KL = stupid
    try:
        klf = float(kl) if kl is not None else None
    except (TypeError, ValueError):
        klf = None
    try:
        rate = (ref_num / ref_den * 100) if ref_num is not None and ref_den else None
    except ZeroDivisionError:
        rate = None
    if kl_thresholds and all(isinstance(t, (int, float)) and t > 0 for t in kl_thresholds):
        t1, t2, t3 = kl_thresholds
    else:
        t1, t2, t3 = 0.01, 0.05, 0.15
    if rate is not None and klf is not None:
        if rate == 0 and klf >= t3:
            parts.append("0 refusals BUT high drift vs this set — possibly lobotomized, check reasoning")
        elif rate == 0 and klf >= t2:
            parts.append("0 refusals with notable drift — verify quality")
        elif rate <= 5 and klf <= t1:
            parts.append("good balance: low refusal + low drift")
        elif rate > 20:
            parts.append("still refusal-prone, regardless of KL")
    elif klf is not None and klf >= t3:
        parts.append("high KL — expect reasoning damage")
    return "; ".join(parts) if parts else "—"


# ---------------------------------------------------------------------------
# Leaderboard scoring (pure, testable)
# ---------------------------------------------------------------------------
def _add_leaderboard_columns(df):
    """Derive the extra columns needed by leaderboard criteria."""
    if df is None or len(df) == 0:
        out = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
        out["Sample Size"] = pd.Series(dtype="float64")
        out["Refusal Drop"] = pd.Series(dtype="float64")
        out["Heretic 2.x"] = pd.Series(dtype="float64")
        return out

    out = df.copy()
    samples = []
    drops = []
    for _, row in out.iterrows():
        ref_num, ref_den = _parse_fraction(row.get("Refusals"))
        init_num, _ = _parse_fraction(row.get("Initial Refusals"))
        samples.append(float(ref_den) if ref_den is not None else None)
        drops.append(
            float(init_num - ref_num)
            if init_num is not None and ref_num is not None
            else None
        )
    out["Sample Size"] = samples
    out["Refusal Drop"] = drops
    if "Heretic Gen" in out.columns:
        out["Heretic 2.x"] = out["Heretic Gen"].map(
            {"2.x": 1.0, "Unknown": 0.5, "1.x": 0.0}
        ).fillna(0.5)
    else:
        out["Heretic 2.x"] = 0.5
    return out


def _percentile_score(series, higher_is_better=True):
    """Map a series to 0-100 percentile ranks; missing values become neutral 50."""
    values = pd.to_numeric(series, errors="coerce")
    valid_count = int(values.notna().sum())
    if valid_count == 0:
        return pd.Series(0.5, index=series.index, dtype="float64")
    ranks = values.rank(method="average", ascending=higher_is_better, na_option="keep")
    if valid_count > 1:
        scaled = (ranks - 1) / (valid_count - 1)
    else:
        scaled = ranks.apply(lambda value: 1.0 if pd.notna(value) else 0.5)
    return scaled.fillna(0.5)


def _score_leaderboard(df, weights):
    """Weighted percentile score (0-100) plus per-criterion sub-scores."""
    scored = df.copy()
    if "Sample Size" not in scored.columns:
        scored = _add_leaderboard_columns(scored)

    effective = {}
    for criterion in LEADERBOARD_CRITERIA:
        try:
            effective[criterion] = max(0.0, float(weights.get(criterion, 0) or 0))
        except (TypeError, ValueError):
            effective[criterion] = 0.0
    total_weight = sum(effective.values())

    score = pd.Series(0.0, index=scored.index, dtype="float64")
    if total_weight <= 0:
        scored["Priority Score"] = 50.0
        for criterion in LEADERBOARD_CRITERIA:
            scored[f"Priority: {criterion}"] = 50.0
        return scored

    for criterion, cfg in LEADERBOARD_CRITERIA.items():
        weight = effective[criterion]
        if weight <= 0:
            continue
        norm = _percentile_score(scored[cfg["column"]], cfg["higher_is_better"])
        scored[f"Priority: {criterion}"] = (norm * 100).round(1)
        score += norm * weight

    scored["Priority Score"] = (score / total_weight * 100).round(1)
    return scored


def _rank_leaderboard(df):
    ranked = df.sort_values("Priority Score", ascending=False, kind="mergesort").reset_index(drop=True)
    ranked.insert(0, "Rank", range(1, len(ranked) + 1))
    return ranked


# ---------------------------------------------------------------------------
# Main execution: metadata instantly, pre-filter by date, then parse subset
# ---------------------------------------------------------------------------
init_filter_state_from_query_params()


def _reset_filters():
    """Callback for Reset button — runs BEFORE widgets instantiate, so no
    StreamlitWidgetAlreadyInstantiatedError (the crash you saw)."""
    for k, v in FILTER_DEFAULTS.items():
        st.session_state[k] = v
    st.query_params.clear()
    st.session_state.metrics_done = False
    st.session_state.metrics_rows = []
    st.session_state.metrics_signature = None


if "metrics_done" not in st.session_state:
    st.session_state.metrics_done = False
if "metrics_rows" not in st.session_state:
    st.session_state.metrics_rows = []
if "metrics_signature" not in st.session_state:
    st.session_state.metrics_signature = None

try:
    from src.popularity_store import load_popularity, save_popularity, snapshot_from_metadata, merge_popularity
except ImportError:
    try:
        from popularity_store import load_popularity, save_popularity, snapshot_from_metadata, merge_popularity
    except ImportError:
        load_popularity = lambda: {}  # noqa: E731
        save_popularity = lambda m: ""  # noqa: E731
        snapshot_from_metadata = lambda md: {}  # noqa: E731
        merge_popularity = lambda rows, metadata, file_map=None: rows  # noqa: E731

# --- Integrated Main Interface Filter Toolbar (meta-page.html layout) ---
with st.container(border=True):
    tb1_search, tb1_sort, tb1_scope, tb1_reset = st.columns([2.2, 1.8, 1.5, 0.9], vertical_alignment="bottom")
    with tb1_search:
        early_query = st.text_input(
            "Search model ID",
            key="query",
            placeholder="e.g. kimi, qwen, llama-3 …",
            help="Case-insensitive substring applied before and after parsing.",
        )
    with tb1_sort:
        sort_by = st.selectbox("Sort by", list(SORT_OPTIONS.keys()), key="sort_by")
    with tb1_scope:
        scope_limit = st.selectbox(
            "Scope",
            list(SCOPE_LIMIT_OPTIONS),
            key="scope_limit",
            help="Default '25 (Top past month)' loads the top 25 weekly/monthly models by downloads/likes so the first screen is full.",
        )
    with tb1_reset:
        st.button("Reset filters", key="reset_filters", type="secondary", width="stretch", on_click=_reset_filters)

    st.markdown('<hr class="hairline-div">', unsafe_allow_html=True)

    tb2_date, tb2_unk, tb2_gen, tb2_quants = st.columns([1.85, 1.05, 1.2, 0.9], vertical_alignment="bottom")
    with tb2_date:
        early_date = st.segmented_control(
            "Release date",
            list(DATE_OPTIONS.keys()),
            key="date_range",
            selection_mode="single",
            help="Pre-filters by Hugging Face creation/modified date BEFORE parsing.",
        )
    with tb2_unk:
        early_unknowns = st.segmented_control(
            "Unknown dates",
            list(UNKNOWN_OPTIONS),
            key="unknowns",
            selection_mode="single",
            format_func=lambda opt: opt.replace(" unknowns", ""),
            help="Models with missing HF date: Include, Hide (strictest), or Only (audit mode).",
        )
    with tb2_gen:
        heretic_gen = st.segmented_control(
            "Heretic generation",
            list(HERETIC_GEN_OPTIONS),
            key="heretic_gen",
            selection_mode="single",
            help="2.x = Heretic 2.0+ (plugin reproduce.json v4). 1.x = legacy metadata.",
        )
    with tb2_quants:
        early_quants = st.toggle(
            "Include quantised",
            key="show_quants",
            help="Enable to include GGUF/MLX/AWQ/GPTQ/EXL2/EXL3/quant/INT8/INT4/OQ/MXFP4/MXFP8.",
        )

    early_date = early_date or FILTER_DEFAULTS["date_range"]
    early_unknowns = early_unknowns or FILTER_DEFAULTS["unknowns"]
    heretic_gen = heretic_gen or FILTER_DEFAULTS["heretic_gen"]

    with st.expander("⚙️ Metric filters & data refresh", expanded=False):
        mf1, mf2, mf3, mf4 = st.columns(4)
        with mf1:
            kl_range = st.slider(
                "KL Divergence",
                min_value=0.0, max_value=2.0, step=0.001, format="%.3f",
                key="kl_range",
            )
        with mf2:
            refusal_range = st.slider(
                "Refusal Rate (%)",
                min_value=0.0, max_value=100.0, step=0.5, format="%.1f",
                key="refusal_range",
            )
        with mf3:
            min_likes = st.number_input("Min likes", min_value=0, step=1, key="min_likes")
        with mf4:
            min_downloads = st.number_input("Min downloads", min_value=0, step=10, key="min_downloads")

        act1, act2, act3 = st.columns([1.2, 1.2, 2.0], vertical_alignment="center")
        with act1:
            refresh = st.button("🔄 Refresh metrics", type="primary", width="stretch")
        with act2:
            if st.button("🔄 Refresh popularity", type="secondary", width="stretch"):
                try:
                    _live = list_heretic_metadata()
                    _path = save_popularity(snapshot_from_metadata(_live))
                    st.success(f"Saved {len(_live)} entries to {_path or 'data/popularity.json'}")
                except Exception as e:
                    st.error(f"Could not save popularity: {e}")
        with act3:
            auto = st.checkbox("Auto-load metrics", value=True)
            try:
                _pop = load_popularity()
                st.caption(f"Popularity cache: {len(_pop)} models in data/popularity.json")
            except Exception:
                pass

try:
    with st.spinner("Fetching model list (fast metadata)..."):
        metadata = list_heretic_metadata()
except Exception as e:
    st.error(f"Could not list heretic models: {e}")
    st.stop()

# Cheap pre-filter BEFORE expensive parsing — plus trending/past-month fast boot.
raw_target_meta = prefilter_metadata(metadata, early_query, early_quants, early_date, early_unknowns)
target_meta = _apply_scope_limit(raw_target_meta, metadata, scope_limit, early_quants, early_query, early_unknowns)
st.markdown(
    f'<div class="scope-banner">'
    f'<div>'
    f'<div class="scope-banner-eyebrow">Pre-loader · Fast Boot</div>'
    f'<div class="scope-banner-title">Showing {html.escape(str(scope_limit))}</div>'
    f'<div class="scope-banner-text">Found <strong>{len(metadata):,}</strong> models in HF corpus (metadata cached 1h). '
    f'Scope <strong>{html.escape(str(early_date))}</strong> + <strong>{html.escape(str(early_unknowns))}</strong> '
    f'→ <strong>{len(target_meta)} queued to parse</strong> (from {len(raw_target_meta):,} matching).</div>'
    f'</div>'
    f'<div class="scope-banner-pill">'
    f'<span>Cold start · {len(target_meta)} parsed</span>'
    f'<strong>{html.escape(str(scope_limit))} · {html.escape(str(early_date))}</strong>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)
if len(target_meta) == 0:
    st.info("No models in this date/search scope — widen the date range, set Unknowns to Include, or clear search.")
    st.stop()
if len(target_meta) > 500:
    st.warning(
        f"Scope selects {len(target_meta)} models — parsing will take a while. "
        "Tip: pick '25 (Top past month)' or 'Last month', Hide unknowns, or add a search term."
    )

fetch_signature = (
    early_date,
    early_unknowns,
    early_query.strip().lower() if early_query else "",
    bool(early_quants),
    scope_limit,
    "heretic-version-metadata-v2",
)
if st.session_state.metrics_signature is not None and st.session_state.metrics_signature != fetch_signature:
    # Scope changed → old parsed rows no longer valid
    st.session_state.metrics_done = False
    st.session_state.metrics_rows = []

should_run = (auto and not st.session_state.metrics_done) or refresh
if refresh:
    st.session_state.metrics_done = False
    st.session_state.metrics_rows = []

created_map = {d["Model ID"]: d.get("Created") for d in target_meta}

if st.session_state.metrics_done and st.session_state.metrics_signature == fetch_signature:
    # Cached reasoning rows + FRESH popularity (file snapshot > live metadata),
    # so the KL/refusal cache stays valid while likes/downloads stay current.
    models_data = merge_popularity(
        [dict(r) for r in st.session_state.metrics_rows], target_meta
    )
    for r in models_data:
        r.setdefault("Created", created_map.get(r.get("Model ID")))
elif should_run:
    status_slot = st.empty()
    progress = st.progress(0)
    rows = []
    with status_slot.status("Fetching reproduce.json → README fallback...", expanded=False) as status:
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            fut_to_id = {
                ex.submit(cached_get_model_data_v2, d["Model ID"]): d["Model ID"]
                for d in target_meta
            }
            done = 0
            for fut in concurrent.futures.as_completed(fut_to_id):
                try:
                    res = fut.result()
                    if res is not None:
                        rows.append(res)
                except Exception as e:
                    logging.warning(f"Worker failed for {fut_to_id[fut]}: {e}")
                done += 1
                progress.progress(done / max(len(target_meta), 1))
                status.update(label=f"Parsed {done}/{len(target_meta)} — {len(rows)} with metrics...")
            status.update(label=f"Done: {len(rows)}/{len(target_meta)} with metrics", state="complete")
    # Merge Created dates + popularity (file snapshot > live metadata > parsed)
    merge_popularity(rows, target_meta)
    for r in rows:
        r.setdefault("Created", created_map.get(r.get("Model ID")))
    st.session_state.metrics_rows = rows
    st.session_state.metrics_done = True
    st.session_state.metrics_signature = fetch_signature
    progress.empty()
    status_slot.empty()
    models_data = rows
    st.rerun()
else:
    st.info("Tick Auto-load or press Refresh to fetch KL/Refusals.")
    st.stop()

if not models_data:
    st.warning("No models found with the 'heretic' tag in this scope.")
    st.stop()

df = pd.DataFrame(models_data)
# Backfill version metadata for rows cached before Heretic 2.x support was added
for _col, _default in (
    ("Heretic Version", "Unknown"),
    ("Heretic Gen", "Unknown"),
    ("Version Source", "heretic tag"),
):
    if _col not in df.columns:
        df[_col] = _default
    else:
        df[_col] = df[_col].fillna(_default).astype(str)
        df[_col] = df[_col].replace({"": _default, "None": _default, "nan": _default})
df["Heretic Gen"] = df.apply(
    lambda row: row["Heretic Gen"]
    if row["Heretic Gen"] in HERETIC_GEN_OPTIONS[1:]
    else _generation_label(row["Heretic Version"]),
    axis=1,
)
# Make Model ID a clickable link
df["Model"] = df["URL"]
# Select and order columns for display (Created kept for filtering, shown in table too)
cols = ["Model", "Heretic Version", "Heretic Gen", "KL Divergence", "Initial Refusals",
        "Refusals", "Refusal Rate (%)", "Version Source", "Likes", "Downloads"]
if "Created" in df.columns:
    cols.append("Created")
display_df = df[cols]

sync_filter_state_to_query_params()

query = st.session_state.get("query", "")
show_quants = st.session_state.get("show_quants", False)
date_range = st.session_state.get("date_range") or FILTER_DEFAULTS["date_range"]
unknowns = st.session_state.get("unknowns") or FILTER_DEFAULTS["unknowns"]
heretic_gen = st.session_state.get("heretic_gen") or FILTER_DEFAULTS["heretic_gen"]
filtered_df = apply_filters(display_df, query, kl_range, refusal_range, min_likes, min_downloads, show_quants, date_range, unknowns, heretic_gen)
sort_col, ascending = SORT_OPTIONS.get(sort_by, ("Downloads", False))
if sort_col == "Heretic Version" and "Heretic Version" in filtered_df.columns:
    filtered_df = (
        filtered_df.assign(_version_key=filtered_df["Heretic Version"].map(_version_sort_key))
        .sort_values("_version_key", ascending=ascending, kind="mergesort")
        .drop(columns=["_version_key"])
        .reset_index(drop=True)
    )
elif sort_col in filtered_df.columns:
    filtered_df = filtered_df.sort_values(sort_col, ascending=ascending, kind="mergesort").reset_index(drop=True)

try:
    import altair as alt
    _ALT_OK = True
except ImportError:
    alt = None  # type: ignore
    _ALT_OK = False


def _style_altair(chart):
    """Align Altair charts with meta-page.html warm-paper palette (#F7F4EE / #FDFBF7 / #C2410C)."""
    return (
        chart.configure(background="#F7F4EE")
        .configure_view(strokeWidth=0, fill="#FDFBF7")
        .configure_axis(
            gridColor="#E5E0D6",
            domainColor="#E5E0D6",
            tickColor="#E5E0D6",
            labelColor="#7B7266",
            titleColor="#5E554A",
            labelFont="JetBrains Mono, monospace",
            titleFont="Instrument Sans, sans-serif",
            labelFontSize=11,
            titleFontSize=12,
        )
        .configure_legend(
            labelColor="#5E554A",
            titleColor="#7B7266",
            labelFont="Instrument Sans, sans-serif",
            titleFont="JetBrains Mono, monospace",
        )
    )


# --- 4-Card KPI Summary Strip (meta-page.html style; ember reserved for Models in scope) ---
dynamic_kl_thresholds = _kl_thresholds(filtered_df["KL Divergence"])
dynamic_sample_floor = _sample_floor(_sample_sizes(filtered_df["Refusals"]))

_kl_med = pd.to_numeric(filtered_df["KL Divergence"], errors="coerce").median()
_ref_med = pd.to_numeric(filtered_df["Refusal Rate (%)"], errors="coerce").median()
_kl_med_str = f"{float(_kl_med):.4f}" if pd.notna(_kl_med) else "—"
_ref_med_str = f"{float(_ref_med):.1f}%" if pd.notna(_ref_med) else "—"
_kl_med_band = _kl_band(_kl_med, dynamic_kl_thresholds) if pd.notna(_kl_med) else "no KL data"

_n2 = int((display_df["Heretic Gen"] == "2.x").sum())
_n1 = int((display_df["Heretic Gen"] == "1.x").sum())
_nu = int((display_df["Heretic Gen"] == "Unknown").sum())
_pct_2x = f"{round((_n2 / max(len(display_df), 1)) * 100)}%"

st.markdown(
    f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Models in scope</div>
        <div class="kpi-value ember">{len(filtered_df)}</div>
        <div class="kpi-sub">of {len(display_df)} parsed · {len(metadata):,} in HF corpus</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Median KL</div>
        <div class="kpi-value">{_kl_med_str}</div>
        <div class="kpi-sub">{html.escape(_kl_med_band)} · tertile bands</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Median refusal</div>
        <div class="kpi-value">{_ref_med_str}</div>
        <div class="kpi-sub">small-sample floor n&lt;{dynamic_sample_floor}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Heretic 2.x</div>
        <div class="kpi-value">{_pct_2x}</div>
        <div class="kpi-sub">2.x: {_n2} · 1.x: {_n1} · Unknown: {_nu}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
# Keep screen-reader / test-friendly caption line cleanly integrated
st.caption(
    "Heretic metadata in parsed scope — "
    + " | ".join(
        f"**{gen}**: {int((display_df['Heretic Gen'] == gen).sum())}"
        for gen in ("2.x", "1.x", "Unknown")
    )
)

tab_table, tab_compare, tab_leaderboard = st.tabs(
    ["📊 Table", "⚖️ Compare", "🏆 Leaderboard"]
)

# 1. Table — editorial card frame + derived Refusal Drop & Sample Size
with tab_table:
    if filtered_df.empty:
        st.info("No models match the current filter.")
    else:
        table_df = _add_leaderboard_columns(filtered_df)
        ordered_cols = [
            c for c in (
                "Model", "KL Divergence", "Refusal Rate (%)", "Refusal Drop", "Sample Size",
                "Initial Refusals", "Refusals", "Likes", "Downloads",
                "Heretic Gen", "Heretic Version", "Version Source", "Created",
            ) if c in table_df.columns
        ]
        table_df = table_df[ordered_cols]
        st.markdown(
            f'<div class="section-bar">'
            f'<span class="section-bar-title">Models</span>'
            f'<span class="mono-note">Sorted by {html.escape(sort_by.lower())} · {len(table_df)} rows shown</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(
            table_df,
            column_config={
                "Model": st.column_config.LinkColumn("Model", display_text=r"https://huggingface\.co/(.*)"),
                "KL Divergence": st.column_config.NumberColumn("KL", format="%.4f"),
                "Refusal Rate (%)": st.column_config.NumberColumn("Refusal", format="%.1f%%"),
                "Refusal Drop": st.column_config.NumberColumn("Drop", format="%.0f"),
                "Sample Size": st.column_config.NumberColumn("Sample", format="%.0f"),
                "Initial Refusals": st.column_config.TextColumn("Base Refusals"),
                "Refusals": st.column_config.TextColumn("Final Refusals"),
                "Likes": st.column_config.NumberColumn("Likes", format="%d"),
                "Downloads": st.column_config.NumberColumn("Downloads", format="%d"),
                "Heretic Gen": st.column_config.TextColumn(
                    "Gen",
                    help="2.x = plugin-based metadata (reproduce.json schema v4); 1.x = legacy metadata.",
                ),
                "Heretic Version": st.column_config.TextColumn(
                    "Version",
                    help="Exact version from reproduce.json (environment.heretic.version) or the model card.",
                ),
                "Version Source": st.column_config.TextColumn(
                    "Source",
                    help="Where the Heretic version came from: reproduce.json, the model card, or only the heretic tag.",
                ),
                "Created": st.column_config.TextColumn("Created"),
            },
            hide_index=True,
            width='stretch',
        )
        st.markdown(
            '<div class="mono-note" style="margin-top: 0.35rem;">'
            'Numbers use tabular figures. KL bands adapt to models in scope (tertiles).'
            '</div>',
            unsafe_allow_html=True,
        )

# 2. Compare — up to 4, transposed, NO winner trophies
with tab_compare:
    if filtered_df.empty:
        st.info("No models to compare — adjust filter.")
    else:
        st.caption(
            "Grain of salt: a 0/x refusal alone proves little. "
            "A 30/30 → 0/30 on a tiny sample is weaker than 95/100 → 2/100, "
            "and zero refusals with high KL often means the weights got wrecked — "
            "uncensored but stupid. Read Refusal **with** KL + sample size."
        )
        if dynamic_kl_thresholds:
            t1, t2, t3 = dynamic_kl_thresholds
            st.caption(
                "Thresholds adapt to your current selection: KL tertiles "
                f"{t1:.3g} / {t2:.3g} / {t3:.3g} and small-sample floor n<{dynamic_sample_floor}."
            )
        else:
            st.caption(
                "Thresholds are static (KL bands 0.01 / 0.05 / 0.15; small-sample floor n<"
                f"{dynamic_sample_floor}) — too few models in scope to adapt them."
            )
        options = filtered_df["Model"].tolist()
        selected = st.multiselect(
            "Select up to 4 models to compare",
            options=options,
            default=options[:2] if len(options) >= 2 else options,
            max_selections=4,
            format_func=_short,
        )
        if len(selected) < 2:
            st.info("Select at least 2 models to compare.")
        else:
            comp = filtered_df[filtered_df["Model"].isin(selected)].set_index("Model").reindex(selected)
            comp["KL Divergence"] = pd.to_numeric(comp["KL Divergence"], errors="coerce")
            comp["Refusal Rate (%)"] = pd.to_numeric(comp["Refusal Rate (%)"], errors="coerce")
            # Per-model honest summary (no best_kl / best_ref verdicts)
            for m in selected:
                row = comp.loc[m]
                rn, rd = _parse_fraction(row.get("Refusals"))
                inn, ind = _parse_fraction(row.get("Initial Refusals"))
                note = _compare_note(
                    row.get("KL Divergence"), rn, rd, inn, ind,
                    sample_floor=dynamic_sample_floor,
                    kl_thresholds=dynamic_kl_thresholds,
                )
                band = _kl_band(row.get("KL Divergence"), dynamic_kl_thresholds)
                st.info(f"**{_short(m)}** — KL {band} | {note}")

            disp = comp.T.copy()
            disp.columns = [_short(c) for c in disp.columns]
            # Extra derived rows for honest comparison
            try:
                kl_vals = pd.to_numeric(comp["KL Divergence"], errors="coerce")
                disp.loc["KL band"] = [
                    _kl_band(v, dynamic_kl_thresholds) for v in kl_vals.reindex(selected).tolist()
                ]
            except Exception:
                pass
            try:
                drops = []
                for m in selected:
                    rn, rd = _parse_fraction(comp.loc[m].get("Refusals"))
                    inn, ind = _parse_fraction(comp.loc[m].get("Initial Refusals"))
                    drops.append(str(inn - rn) if inn is not None and rn is not None else "—")
                disp.loc["Refusal drop (base − final)"] = drops
            except Exception:
                pass
            try:
                ns = []
                for m in selected:
                    _, rd = _parse_fraction(comp.loc[m].get("Refusals"))
                    ns.append(str(rd) if rd is not None else "—")
                disp.loc["Sample size (n prompts)"] = ns
            except Exception:
                pass
            for metric in list(disp.index):
                for col_url, col_short in zip(selected, disp.columns):
                    v = comp.loc[col_url, metric] if metric in comp.columns else disp.loc[metric, col_short]
                    if pd.isna(v):
                        disp.loc[metric, col_short] = "—"
                    elif metric == "KL Divergence":
                        try:
                            disp.loc[metric, col_short] = f"{float(v):.4f}"
                        except (TypeError, ValueError):
                            disp.loc[metric, col_short] = str(v)
                    elif metric == "Refusal Rate (%)":
                        try:
                            disp.loc[metric, col_short] = f"{float(v):.2f}%"
                        except (TypeError, ValueError):
                            disp.loc[metric, col_short] = str(v)
                    elif metric in ("Likes", "Downloads"):
                        try:
                            disp.loc[metric, col_short] = f"{int(float(v)):,}"
                        except Exception:
                            disp.loc[metric, col_short] = str(v)
                    else:
                        disp.loc[metric, col_short] = str(v) if v is not None else "—"
            disp.index.name = "Metric"
            st.table(disp)


# 3. Leaderboard & Visual Analytics (merged Charts + Leaderboard)
with tab_leaderboard:
    st.subheader("🏆 Priority Leaderboard")
    st.caption(
        "Filter candidates and weight your evaluation priorities (percentile-normalized 0–100)."
    )
    if filtered_df.empty:
        st.info("No models in the current global filter — widen the filters first.")
    else:
        with st.expander("1. Filter candidates", expanded=True):
            lf1, lf2, lf3, lf4 = st.columns(4)
            with lf1:
                lb_gens = st.multiselect(
                    "Heretic generation",
                    list(HERETIC_GEN_OPTIONS[1:]),
                    default=list(HERETIC_GEN_OPTIONS[1:]),
                    key="lb_gens",
                )
            with lf2:
                lb_kl_default = float(
                    pd.to_numeric(filtered_df["KL Divergence"], errors="coerce").max() or 0.5
                )
                lb_max_kl = st.number_input(
                    "Max KL divergence",
                    min_value=0.0,
                    value=lb_kl_default,
                    step=0.001,
                    format="%.4f",
                    key="lb_max_kl",
                    help="Increase to include higher-divergence models.",
                )
            with lf3:
                lb_max_refusal = st.slider(
                    "Max refusal rate (%)", 0.0, 100.0, 100.0, 1.0, key="lb_max_refusal"
                )
            with lf4:
                lb_min_sample = st.number_input(
                    "Min sample size (n)", min_value=0, value=0, step=10, key="lb_min_sample"
                )

        lb_df = filtered_df.copy()
        if lb_gens:
            lb_df = lb_df[lb_df["Heretic Gen"].isin(lb_gens)]
        else:
            lb_df = lb_df.iloc[0:0]
        lb_df = lb_df[
            pd.to_numeric(lb_df["KL Divergence"], errors="coerce").fillna(float("inf")) <= lb_max_kl
        ]
        lb_df = lb_df[
            pd.to_numeric(lb_df["Refusal Rate (%)"], errors="coerce").fillna(100.0) <= lb_max_refusal
        ]
        lb_df = _add_leaderboard_columns(lb_df)
        if lb_min_sample > 0:
            lb_df = lb_df[
                pd.to_numeric(lb_df["Sample Size"], errors="coerce").fillna(0) >= lb_min_sample
            ]

        st.markdown("**2. Set your priorities**")
        st.caption("Weights are relative; set a criterion to 0 to ignore it.")
        leaderboard_weights = {}
        criteria_items = list(LEADERBOARD_CRITERIA.items())
        weight_rows = [dict(criteria_items[i:i + 4]) for i in range(0, len(criteria_items), 4)]
        for criterion_row in weight_rows:
            weight_cols = st.columns(4)
            for col_idx, (criterion, cfg) in enumerate(criterion_row.items()):
                slug = re.sub(r"[^a-z0-9]+", "_", criterion.lower()).strip("_")
                with weight_cols[col_idx]:
                    leaderboard_weights[criterion] = st.slider(
                        criterion,
                        min_value=0.0,
                        max_value=10.0,
                        value=float(cfg["default_weight"]),
                        step=0.5,
                        key=f"lb_weight_{slug}",
                        help=cfg.get("help"),
                    )

        active = {k: v for k, v in leaderboard_weights.items() if v > 0}
        if not active:
            st.warning("Give at least one priority a weight above 0 to build a leaderboard.")
        elif lb_df.empty:
            st.info("No models match these leaderboard filters.")
        else:
            lb_scored = _rank_leaderboard(_score_leaderboard(lb_df, leaderboard_weights))
            st.caption(
                "Active weights — "
                + " · ".join(f"{name}: {weight:g}" for name, weight in active.items())
            )

            # Editorial 2/3 + 1/3 Spotlight & Weights Overview (borrowed from meta-page.html)
            spot_left, spot_right = st.columns([1.85, 1.0], vertical_alignment="top")
            with spot_left:
                top_cards = []
                for idx_r, row_r in lb_scored.head(5).iterrows():
                    r_rank = int(row_r.get("Rank", idx_r + 1))
                    r_name = html.escape(_short(row_r.get("Model", "")))
                    r_score = float(row_r.get("Priority Score", 0.0) or 0.0)
                    r_kl = row_r.get("KL Divergence")
                    r_ref = row_r.get("Refusal Rate (%)")
                    r_drop = row_r.get("Refusal Drop")
                    kl_txt = f"{float(r_kl):.3f}" if pd.notna(r_kl) else "—"
                    ref_txt = f"{float(r_ref):.1f}%" if pd.notna(r_ref) else "—"
                    drop_txt = f"{float(r_drop):.0f}" if pd.notna(r_drop) else "—"
                    fill_cls = "top1" if r_rank == 1 else ""
                    top_cards.append(
                        f'<div class="lb-row">'
                        f'<div class="lb-row-top">'
                        f'<span class="lb-row-name"><span style="color:var(--muted);font-family:JetBrains Mono,monospace;margin-right:0.5rem;">#{r_rank}</span>{r_name}</span>'
                        f'<span class="lb-row-score">{r_score:.1f}</span>'
                        f'</div>'
                        f'<div class="lb-row-meta">KL {kl_txt} · Refusal {ref_txt} · Drop {drop_txt}</div>'
                        f'<div class="lb-bar-track"><div class="lb-bar-fill {fill_cls}" style="width:{max(2, min(100, r_score)):.1f}%;"></div></div>'
                        f'</div>'
                    )
                st.markdown(
                    '<div class="lb-card">'
                    '<div class="section-bar" style="margin-bottom:0.35rem;">'
                    '<span class="section-bar-title">Top Ranked Spotlight</span>'
                    '<span class="mono-note">Weighted score, 0–100</span>'
                    '</div>'
                    + "".join(top_cards)
                    + "</div>",
                    unsafe_allow_html=True,
                )

            with spot_right:
                max_w = max(active.values()) if active else 1.0
                w_rows = []
                for w_name, w_val in active.items():
                    pct_w = (w_val / max_w) * 100.0 if max_w > 0 else 0.0
                    w_rows.append(
                        f'<div style="margin-bottom:0.65rem;">'
                        f'<div style="display:flex;justify-content:space-between;font-size:0.82rem;">'
                        f'<span style="color:var(--secondary);">{html.escape(w_name)}</span>'
                        f'<span class="mono-note" style="color:var(--ink);">{w_val:g}</span>'
                        f'</div>'
                        f'<div class="lb-bar-track full"><div class="lb-bar-fill" style="width:{pct_w:.1f}%;"></div></div>'
                        f'</div>'
                    )
                st.markdown(
                    '<div class="lb-card">'
                    '<div class="section-bar" style="margin-bottom:0.6rem;">'
                    '<span class="section-bar-title">Active Weights</span>'
                    '<span class="mono-note">Relative priority</span>'
                    '</div>'
                    + "".join(w_rows)
                    + '<div class="mono-note" style="margin-top:0.5rem;">Percentile rank normalized per metric.</div>'
                    + "</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)

            size_col, subs_col = st.columns([1, 1])
            with size_col:
                size_choice = st.selectbox(
                    "Leaderboard size",
                    ["Top 10", "Top 25", "Top 50", "Top 100", "All"],
                    index=1,
                    key="lb_size",
                )
            with subs_col:
                show_subs = st.checkbox(
                    "Show priority sub-scores",
                    value=False,
                    key="lb_show_subs",
                )
            limit = {
                "Top 10": 10,
                "Top 25": 25,
                "Top 50": 50,
                "Top 100": 100,
                "All": None,
            }[size_choice]
            lb_view = lb_scored.head(limit) if limit is not None else lb_scored

            base_cols = [
                "Rank", "Model", "Priority Score", "Heretic Version", "Heretic Gen",
                "Version Source", "KL Divergence", "Initial Refusals", "Refusals",
                "Refusal Rate (%)", "Sample Size", "Refusal Drop", "Likes", "Downloads",
            ]
            sub_cols = [c for c in lb_view.columns if c.startswith("Priority: ")]
            lb_display = lb_view[base_cols + (sub_cols if show_subs else [])]

            st.dataframe(
                lb_display,
                column_config={
                    "Rank": st.column_config.NumberColumn("Rank", format="%d"),
                    "Model": st.column_config.LinkColumn(
                        "Model", display_text=r"https://huggingface\.co/(.*)"
                    ),
                    "Priority Score": st.column_config.NumberColumn(
                        "Priority Score", format="%.1f",
                        help="Weighted percentile score from 0 to 100.",
                    ),
                    "Heretic Version": st.column_config.TextColumn("Heretic Version"),
                    "Heretic Gen": st.column_config.TextColumn("Heretic Gen"),
                    "Version Source": st.column_config.TextColumn("Version Source"),
                    "KL Divergence": st.column_config.NumberColumn("KL Divergence", format="%.4f"),
                    "Initial Refusals": st.column_config.TextColumn("Initial Refusals"),
                    "Refusals": st.column_config.TextColumn("Refusals"),
                    "Refusal Rate (%)": st.column_config.NumberColumn("Refusal Rate (%)", format="%.2f%%"),
                    "Sample Size": st.column_config.NumberColumn("Sample Size", format="%.0f"),
                    "Refusal Drop": st.column_config.NumberColumn("Refusal Drop", format="%.0f"),
                    "Likes": st.column_config.NumberColumn("Likes"),
                    "Downloads": st.column_config.NumberColumn("Downloads"),
                    **{
                        col: st.column_config.NumberColumn(col, format="%.1f")
                        for col in sub_cols
                    },
                },
                hide_index=True,
                width='stretch',
            )
            st.download_button(
                "Download leaderboard CSV",
                data=lb_display.to_csv(index=False).encode("utf-8"),
                file_name="heretic_leaderboard.csv",
                mime="text/csv",
                key="lb_download",
            )

            with st.expander("📐 Directional Ablation Trade-off Matrix (Pareto Reference)", expanded=False):
                st.markdown(
                    r"""
The ideal Pareto frontier across directional ablation frameworks balances maximum refusal modulation against minimal capability degradation:
- **KL Divergence Cap ($\le 0.2$)**: First-token probability shift limit; keeps MMLU/ARC-C drop $< 1.0\%$ and Wikitext PPL shift $\le 0.1$.
- **Sweet-Spot Sample Size ($128 - 256$)**: Stabilizes Welford mean accumulation without exhausting VRAM (min viable: $32$ | max standard: $512$).
- **Refusal Rate Delta ($-85\%$ to $-95\%$)**: Multi-layer projected sweet spot (pushing $-100\%$ naive unclipped ablation on dense models destroys grammar).
- **Orthogonalization ($\lambda = 0.8 - 1.0$)**: Balances helpfulness vs. safety ($\lambda = 0.8$ jumps false-refusal compliance while keeping harmful compliance $< 6\%$).
                    """
                )

            with st.expander("📈 Corpus Distribution Charts", expanded=False):
                if not _ALT_OK:
                    st.warning("`altair` is not installed.")
                else:
                    chart_df = filtered_df.copy()
                    chart_df["Short"] = chart_df["Model"].astype(str).str.split("huggingface.co/").str[-1]
                    chart_df["KL Divergence"] = pd.to_numeric(chart_df["KL Divergence"], errors="coerce")
                    chart_df["Refusal Rate (%)"] = pd.to_numeric(chart_df["Refusal Rate (%)"], errors="coerce")
                    chart_df["Likes"] = pd.to_numeric(chart_df["Likes"], errors="coerce").fillna(0)
                    chart_df["Downloads"] = pd.to_numeric(chart_df["Downloads"], errors="coerce").fillna(0)
                    top20 = chart_df.nlargest(20, "Likes").sort_values("Refusal Rate (%)", ascending=True).dropna(subset=["Refusal Rate (%)"])
                    if not top20.empty:
                        st.markdown("**Refusal Rate per model (top 20 by Likes)**")
                        bars = _style_altair(
                            alt.Chart(top20)
                            .mark_bar(color="#5E554A", cornerRadiusTopRight=3, cornerRadiusBottomRight=3)
                            .encode(
                                x=alt.X("Refusal Rate (%):Q"),
                                y=alt.Y("Short:N", sort="-x", title="Model"),
                                tooltip=["Short:N", "Refusal Rate (%):Q", "KL Divergence:Q", "Likes:Q", "Downloads:Q"],
                            )
                        )
                        st.altair_chart(bars, width="stretch")
                    kl_df = chart_df.dropna(subset=["KL Divergence"])
                    if not kl_df.empty:
                        st.markdown("**Distribution of KL Divergence**")
                        hist = _style_altair(
                            alt.Chart(kl_df)
                            .mark_bar(color="#C2410C", cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
                            .encode(
                                x=alt.X("KL Divergence:Q", bin=alt.Bin(maxbins=20)),
                                y=alt.Y("count():Q", title="Models"),
                                tooltip=[alt.Tooltip("count():Q", title="Models")],
                            )
                        )
                        st.altair_chart(hist, width="stretch")

st.markdown(
    f'<footer class="heretic-footer">'
    f'Fork from Heretic Models Explorer · Inspired by @p-e-w Heretic and Heretic Grimoire · '
    f'KL bands: corpus tertiles · Sample floor: median/2, min {dynamic_sample_floor}'
    f'</footer>',
    unsafe_allow_html=True,
)
