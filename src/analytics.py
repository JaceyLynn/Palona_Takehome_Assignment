"""Campaign analytics — simulate metrics, summarise, recommend.

All simulation uses believable random ranges per category so demos
look realistic. The module is structured so OpenAI summaries can
replace the rule-based fallbacks later.
"""

import random
from collections import defaultdict
from datetime import datetime, timezone

from src.storage import append_performance_record as _append_record

# ── Realistic ranges per category ─────────────────────────────
# (min, max) tuples — established prospects engage more than general

_RANGES = {
    "established_prospects": {
        "open_rate": (40, 68),
        "click_rate": (10, 22),
        "unsubscribe_rate": (0.05, 0.8),
        "demo_clicks": (2, 8),
        "dwell_time_seconds": (45, 130),
        "linkedin_engagement_rate": (3.0, 9.0),
    },
    "emerging_clients": {
        "open_rate": (30, 55),
        "click_rate": (5, 15),
        "unsubscribe_rate": (0.2, 1.5),
        "demo_clicks": (1, 5),
        "dwell_time_seconds": (25, 90),
        "linkedin_engagement_rate": (2.0, 6.0),
    },
    "general_audience": {
        "open_rate": (18, 40),
        "click_rate": (2, 10),
        "unsubscribe_rate": (0.5, 3.0),
        "demo_clicks": (0, 3),
        "dwell_time_seconds": (10, 55),
        "linkedin_engagement_rate": (1.0, 4.5),
    },
}


def _rand(lo: float, hi: float, decimals: int = 1) -> float:
    return round(random.uniform(lo, hi), decimals)


# ── 1. Simulate metrics ──────────────────────────────────────

def simulate_performance_metrics(campaign_id: str,
                                  target_clients: list[dict]) -> list[dict]:
    """Return one metrics record per client category.

    Each record:
        campaign_id, category, open_rate, click_rate,
        unsubscribe_rate, demo_clicks, dwell_time_seconds,
        linkedin_engagement_rate, recorded_at
    """
    by_cat: dict[str, int] = defaultdict(int)
    for c in target_clients:
        by_cat[c.get("category", "general_audience")] += 1

    records = []
    for category, count in by_cat.items():
        r = _RANGES.get(category, _RANGES["general_audience"])
        records.append({
            "campaign_id": campaign_id,
            "category": category,
            "recipients": count,
            "open_rate": _rand(*r["open_rate"]),
            "click_rate": _rand(*r["click_rate"]),
            "unsubscribe_rate": _rand(*r["unsubscribe_rate"], decimals=2),
            "demo_clicks": random.randint(*r["demo_clicks"]),
            "dwell_time_seconds": _rand(*r["dwell_time_seconds"], decimals=0),
            "linkedin_engagement_rate": _rand(*r["linkedin_engagement_rate"]),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
    return records


# ── 2. Persist records ────────────────────────────────────────

def save_performance_records(records: list[dict]) -> None:
    """Append every record to data/performance_history.json."""
    for r in records:
        _append_record(r)


# ── 3. Rule-based summary ────────────────────────────────────

def summarize_performance_by_category(records: list[dict]) -> dict:
    """Return a human-readable summary dict.

    {
      "best_category": str,
      "worst_category": str,
      "by_category": {category: {open_rate, click_rate, ...}, ...},
      "summary_text": str,
    }
    """
    by_cat = {r["category"]: r for r in records}
    best = max(records, key=lambda r: r["open_rate"])
    worst = min(records, key=lambda r: r["open_rate"])

    text = (
        f"**Best performer:** {best['category'].replace('_', ' ')} "
        f"({best['open_rate']}% open, {best['click_rate']}% CTR, "
        f"{best['demo_clicks']} demo clicks).\n\n"
        f"**Lowest engagement:** {worst['category'].replace('_', ' ')} "
        f"({worst['open_rate']}% open, {worst['click_rate']}% CTR).\n\n"
        f"**LinkedIn:** Best engagement from "
        f"{max(records, key=lambda r: r['linkedin_engagement_rate'])['category'].replace('_', ' ')} "
        f"at {max(records, key=lambda r: r['linkedin_engagement_rate'])['linkedin_engagement_rate']}%."
    )

    return {
        "best_category": best["category"],
        "worst_category": worst["category"],
        "by_category": by_cat,
        "summary_text": text,
    }


# ── 4. Next-content recommendation ───────────────────────────

def recommend_next_content_direction(thesis: str,
                                      performance_summary: dict) -> str:
    """Suggest a next campaign direction based on performance.

    TODO: Replace rule-based logic with OpenAI call using
    next_direction_prompt(thesis, metrics) for richer output.
    """
    best = performance_summary["best_category"]
    worst = performance_summary["worst_category"]
    by_cat = performance_summary["by_category"]

    best_ctr = by_cat[best]["click_rate"]
    worst_open = by_cat[worst]["open_rate"]

    return (
        f"**Recommended next thesis:** Double down on content for "
        f"*{best.replace('_', ' ')}* — they had the highest engagement "
        f"({best_ctr}% CTR).\n\n"
        f"For *{worst.replace('_', ' ')}* ({worst_open}% open rate), "
        f"try a different angle: shorter subject lines, stronger hooks, "
        f"or a more educational tone.\n\n"
        f"Consider narrowing \"{thesis}\" to address the top segment's "
        f"specific pain points more directly."
    )


# ── 5. Full campaign report ──────────────────────────────────

def generate_campaign_report(campaign_id: str, thesis: str,
                              records: list[dict]) -> dict:
    """Build a complete report dict from raw metric records.

    Returns:
        {
          "campaign_id": str,
          "thesis": str,
          "metrics": [...],
          "summary": {best_category, worst_category, ...},
          "recommendation": str,
        }
    """
    summary = summarize_performance_by_category(records)
    recommendation = recommend_next_content_direction(thesis, summary)

    return {
        "campaign_id": campaign_id,
        "thesis": thesis,
        "metrics": records,
        "summary": summary,
        "recommendation": recommendation,
    }
