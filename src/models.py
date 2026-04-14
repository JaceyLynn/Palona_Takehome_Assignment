"""Data model factories — plain dicts with sensible defaults.

Each make_* function returns a new dict you can save to JSON.
No classes or ORMs — just dictionaries for simplicity.
"""

import uuid
from datetime import datetime, timezone


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Campaign Input ───────────────────────────────────────────

def make_campaign_input(thesis: str, audience_category: str = "",
                        cta: str = "", tone_notes: str = "") -> dict:
    return {
        "campaign_id": _new_id(),
        "thesis": thesis,
        "audience_category": audience_category,
        "cta": cta,
        "tone_notes": tone_notes,
        "created_at": _now_iso(),
    }


# ── Client ───────────────────────────────────────────────────

def make_client(company_name: str, contact_name: str, email: str,
                category: str, subcategory: str = "",
                needs: str = "", preferred_send_time: str = "09:00") -> dict:
    return {
        "id": _new_id(),
        "company_name": company_name,
        "contact_name": contact_name,
        "email": email,
        "category": category,
        "subcategory": subcategory,
        "needs": needs,
        "preferred_send_time": preferred_send_time,
    }


# ── Generated Content ────────────────────────────────────────

def make_generated_content(campaign_id: str, thesis: str,
                           blog_outline: str = "", blog_draft: str = "",
                           newsletter_versions: list | None = None,
                           linkedin_post: str = "") -> dict:
    return {
        "campaign_id": campaign_id,
        "thesis": thesis,
        "blog_outline": blog_outline,
        "blog_draft": blog_draft,
        "newsletter_versions": newsletter_versions or [],
        "linkedin_post": linkedin_post,
        "edited": False,
        "approved": False,
        "created_at": _now_iso(),
    }


# ── Campaign Log ─────────────────────────────────────────────

def make_campaign_log(campaign_id: str, thesis: str,
                      targeted_categories: list | None = None,
                      content_version_ids: list | None = None) -> dict:
    return {
        "campaign_id": campaign_id,
        "thesis": thesis,
        "send_status": "draft",
        "send_time": None,
        "targeted_categories": targeted_categories or [],
        "content_version_ids": content_version_ids or [],
    }


# ── Performance Record ───────────────────────────────────────

def make_performance_record(campaign_id: str, category: str,
                            open_rate: float = 0.0, click_rate: float = 0.0,
                            unsubscribe_rate: float = 0.0,
                            demo_clicks: int = 0,
                            dwell_time_seconds: float = 0.0,
                            linkedin_engagement_rate: float = 0.0) -> dict:
    return {
        "campaign_id": campaign_id,
        "category": category,
        "open_rate": open_rate,
        "click_rate": click_rate,
        "unsubscribe_rate": unsubscribe_rate,
        "demo_clicks": demo_clicks,
        "dwell_time_seconds": dwell_time_seconds,
        "linkedin_engagement_rate": linkedin_engagement_rate,
        "recorded_at": _now_iso(),
    }
