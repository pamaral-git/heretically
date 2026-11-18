"""Pure data layer for Heretically.

Everything here is in-memory only: no files, no database, no storage bucket.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from types import SimpleNamespace

import pandas as pd
import requests
from huggingface_hub import HfApi
from requests.adapters import HTTPAdapter
try:
    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )
except ImportError:
    # Fallback no-op decorator when tenacity is not installed
    def retry(*args, **kwargs):
        def decorator(f):
            return f
        return decorator
    retry_if_exception_type = lambda *args, **kwargs: None
    stop_after_attempt = lambda *args, **kwargs: None
    wait_exponential = lambda *args, **kwargs: None

logger = logging.getLogger(__name__)

HERETIC_VERSION_PATTERNS = (
    re.compile(r"(?i)made\s+(?:using|with)\s+\[heretic\]\([^)]*\)\s*v?([0-9][0-9a-z.+-]*)"),
    re.compile(r"(?i)made\s+(?:using|with)\s+heretic\s+v?([0-9][0-9a-z.+-]*)"),
    re.compile(r"(?i)(?:\[heretic\]\([^)]*\)|heretic-project\.org\)|github\.com/p-e-w/heretic\))\s*v?([0-9][0-9a-z.+-]*)"),
)

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

DISPLAY_COLUMNS = [
    "Rank",
    "Model ID",
    "Priority Score",
    "KL Divergence",
    "Refusal Rate (%)",
    "Refusals",
    "Initial Refusals",
    "Heretic Version",
    "Heretic Gen",
    "Sample Size",
    "Refusal Drop",
    "Likes",
    "Downloads",
    "URL",
]

_METADATA_TTL_SECONDS = 3600
_METADATA_CACHE = {"data": None, "ts": 0.0}
_METADATA_LOCK = threading.Lock()
_SESSION = None


def _get_session():
    global _SESSION
    if _SESSION is None:
        session = requests.Session()
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=0)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({"User-Agent": "Heretically-HF-Space/1.0"})
        _SESSION = session
    return _SESSION


@retry(
    retry=retry_if_exception_type(
        (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
        )
    ),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
def fetch_url(url):
    response = _get_session().get(url, timeout=(3.05, 10))
    if response.status_code in (429, 500, 502, 503, 504):
        response.raise_for_status()
    return response


def _parse_fraction(s) -> tuple:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return (None, None)
    match = re.search(r"(\d+)\s*/\s*(\d+)", str(s))
    if not match:
        return (None, None)
    try:
        return (int(match.group(1)), int(match.group(2)))
    except (ValueError, ZeroDivisionError):
        return (None, None)


def _to_float_or_none(v):
    try:
        value = float(v)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(value) else value


def _version_major(version):
    if version is None:
        return None
    match = re.match(r"\s*v?(\d+)", str(version))
    return int(match.group(1)) if match else None


def _generation_label(version=None, schema_version=None) -> str:
    major = _version_major(version)
    if major is not None:
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
    numbers = [int(n) for n in re.findall(r"\d+", str(version or ""))][:4]
    return tuple(numbers + [0] * (4 - len(numbers)))


def _extract_heretic_version(text):
    if not text:
        return None
    head = str(text)[:6000]
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


def _row_from_metrics(
    model,
    kl_div,
    initial_refusals,
    refusals,
    refusal_rate,
    version=None,
    generation=None,
    source=None,
):
    model_id = getattr(model, "id", None)
    return {
        "Model ID": model_id,
        "KL Divergence": float(kl_div),
        "Initial Refusals": initial_refusals,
        "Refusal Rate (%)": refusal_rate,
        "Refusals": refusals,
        "Heretic Version": version or "Unknown",
        "Heretic Gen": generation or _generation_label(version),
        "Version Source": source or "heretic tag",
        "Likes": getattr(model, "likes", 0) or 0,
        "Downloads": getattr(model, "downloads", 0) or 0,
        "URL": f"https://huggingface.co/{model_id}",
    }


def _layer_dict(entry, key):
    if not isinstance(entry, dict) or key is None:
        return {}
    value = entry.get(key)
    return value if isinstance(value, dict) else {}


def _entry_value(entry, key="score"):
    raw = entry.get(key) if isinstance(entry, dict) else None
    if isinstance(raw, dict):
        return _to_float_or_none(raw.get("value"))
    return _to_float_or_none(raw)


def _metrics_from_scores(scores):
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
    if refusal_entry is None:
        refusal_entry = classifier_entry
    if kl_entry is None or refusal_entry is None:
        return None

    kl_score = _layer_dict(kl_entry, "score")
    kl_div = _to_float_or_none(kl_score.get("value"))
    if kl_div is None:
        kl_div = _to_float_or_none(_display_text(kl_score))
    if kl_div is None:
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
                refusals = f"≈{round(value * 100)}/100"
        else:
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


def _parse_readme_metrics(text):
    if not text:
        return None
    kl_div = None
    refusals_str = None
    refusal_rate = None
    initial_refusals_str = None

    kl_match = re.search(r"(?i)KL\s*divergence[^a-zA-Z\d\n]*?([\d\.]+)", str(text))
    if kl_match:
        try:
            kl_div = float(kl_match.group(1))
        except ValueError:
            kl_div = None

    for line in str(text).split("\n"):
        line_lower = line.lower()
        if "refusals" not in line_lower:
            continue
        fractions = re.findall(r"(\d+)\s*/\s*(\d+)", line)
        if not fractions:
            continue
        if "initial" in line_lower and initial_refusals_str is None:
            initial_refusals_str = f"{fractions[0][0]}/{fractions[0][1]}"
            continue
        if refusals_str is not None:
            continue
        is_table_row = "|" in line
        is_prose_range = (
            "from" in line_lower and " to " in line_lower and len(fractions) >= 2
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
        except (ValueError, ZeroDivisionError):
            refusals_str = None
            refusal_rate = None
            continue
        if init_frac is not None and initial_refusals_str is None:
            initial_refusals_str = f"{init_frac[0]}/{init_frac[1]}"

    if kl_div is None or refusals_str is None:
        return None
    return kl_div, initial_refusals_str, refusals_str, refusal_rate


def fetch_model_info(model, version=None, generation=None, source=None):
    model_id = getattr(model, "id", None)
    if not model_id:
        return None
    readme_text = ""
    try:
        response = fetch_url(f"https://huggingface.co/{model_id}/raw/main/README.md")
        if response.status_code == 200:
            readme_text = response.text
    except requests.exceptions.RequestException as exc:
        logger.warning("Error fetching README for %s: %s", model_id, exc)
    except Exception as exc:
        logger.error("Unexpected error fetching README for %s: %s", model_id, exc)

    metrics = _parse_readme_metrics(readme_text)
    if metrics is None:
        return None
    kl_div, initial_refusals, refusals, refusal_rate = metrics

    if version is None:
        version = _extract_heretic_version(readme_text)
        if version is not None:
            generation = _generation_label(version)
            source = "model card"
    if generation is None:
        generation = _generation_label(version)

    return _row_from_metrics(
        model,
        kl_div,
        initial_refusals,
        refusals,
        refusal_rate,
        version,
        generation,
        source,
    )


def get_model_data(model):
    model_id = getattr(model, "id", None)
    if not model_id:
        return None
    version = None
    generation = None
    source = None
    try:
        response = fetch_url(
            f"https://huggingface.co/{model_id}/raw/main/reproduce/reproduce.json"
        )
        if response.status_code == 200:
            data = response.json()
            version, generation = _reproduce_version_info(data)
            source = _reproduce_source(data)
            metrics = _metrics_from_reproduce(data)
            if metrics is not None:
                kl_div, initial_refusals, refusals, refusal_rate = metrics
                return _row_from_metrics(
                    model,
                    kl_div,
                    initial_refusals,
                    refusals,
                    refusal_rate,
                    version,
                    generation,
                    source,
                )
    except requests.exceptions.RequestException as exc:
        logger.warning("Error fetching reproduce.json for %s: %s", model_id, exc)
    except (ValueError, KeyError, TypeError) as exc:
        logger.warning("Formatting error in reproduce.json for %s: %s", model_id, exc)
    except Exception as exc:
        logger.error("Unexpected error processing %s: %s", model_id, exc)
    return fetch_model_info(model, version, generation, source)


@lru_cache(maxsize=8192)
def _cached_model_data(model_id):
    proxy = SimpleNamespace(id=model_id, likes=0, downloads=0)
    return get_model_data(proxy)


def _iso(value):
    if value is None:
        return None
    try:
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
    except Exception:
        return None


def fetch_heretic_metadata(force_refresh=False):
    now = time.time()
    cached = _METADATA_CACHE.get("data")
    if (
        not force_refresh
        and cached is not None
        and now - _METADATA_CACHE.get("ts", 0.0) < _METADATA_TTL_SECONDS
    ):
        return cached

    with _METADATA_LOCK:
        cached = _METADATA_CACHE.get("data")
        if (
            not force_refresh
            and cached is not None
            and time.time() - _METADATA_CACHE.get("ts", 0.0) < _METADATA_TTL_SECONDS
        ):
            return cached

        try:
            api = HfApi()
            models = list(api.list_models(filter="heretic"))
        except Exception:
            if cached is not None:
                logger.warning("Metadata refresh failed; using stale in-memory cache")
                return cached
            raise

        out = []
        seen = set()
        for model in models:
            model_id = getattr(model, "id", None)
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            created = _iso(getattr(model, "created_at", None))
            modified = _iso(getattr(model, "last_modified", None))
            out.append(
                {
                    "Model ID": model_id,
                    "Likes": getattr(model, "likes", 0) or 0,
                    "Downloads": getattr(model, "downloads", 0) or 0,
                    "URL": f"https://huggingface.co/{model_id}",
                    "Created": created or modified,
                    "LastModified": modified,
                }
            )
        out.sort(key=lambda item: str(item["Model ID"]).lower())
        _METADATA_CACHE["data"] = out
        _METADATA_CACHE["ts"] = time.time()
        return out


def list_heretic_metadata():
    return fetch_heretic_metadata()


def _parse_created(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _trending_sort_key(item):
    return (
        -int(item.get("Downloads") or 0),
        -int(item.get("Likes") or 0),
        str(item.get("Model ID") or "").lower(),
    )


def select_trending(metadata, days=7, top_n=10, now=None):
    meta = list(metadata or [])
    if top_n is None or top_n <= 0:
        return []
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(days=days)

    recent = []
    rest = []
    for item in meta:
        created = _parse_created(item.get("Created")) or _parse_created(
            item.get("LastModified")
        )
        if created is not None and created >= cutoff:
            recent.append(item)
        else:
            rest.append(item)

    selected = sorted(recent, key=_trending_sort_key)[:top_n]
    if len(selected) < top_n:
        seen = {item.get("Model ID") for item in selected}
        fill = sorted(
            (item for item in rest if item.get("Model ID") not in seen),
            key=_trending_sort_key,
        )
        selected.extend(fill[: top_n - len(selected)])
    return selected


def load_models(metadata, max_workers=16):
    meta = [item for item in list(metadata or []) if item.get("Model ID")]
    if not meta:
        return [], {"attempted": 0, "parsed": 0}

    workers = max(1, min(int(max_workers or 1), len(meta)))
    rows = []
    attempted = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_cached_model_data, str(item["Model ID"])): item
            for item in meta
        }
        attempted = len(futures)
        for future in as_completed(futures):
            info = futures[future]
            try:
                row = future.result()
            except Exception as exc:
                logger.warning("Failed parsing %s: %s", info.get("Model ID"), exc)
                continue
            if row is None:
                continue
            row["Likes"] = int(info.get("Likes") or 0)
            row["Downloads"] = int(info.get("Downloads") or 0)
            row["Created"] = info.get("Created")
            row["LastModified"] = info.get("LastModified")
            row["URL"] = info.get("URL") or f"https://huggingface.co/{row['Model ID']}"
            rows.append(row)

    rows.sort(key=lambda item: str(item.get("Model ID") or "").lower())
    return rows, {"attempted": attempted, "parsed": len(rows)}


def load_trending(days=7, limit=10, max_workers=8, now=None, metadata=None):
    meta = fetch_heretic_metadata() if metadata is None else list(metadata)
    scope = select_trending(meta, days=days, top_n=limit, now=now)
    rows, stats = load_models(scope, max_workers=max_workers)
    stats.update(
        {
            "scope": "trending",
            "metadata_total": len(meta),
            "selected": len(scope),
            "days": days,
        }
    )
    return rows, stats


def load_all(max_workers=16, metadata=None):
    meta = fetch_heretic_metadata() if metadata is None else list(metadata)
    rows, stats = load_models(meta, max_workers=max_workers)
    stats.update(
        {
            "scope": "all",
            "metadata_total": len(meta),
            "selected": len(meta),
        }
    )
    return rows, stats


def clear_caches():
    _cached_model_data.cache_clear()
    with _METADATA_LOCK:
        _METADATA_CACHE["data"] = None
        _METADATA_CACHE["ts"] = 0.0


refresh_cache = clear_caches


def filter_by_query(df, query):
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)
    text = str(query or "").strip()
    if not text or "Model ID" not in df.columns:
        return df.copy()
    ids = df["Model ID"].astype("string")
    return df[ids.str.contains(text, case=False, na=False, regex=False)].copy()


def parse_top_n(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in ("", "all", "none"):
        return None
    try:
        return max(1, int(float(text)))
    except (TypeError, ValueError):
        return None


def _add_leaderboard_columns(df):
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
        out["Heretic 2.x"] = (
            out["Heretic Gen"].map({"2.x": 1.0, "Unknown": 0.5, "1.x": 0.0}).fillna(0.5)
        )
    else:
        out["Heretic 2.x"] = 0.5
    return out


def _percentile_score(series, higher_is_better=True):
    values = pd.to_numeric(series, errors="coerce")
    valid_count = int(values.notna().sum())
    if valid_count == 0:
        return pd.Series(0.5, index=series.index, dtype="float64")
    ranks = values.rank(
        method="average", ascending=higher_is_better, na_option="keep"
    )
    if valid_count > 1:
        scaled = (ranks - 1) / (valid_count - 1)
    else:
        scaled = ranks.apply(lambda value: 1.0 if pd.notna(value) else 0.5)
    return scaled.fillna(0.5)


def _score_leaderboard(df, weights):
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

    for criterion, config in LEADERBOARD_CRITERIA.items():
        weight = effective[criterion]
        if weight <= 0:
            continue
        column = config["column"]
        if column not in scored.columns:
            scored[column] = float("nan")
        norm = _percentile_score(scored[column], config["higher_is_better"])
        scored[f"Priority: {criterion}"] = (norm * 100).round(1)
        score += norm * weight

    scored["Priority Score"] = (score / total_weight * 100).round(1)
    return scored


def _rank_leaderboard(df):
    ranked = df.sort_values(
        "Priority Score", ascending=False, kind="mergesort"
    ).reset_index(drop=True)
    ranked.insert(0, "Rank", range(1, len(ranked) + 1))
    return ranked


def build_leaderboard(df, weights=None, top_n=None):
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)
    if weights is None:
        weights = {
            name: config["default_weight"]
            for name, config in LEADERBOARD_CRITERIA.items()
        }
    scored = _score_leaderboard(_add_leaderboard_columns(df), weights)
    ranked = _rank_leaderboard(scored)
    if top_n is not None:
        ranked = ranked.head(max(1, int(top_n)))
    columns = [column for column in DISPLAY_COLUMNS if column in ranked.columns]
    return ranked[columns].reset_index(drop=True)


def to_csv_bytes(df):
    if df is None or getattr(df, "empty", True):
        return b""
    return df.to_csv(index=False).encode("utf-8")
