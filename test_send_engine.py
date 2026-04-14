"""Test send_engine.py — run with: python3 test_send_engine.py"""
from src.clients import load_clients
from src.content_generator import generate_full_campaign_content
from src.send_engine import prepare_send_payload, simulate_send_campaign, log_send_result
from src.storage import load_campaign_log, save_json, _data

# Reset campaign log for clean test
save_json(_data("campaign_log.json"), [])

clients = load_clients()
content = generate_full_campaign_content("AI for agencies", clients, cta="Book a demo")
content["campaign_id"] = "test0001"

# 1 - prepare payload
payload = prepare_send_payload(content, clients)
assert payload["campaign_id"] == "test0001"
assert len(payload["groups"]) == 3
for g in payload["groups"]:
    assert len(g["recipients"]) == 3
    assert "subject" in g and "body" in g
print("prepare_send_payload OK")

# 2 - simulate send
record = simulate_send_campaign("test0001", content, clients)
assert record["campaign_id"] == "test0001"
assert record["send_status"] == "sent"
assert record["sent_count"] == 9
assert len(record["targeted_categories"]) == 3
for gr in record["group_results"]:
    assert gr["sent"] == 3
    for d in gr["deliveries"]:
        assert d["status"] == "simulated_sent"
        assert "@" in d["email"]
print("simulate_send_campaign OK")

# 3 - log result
log_send_result(record)
log = load_campaign_log()
assert len(log) == 1
assert log[0]["campaign_id"] == "test0001"
assert log[0]["sent_count"] == 9
print("log_send_result OK")

# Clean up
save_json(_data("campaign_log.json"), [])

print("ALL SEND_ENGINE TESTS PASSED")
