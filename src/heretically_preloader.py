"""Heretically pre-loader fix — past month, more initial models. v2 (fixed).

Fixes over v1:
- Uses Created OR LastModified (matches hf_space/heretically_core.select_trending).
  A model with Created=None but LastModified 1 day ago IS recent, not undated.
- Unknowns handling matches app.py filter_metadata_by_date: Include / Hide / Only.
  Only truly undated models (both Created and LastModified missing) go to undated bucket.
- Backward compat: old deep-link scope_limit="25" maps to "25 (Top past month)",
  old "10" maps to "10 (Trending 7d)". Old links keep working.
- Single source: select_candidates(metadata, days, top_n, ...) is the same
  algorithm as core.select_trending, plus unknowns + quant + query.
"""
from datetime import datetime, timezone
import pandas as pd

PAST_MONTH_DAYS = 30
PAST_MONTH_N = 25

FILTER_DEFAULTS_PATCH = {
    "date_range": "Last month",
    "scope_limit": "25 (Top past month)",
}

SCOPE_LIMIT_OPTIONS_NEW = (
    "25 (Top past month)",
    "10 (Trending 7d)",
    "50",
    "100",
    "All",
)

# Old labels that may appear in shared URLs / query params.
SCOPE_ALIASES = {
    "25": "25 (Top past month)",
    "10": "10 (Trending 7d)",
}

SCOPE_LIMIT_COUNTS = {
    "25 (Top past month)": 25,
    "10 (Trending 7d)": 10,
    "50": 50,
    "100": 100,
    "All": None,
}


def normalise_scope_limit(value: str) -> str:
    v = str(value or "").strip()
    if v in SCOPE_LIMIT_OPTIONS_NEW:
        return v
    return SCOPE_ALIASES.get(v, "25 (Top past month)")


def _popularity_sort_key(d: dict) -> tuple:
    return (
        -int(d.get("Downloads") or 0),
        -int(d.get("Likes") or 0),
        str(d.get("Model ID") or "").lower(),
    )


def _parse_created_or_modified(d: dict):
    """Created or LastModified, aware datetime or None. Matches core."""
    for key in ("Created", "LastModified"):
        v = d.get(key)
        if v is None or (isinstance(v, float) and pd.isna(v)):
            continue
        if isinstance(v, datetime):
            dt = v
        else:
            try:
                dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
            except Exception:
                continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    return None


def select_candidates(all_metadata: list, days: int = PAST_MONTH_DAYS, top_n: int = PAST_MONTH_N,
                      query: str = "", show_quants: bool = False,
                      unknowns: str = "Include unknowns", now=None) -> list:
    """Same algorithm as core.select_trending, plus unknowns/quant/query."""
    import re
    quant_re = re.compile(r"(?i)(?:gguf|mlx|awq|nvfp4|gptq|exl[23]|-quant\b|int8|int4|oq[1-8]|mxfp[48])")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cutoff = now - pd.Timedelta(days=days).to_pytimedelta()
    recent, rest, undated = [], [], []
    for d in all_metadata or []:
        dt = _parse_created_or_modified(d)
        if dt is None:
            undated.append(d)
        elif dt >= cutoff:
            recent.append(d)
        else:
            rest.append(d)
    if unknowns == "Only unknowns":
        pool = undated
        fill_pool = []
    elif unknowns == "Hide unknowns":
        pool = recent
        fill_pool = rest
    else:  # Include unknowns — undated ride along in-window, as in app.py
        pool = recent + undated
        fill_pool = rest
    if not show_quants:
        pool = [d for d in pool if not quant_re.search(d.get("Model ID", ""))]
        fill_pool = [d for d in fill_pool if not quant_re.search(d.get("Model ID", ""))]
    q = (query or "").strip().lower()
    if q:
        pool = [d for d in pool if q in str(d.get("Model ID", "")).lower()]
        fill_pool = [d for d in fill_pool if q in str(d.get("Model ID", "")).lower()]
    selected = sorted(pool, key=_popularity_sort_key)[:top_n]
    if len(selected) < top_n:
        seen = {d.get("Model ID") for d in selected}
        fill = sorted((d for d in fill_pool if d.get("Model ID") not in seen),
                      key=_popularity_sort_key)
        selected.extend(fill[: top_n - len(selected)])
    return selected


def top_past_month_candidates(all_metadata: list, query: str = "", show_quants: bool = False,
                              unknowns: str = "Include unknowns", n: int = PAST_MONTH_N,
                              now=None) -> list:
    return select_candidates(all_metadata, days=PAST_MONTH_DAYS, top_n=n,
                             query=query, show_quants=show_quants,
                             unknowns=unknowns, now=now)


def apply_scope_limit_new(target_meta: list, all_metadata: list, scope_limit: str,
                          show_quants: bool, query: str, unknowns: str = "Include unknowns",
                          now=None) -> list:
    scope_limit = normalise_scope_limit(scope_limit)
    if scope_limit == "25 (Top past month)":
        return select_candidates(all_metadata, days=PAST_MONTH_DAYS, top_n=25,
                                 query=query, show_quants=show_quants,
                                 unknowns=unknowns, now=now)
    if scope_limit == "10 (Trending 7d)":
        return select_candidates(all_metadata, days=7, top_n=10,
                                 query=query, show_quants=show_quants,
                                 unknowns=unknowns, now=now)
    n = SCOPE_LIMIT_COUNTS.get(scope_limit)
    ordered = sorted(target_meta, key=_popularity_sort_key)
    return ordered if n is None else ordered[:n]


COLD_START_CAPTION = "Loading top 25 from the past month — by downloads, then likes."
