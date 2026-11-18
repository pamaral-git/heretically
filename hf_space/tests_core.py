import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import heretically_core as core

V1_PATH = Path("/tmp/opencode/v1.json")
V2_PATH = Path("/tmp/opencode/v2.json")
README_V1_PATH = Path("/tmp/opencode/readme_v1.md")
README_V2_PATH = Path("/tmp/opencode/readme_v2.md")

FALLBACK_V2 = {
    "version": "4",
    "environment": {"heretic": {"version": "2.0.0"}},
    "scores": [
        {
            "name": "refusal",
            "score": {"md_display": "0/100", "value": 0.0},
            "baseline": {"md_display": "98/100", "value": 0.98},
        },
        {
            "name": "kl_divergence",
            "score": {"md_display": "0.0338", "value": 0.03381050005555153},
        },
    ],
}

FALLBACK_V1 = {
    "version": "1",
    "environment": {"heretic": {"version": "1.2.0"}},
    "metrics": {
        "kl_divergence": 0.1692868173122406,
        "refusals": 14,
        "base_refusals": 99,
        "n_bad_prompts": 100,
    },
}

FALLBACK_README_V2 = "| Metric | Score | Baseline |\n|---|---|---|\n| Refusals | 0/100 | 98/100 |\n| KL divergence | 0.0338 | 0 |\n"
FALLBACK_README_V1 = "| Metric | Score | Baseline |\n|---|---|---|\n| Refusals | 40/100 | 93/100 |\n| KL divergence | 0.0171 | 0 |\n"


def load_json(path):
    if Path(path).exists():
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return FALLBACK_V2 if "v2" in str(path) else FALLBACK_V1


def test_helpers():
    assert core._parse_fraction("15/100") == (15, 100)
    assert core._parse_fraction(" 3 / 30 ") == (3, 30)
    assert core._parse_fraction(None) == (None, None)
    assert core._parse_fraction("no fraction") == (None, None)
    assert core._version_major("v2.0.0") == 2
    assert core._generation_label("2.0.0") == "2.x"
    assert core._generation_label("1.2.0") == "1.x"
    assert core._generation_label(None, 4) == "2.x"
    assert core._generation_label(None, "3") == "1.x"
    assert core._generation_label("3.1") == "Unknown"
    assert core._generation_label(None, None) == "Unknown"
    assert core._version_sort_key("2.0.1") == (2, 0, 1, 0)
    assert core._version_sort_key("1.2") == (1, 2, 0, 0)
    assert core._extract_heretic_version(
        "made using [Heretic](https://heretic-project.org) v2.0.0"
    ) == "2.0.0"
    assert core._extract_heretic_version("made using Heretic v1.2.0") == "1.2.0"
    assert core._extract_heretic_version("unrelated v9.9 text") is None
    assert core._to_float_or_none("0.5") == 0.5
    assert core._to_float_or_none(None) is None
    print("PASS helpers")


def test_reproduce_v2():
    data = load_json(V2_PATH)
    version, generation = core._reproduce_version_info(data)
    assert version == "2.0.0"
    assert generation == "2.x"
    assert core._reproduce_source(data) == "reproduce.json (schema v4)"
    metrics = core._metrics_from_reproduce(data)
    kl_div, initial_refusals, refusals, refusal_rate = metrics
    assert abs(kl_div - 0.03381050005555153) < 1e-15
    assert initial_refusals == "98/100"
    assert refusals == "0/100"
    assert refusal_rate == 0.0
    assert core._metrics_from_scores(data["scores"]) == metrics
    print("PASS reproduce v2")


def test_reproduce_v1():
    data = load_json(V1_PATH)
    version, generation = core._reproduce_version_info(data)
    assert version == "1.2.0"
    assert generation == "1.x"
    assert core._reproduce_source(data) == "reproduce.json (schema v1)"
    metrics = core._metrics_from_reproduce(data)
    kl_div, initial_refusals, refusals, refusal_rate = metrics
    assert abs(kl_div - 0.1692868173122406) < 1e-15
    assert initial_refusals == "99/100"
    assert refusals == "14/100"
    assert abs(refusal_rate - 14.0) < 1e-12
    assert core._metrics_from_legacy(data) == metrics
    print("PASS reproduce v1")


def test_row_from_metrics():
    data = load_json(V2_PATH)
    metrics = core._metrics_from_reproduce(data)
    model = SimpleNamespace(id="org/model", likes=12, downloads=345)
    row = core._row_from_metrics(
        model, *metrics, version="2.0.0", generation="2.x", source="reproduce.json"
    )
    assert row["Model ID"] == "org/model"
    assert row["Likes"] == 12
    assert row["Downloads"] == 345
    assert row["Heretic Gen"] == "2.x"
    assert row["URL"] == "https://huggingface.co/org/model"
    assert row["Refusals"] == "0/100"
    print("PASS row builder")


def test_readme_fallback():
    readme_v2 = (
        README_V2_PATH.read_text(encoding="utf-8")
        if README_V2_PATH.exists()
        else FALLBACK_README_V2
    )
    readme_v1 = (
        README_V1_PATH.read_text(encoding="utf-8")
        if README_V1_PATH.exists()
        else FALLBACK_README_V1
    )

    metrics_v2 = core._parse_readme_metrics(readme_v2)
    assert metrics_v2 is not None
    assert metrics_v2 == (0.0338, "98/100", "0/100", 0.0)
    assert core._parse_readme_metrics("no metrics here") is None
    metrics_v1 = core._parse_readme_metrics(readme_v1)
    assert metrics_v1 is not None
    assert metrics_v1 == (0.0171, "93/100", "40/100", 40.0)
    print("PASS README fallback")


def synthetic_frame():
    return pd.DataFrame(
        [
            {
                "Model ID": "best/model",
                "KL Divergence": 0.01,
                "Refusal Rate (%)": 0.0,
                "Refusals": "0/100",
                "Initial Refusals": "90/100",
                "Heretic Gen": "2.x",
                "Likes": 5,
                "Downloads": 20,
            },
            {
                "Model ID": "mid/model",
                "KL Divergence": 0.05,
                "Refusal Rate (%)": 10.0,
                "Refusals": "10/100",
                "Initial Refusals": "90/100",
                "Heretic Gen": "2.x",
                "Likes": 50,
                "Downloads": 500,
            },
            {
                "Model ID": "bad/model",
                "KL Divergence": 0.3,
                "Refusal Rate (%)": 60.0,
                "Refusals": "60/100",
                "Initial Refusals": "80/100",
                "Heretic Gen": "1.x",
                "Likes": 1,
                "Downloads": 5,
            },
        ]
    )


def test_percentiles():
    values = pd.Series([1.0, 2.0, 3.0], index=list("abc"))
    assert list(core._percentile_score(values, higher_is_better=True)) == [
        0.0,
        0.5,
        1.0,
    ]
    assert list(core._percentile_score(values, higher_is_better=False)) == [
        1.0,
        0.5,
        0.0,
    ]
    with_missing = pd.Series([5.0, None, 10.0], index=list("abc"))
    assert list(core._percentile_score(with_missing, higher_is_better=True)) == [
        0.0,
        0.5,
        1.0,
    ]
    print("PASS percentile scoring")


def test_leaderboard():
    frame = synthetic_frame()
    enriched = core._add_leaderboard_columns(frame)
    assert list(enriched["Sample Size"]) == [100.0, 100.0, 100.0]
    assert list(enriched["Refusal Drop"]) == [90.0, 80.0, 20.0]
    assert list(enriched["Heretic 2.x"]) == [1.0, 1.0, 0.0]

    ranked = core.build_leaderboard(frame, top_n=2)
    assert len(ranked) == 2
    assert list(ranked["Rank"]) == [1, 2]
    assert list(ranked["Model ID"]) == ["best/model", "mid/model"]
    assert ranked.loc[0, "Priority Score"] > ranked.loc[1, "Priority Score"]

    full = core.build_leaderboard(frame)
    assert list(full["Model ID"]) == ["best/model", "mid/model", "bad/model"]

    zero = core._score_leaderboard(
        core._add_leaderboard_columns(frame),
        {name: 0 for name in core.LEADERBOARD_CRITERIA},
    )
    assert list(zero["Priority Score"]) == [50.0, 50.0, 50.0]

    csv = core.to_csv_bytes(full)
    assert b"Model ID" in csv
    assert b"best/model" in csv
    assert core.to_csv_bytes(pd.DataFrame()) == b""
    print("PASS leaderboard scoring and CSV")


def test_query_and_top_n():
    frame = synthetic_frame()
    assert len(core.filter_by_query(frame, "mid")) == 1
    assert len(core.filter_by_query(frame, "MODEL")) == 3
    assert len(core.filter_by_query(frame, "")) == 3
    assert core.parse_top_n("10") == 10
    assert core.parse_top_n("All") is None
    assert core.parse_top_n("") is None
    assert core.parse_top_n("25") == 25
    print("PASS query and top-N helpers")


def test_trending():
    now = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
    metadata = []
    for i in range(12):
        metadata.append(
            {
                "Model ID": f"recent-{i:02d}",
                "Created": (now - timedelta(days=i % 5)).isoformat(),
                "LastModified": now.isoformat(),
                "Downloads": i * 100,
                "Likes": i,
            }
        )
    metadata.append(
        {
            "Model ID": "old-big",
            "Created": "2025-01-01T00:00:00+00:00",
            "LastModified": "2025-01-01T00:00:00+00:00",
            "Downloads": 999999,
            "Likes": 9999,
        }
    )

    selected = core.select_trending(metadata, days=7, top_n=10, now=now)
    assert len(selected) == 10
    ids = [item["Model ID"] for item in selected]
    assert "old-big" not in ids
    assert ids == [f"recent-{i:02d}" for i in range(11, 1, -1)]
    downloads = [item["Downloads"] for item in selected]
    assert downloads == sorted(downloads, reverse=True)

    few_recent = metadata[:3] + [
        {
            "Model ID": f"old-{i:02d}",
            "Created": "2025-01-01T00:00:00+00:00",
            "LastModified": "2025-01-01T00:00:00+00:00",
            "Downloads": i * 10,
            "Likes": i,
        }
        for i in range(10)
    ]
    filled = core.select_trending(few_recent, days=7, top_n=10, now=now)
    assert len(filled) == 10
    assert [item["Model ID"] for item in filled[:3]] == [
        "recent-02",
        "recent-01",
        "recent-00",
    ]
    assert len({item["Model ID"] for item in filled}) == 10
    assert filled[3]["Model ID"] == "old-09"

    assert core.select_trending([], days=7, top_n=10, now=now) == []
    undated = {
        "Model ID": "modified-only",
        "Created": None,
        "LastModified": (now - timedelta(days=1)).isoformat(),
        "Downloads": 1,
        "Likes": 0,
    }
    assert core.select_trending([undated], days=7, top_n=1, now=now) == [undated]
    print("PASS trending selection and fallback fill")


def main():
    test_helpers()
    test_reproduce_v2()
    test_reproduce_v1()
    test_row_from_metrics()
    test_readme_fallback()
    test_percentiles()
    test_leaderboard()
    test_query_and_top_n()
    test_trending()
    print("ALL CORE TESTS PASSED")


if __name__ == "__main__":
    main()
