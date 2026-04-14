"""Tests for campaign logging: build_marketing_email_payload, create_campaign_log_record."""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from src.hubspot_client import build_marketing_email_payload, create_marketing_email_draft
from src.send_engine import create_campaign_log_record


# ── Sample data ──────────────────────────────────────────────

CAMPAIGN_CONTENT = {
    "campaign_id": "camp_001",
    "thesis": "AI in Healthcare",
    "newsletter_versions": [
        {"category": "established_prospects", "subject": "EP Subject", "body": "EP Body"},
        {"category": "emerging_clients", "subject": "EC Subject", "body": "EC Body"},
    ],
}

SEND_RESULTS = {
    "campaign_id": "camp_001",
    "thesis": "AI in Healthcare",
    "send_status": "sent",
    "send_time": "2026-04-14T12:00:00+00:00",
    "group_results": [
        {"category": "established_prospects", "subject": "EP Subject", "sent": 3,
         "deliveries": [{"email": "a@x.com", "status": "simulated_sent"}] * 3},
        {"category": "emerging_clients", "subject": "EC Subject", "sent": 2,
         "deliveries": [{"email": "b@x.com", "status": "simulated_sent"}] * 2},
    ],
}


# ── build_marketing_email_payload ────────────────────────────

def test_build_payload_list_format():
    payload = build_marketing_email_payload(CAMPAIGN_CONTENT, "established_prospects")
    assert payload["subject"] == "EP Subject", f"Got: {payload['subject']}"
    assert "Established Prospects" in payload["name"]
    assert payload["campaign_id"] == "camp_001"
    print("build_marketing_email_payload (list format) OK")


def test_build_payload_dict_format():
    content_dict = {
        **CAMPAIGN_CONTENT,
        "newsletter_versions_by_persona": {
            "established_prospects": {"subject": "EP Dict Sub", "body": "EP Dict Body"},
        },
    }
    del content_dict["newsletter_versions"]
    payload = build_marketing_email_payload(content_dict, "established_prospects")
    assert payload["subject"] == "EP Dict Sub", f"Got: {payload['subject']}"
    print("build_marketing_email_payload (dict format) OK")


def test_build_payload_missing_persona():
    payload = build_marketing_email_payload(CAMPAIGN_CONTENT, "general_audience")
    assert "AI in Healthcare" in payload["subject"]  # fallback subject
    print("build_marketing_email_payload (missing persona fallback) OK")


# ── create_marketing_email_draft (simulated) ─────────────────

def test_create_draft_simulated():
    payload = build_marketing_email_payload(CAMPAIGN_CONTENT, "established_prospects")
    result = create_marketing_email_draft(payload)
    assert result["success"] is True
    assert result["simulated"] is True
    assert "marketing/v3/emails" in result["endpoint"]
    assert len(result["returned_ids"]) == 1
    print("create_marketing_email_draft (simulated) OK")


# ── create_campaign_log_record ───────────────────────────────

def test_log_record():
    email_results = [
        {"persona": "established_prospects", "email_id": "sim_abc123",
         "endpoint": "https://api.hubapi.com/marketing/v3/emails", "simulated": True},
        {"persona": "emerging_clients", "email_id": "sim_def456",
         "endpoint": "https://api.hubapi.com/marketing/v3/emails", "simulated": True},
    ]
    records = create_campaign_log_record(CAMPAIGN_CONTENT, SEND_RESULTS, email_results)

    assert len(records) == 2, f"Expected 2 records, got {len(records)}"

    ep = records[0]
    assert ep["campaign_id"] == "camp_001"
    assert ep["blog_title"] == "AI in Healthcare"
    assert ep["persona"] == "established_prospects"
    assert ep["newsletter_id"] == "sim_abc123"
    assert ep["newsletter_subject"] == "EP Subject"
    assert ep["crm_mode"] == "mock"
    assert ep["send_status"] == "sent"
    assert ep["recipient_count"] == 3
    assert ep["hubspot_email_endpoint"] == "https://api.hubapi.com/marketing/v3/emails"
    assert ep["hubspot_email_id"] == "sim_abc123"

    ec = records[1]
    assert ec["persona"] == "emerging_clients"
    assert ec["recipient_count"] == 2
    print("create_campaign_log_record OK")


def test_log_record_no_email_results():
    records = create_campaign_log_record(CAMPAIGN_CONTENT, SEND_RESULTS, [])
    assert len(records) == 2
    assert records[0]["newsletter_id"] == ""
    assert records[0]["crm_mode"] == "mock"
    assert "hubspot_email_endpoint" not in records[0]
    print("create_campaign_log_record (no email results) OK")


if __name__ == "__main__":
    test_build_payload_list_format()
    test_build_payload_dict_format()
    test_build_payload_missing_persona()
    test_create_draft_simulated()
    test_log_record()
    test_log_record_no_email_results()
    print("\nALL CAMPAIGN LOG TESTS PASSED")
