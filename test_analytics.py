"""Test analytics.py — run with: python3 test_analytics.py"""
from src.clients import load_clients
from src.analytics import (
    simulate_performance_metrics,
    save_performance_records,
    summarize_performance_by_category,
    recommend_next_content_direction,
    generate_campaign_report,
)
from src.storage import save_json, _data, load_performance_history

# Reset history for clean test
save_json(_data("performance_history.json"), [])

clients = load_clients()

# 1 - simulate metrics
records = simulate_performance_metrics("camp001", clients)
assert len(records) == 3
cats = {r["category"] for r in records}
assert cats == {"established_prospects", "emerging_clients", "general_audience"}
for r in records:
    assert r["campaign_id"] == "camp001"
    assert 0 < r["open_rate"] <= 100
    assert 0 <= r["click_rate"] <= 100
    assert r["demo_clicks"] >= 0
    assert r["dwell_time_seconds"] >= 0
    assert r["linkedin_engagement_rate"] >= 0
    assert "recorded_at" in r
print("simulate_performance_metrics OK")

# 2 - save records
save_performance_records(records)
history = load_performance_history()
assert len(history) == 3
print("save_performance_records OK")

# 3 - summarize
summary = summarize_performance_by_category(records)
assert summary["best_category"] in cats
assert summary["worst_category"] in cats
assert len(summary["by_category"]) == 3
assert "Best performer" in summary["summary_text"]
assert "LinkedIn" in summary["summary_text"]
print("summarize_performance_by_category OK")

# 4 - recommendation
rec = recommend_next_content_direction("AI for agencies", summary)
assert "Recommended next thesis" in rec
assert len(rec) > 50
print("recommend_next_content_direction OK")

# 5 - full report
report = generate_campaign_report("camp001", "AI for agencies", records)
assert report["campaign_id"] == "camp001"
assert report["thesis"] == "AI for agencies"
assert len(report["metrics"]) == 3
assert "best_category" in report["summary"]
assert len(report["recommendation"]) > 0
print("generate_campaign_report OK")

# Cleanup
save_json(_data("performance_history.json"), [])

print("ALL ANALYTICS TESTS PASSED")
