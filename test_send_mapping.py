"""Test map_newsletters_to_target_clients with both content formats."""

from src.send_engine import map_newsletters_to_target_clients, simulate_send_campaign

# -- Sample data --
clients = [
    {"id": "c001", "contact_name": "Alex", "email": "alex@a.com", "category": "established_prospects", "preferred_send_time": "09:00"},
    {"id": "c002", "contact_name": "Sam",  "email": "sam@b.com",  "category": "emerging_clients", "preferred_send_time": "11:00"},
    {"id": "c003", "contact_name": "Jo",   "email": "jo@c.com",   "category": "established_prospects", "preferred_send_time": "08:30"},
]

# Format A: newsletter_versions (list)
content_list = {
    "campaign_id": "test_01",
    "thesis": "AI helps agencies",
    "newsletter_versions": [
        {"category": "established_prospects", "subject": "Scale with AI", "body": "Body EP"},
        {"category": "emerging_clients", "subject": "Start with AI", "body": "Body EC"},
    ],
}

# Format B: newsletter_versions_by_persona (dict)
content_dict = {
    "campaign_id": "test_02",
    "thesis": "AI helps agencies",
    "newsletter_versions_by_persona": {
        "established_prospects": {"subject": "Scale with AI", "body": "Body EP"},
        "emerging_clients": {"subject": "Start with AI", "body": "Body EC"},
    },
}

# -- Test with list format --
mapped = map_newsletters_to_target_clients(content_list, clients)
assert len(mapped) == 2
ep = [m for m in mapped if m["persona"] == "established_prospects"][0]
ec = [m for m in mapped if m["persona"] == "emerging_clients"][0]
assert ep["newsletter_subject"] == "Scale with AI"
assert ep["newsletter_body"] == "Body EP"
assert len(ep["recipients"]) == 2  # Alex + Jo
assert ec["newsletter_subject"] == "Start with AI"
assert len(ec["recipients"]) == 1  # Sam
assert ep["campaign_id"] == "test_01"
assert ep["blog_title"] == "AI helps agencies"
print("map_newsletters (list format) OK")

# -- Test with dict format --
mapped2 = map_newsletters_to_target_clients(content_dict, clients)
ep2 = [m for m in mapped2 if m["persona"] == "established_prospects"][0]
assert ep2["newsletter_subject"] == "Scale with AI"
assert ep2["blog_title"] == "AI helps agencies"
print("map_newsletters (dict format) OK")

# -- Test group_results now include subject --
record = simulate_send_campaign("test_01", content_list, clients)
for g in record["group_results"]:
    assert "subject" in g, f"Missing subject in group_results for {g['category']}"
ep_g = [g for g in record["group_results"] if g["category"] == "established_prospects"][0]
assert ep_g["subject"] == "Scale with AI"
assert ep_g["sent"] == 2
print("simulate_send_campaign (subject in group_results) OK")

print("\nALL MAP/SEND TESTS PASSED")
