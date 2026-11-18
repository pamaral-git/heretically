"""Tests for Heretically redesign — pre-loader, charts, derived columns.
Run: python3 tests_heretically_redesign.py
Style mirrors hf_space/tests_core.py: plain asserts, PASS lines, no pytest needed.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "hf_space"))

import heretically_preloader as pre
import heretically_charts as charts
import heretically_toolbar as toolbar


def test_scope_alias():
    assert pre.normalise_scope_limit("25") == "25 (Top past month)"
    assert pre.normalise_scope_limit("10") == "10 (Trending 7d)"
    assert pre.normalise_scope_limit("25 (Top past month)") == "25 (Top past month)"
    assert pre.normalise_scope_limit("bogus") == "25 (Top past month)"
    print("PASS scope alias / backward compat")


def test_preloader_past_month():
    now = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
    meta = []
    for i in range(12):
        meta.append({
            "Model ID": f"recent-{i:02d}",
            "Created": (now - timedelta(days=i % 5)).isoformat(),
            "LastModified": now.isoformat(),
            "Downloads": i * 100, "Likes": i,
        })
    meta.append({"Model ID": "old-big", "Created": "2025-01-01T00:00:00+00:00",
                 "LastModified": "2025-01-01T00:00:00+00:00",
                 "Downloads": 999999, "Likes": 9999})
    sel = pre.select_candidates(meta, days=30, top_n=10, now=now)
    assert len(sel) == 10
    ids = [d["Model ID"] for d in sel]
    assert "old-big" not in ids
    assert [d["Downloads"] for d in sel] == sorted([d["Downloads"] for d in sel], reverse=True)
    print("PASS preloader past month excludes old-big when enough recent")


def test_preloader_lastmodified_fallback():
    now = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
    meta = [{
        "Model ID": "modified-only", "Created": None,
        "LastModified": (now - timedelta(days=1)).isoformat(),
        "Downloads": 999, "Likes": 9,
    }]
    sel = pre.select_candidates(meta, days=30, top_n=1, now=now)
    assert sel == meta, "Created=None but LastModified recent must count as recent"
    print("PASS preloader Created-or-LastModified fallback")


def test_preloader_backfill():
    now = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
    few = [{"Model ID": f"recent-{i:02d}",
            "Created": (now - timedelta(days=i)).isoformat(),
            "LastModified": now.isoformat(),
            "Downloads": i * 10, "Likes": i} for i in range(3)]
    old = [{"Model ID": f"old-{i:02d}", "Created": "2025-01-01T00:00:00+00:00",
            "LastModified": "2025-01-01T00:00:00+00:00",
            "Downloads": i * 10, "Likes": i} for i in range(10)]
    filled = pre.select_candidates(few + old, days=30, top_n=10, now=now)
    assert len(filled) == 10
    assert len({d["Model ID"] for d in filled}) == 10
    assert filled[0]["Model ID"] == "recent-02"
    print("PASS preloader backfill")


def test_preloader_unknowns():
    now = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
    meta = [
        {"Model ID": "recent-00", "Created": now.isoformat(), "LastModified": now.isoformat(),
         "Downloads": 10, "Likes": 1},
        {"Model ID": "undated-00", "Created": None, "LastModified": None,
         "Downloads": 999, "Likes": 9},
    ]
    assert [d["Model ID"] for d in pre.select_candidates(meta, days=30, top_n=10, now=now, unknowns="Hide unknowns")] == ["recent-00"]
    assert [d["Model ID"] for d in pre.select_candidates(meta, days=30, top_n=10, now=now, unknowns="Only unknowns")] == ["undated-00"]
    print("PASS preloader unknowns Hide / Only")


def test_pareto_adaptive_domain():
    df = pd.DataFrame([
        {"Model ID": "best/model", "KL Divergence": 0.01, "Refusal Rate (%)": 0.0,
         "Likes": 5, "Downloads": 20},
        {"Model ID": "bad/model", "KL Divergence": 0.30, "Refusal Rate (%)": 60.0,
         "Likes": 1, "Downloads": 5},
    ])
    assert charts._adaptive_domain(df["KL Divergence"], 0.25) >= 0.30
    assert charts._adaptive_domain(df["Refusal Rate (%)"], 30.0) >= 60.0
    f = charts.pareto_frontier(df)
    assert list(f["Model ID"]) == ["best/model"]
    print("PASS pareto adaptive domain + frontier")


def test_percentile_matches_core():
    import heretically_core as core
    vals = pd.Series([1.0, 2.0, 3.0])
    assert list(core._percentile_score(vals, True)) == [0.0, 0.5, 1.0]
    assert list(charts._pct_core(vals, True)) == [0.0, 0.5, 1.0]
    print("PASS percentile matches core")


def test_derived_columns():
    df = pd.DataFrame([
        {"Model ID": "a/b", "KL Divergence": 0.02, "Refusal Rate (%)": 5.0,
         "Refusals": "5/100", "Initial Refusals": "90/100",
         "Likes": 10, "Downloads": 100, "Heretic Gen": "2.x", "Heretic Version": "2.0.0"},
    ])
    out = toolbar._ensure_derived(df)
    assert list(out["Sample Size"]) == [100]
    assert list(out["Refusal Drop"]) == [85.0]
    print("PASS derived Sample Size / Refusal Drop")


def main():
    test_scope_alias()
    test_preloader_past_month()
    test_preloader_lastmodified_fallback()
    test_preloader_backfill()
    test_preloader_unknowns()
    test_pareto_adaptive_domain()
    test_percentile_matches_core()
    test_derived_columns()
    print("ALL REDESIGN TESTS PASSED")


if __name__ == "__main__":
    main()
