"""Smoke test for hubspot_client.py (simulated mode)."""

from src.hubspot_client import (
    create_contact,
    batch_upsert_contacts,
    upsert_contacts_to_hubspot,
    create_marketing_email_draft,
    log_campaign_to_hubspot,
)

sample_contacts = [
    {"email": "alex@scaleup.io", "contact_name": "Alex Rivera", "company_name": "ScaleUp Agency", "category": "established_prospects"},
    {"email": "sam@novabrand.io", "contact_name": "Sam Chen", "company_name": "NovaBrand Studio", "category": "emerging_clients"},
]

# 1. create_contact
r = create_contact(sample_contacts[0])
assert r["success"] and r["simulated"]
assert r["endpoint"].endswith("/crm/v3/objects/contacts")
assert r["request_payload"]["properties"]["email"] == "alex@scaleup.io"
assert len(r["returned_ids"]) == 1
print("create_contact OK")

# 2. batch_upsert_contacts
r = batch_upsert_contacts(sample_contacts)
assert r["success"] and r["simulated"]
assert r["endpoint"].endswith("/crm/v3/objects/contacts/batch/upsert")
assert len(r["request_payload"]["inputs"]) == 2
assert r["request_payload"]["inputs"][0]["idProperty"] == "email"
assert len(r["returned_ids"]) == 2
print("batch_upsert_contacts OK")

# 3. upsert_contacts_to_hubspot (convenience)
r = upsert_contacts_to_hubspot(sample_contacts)
assert r["success"] and r["simulated"]
print("upsert_contacts_to_hubspot OK")

# 4. create_marketing_email_draft
r = create_marketing_email_draft({
    "name": "AI Workflow Newsletter",
    "subject": "Scale with AI",
    "body": "<p>Hello world</p>",
    "campaign_id": "abc123",
})
assert r["success"] and r["simulated"]
assert r["endpoint"].endswith("/marketing/v3/emails")
assert r["request_payload"]["state"] == "DRAFT"
print("create_marketing_email_draft OK")

# 5. log_campaign_to_hubspot
r = log_campaign_to_hubspot({
    "campaign_id": "abc123",
    "thesis": "AI helps agencies scale",
    "sent_count": 9,
    "send_time": "2026-04-14T12:00:00Z",
})
assert r["success"] and r["simulated"]
assert r["endpoint"].endswith("/crm/v3/objects/notes/batch/create")
assert "abc123" in r["request_payload"]["inputs"][0]["properties"]["hs_note_body"]
print("log_campaign_to_hubspot OK")

print("\nALL HUBSPOT CLIENT TESTS PASSED")
