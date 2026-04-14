"""Smoke test for HubSpot list (segment) functions."""

from src.hubspot_client import (
    get_or_create_manual_list,
    add_contacts_to_list,
    PERSONA_LISTS,
)

# 1. PERSONA_LISTS constant
assert len(PERSONA_LISTS) == 3
assert "Established Prospects" in PERSONA_LISTS
print(f"PERSONA_LISTS OK: {PERSONA_LISTS}")

# 2. get_or_create_manual_list (simulated)
for name in PERSONA_LISTS:
    r = get_or_create_manual_list(name)
    assert r["success"] and r["simulated"]
    assert r["list_name"] == name
    assert r["created"] is True
    assert r["list_id"].startswith("sim_")
    assert r["endpoint"].endswith("/crm/v3/lists")
    assert r["request_payload"]["objectTypeId"] == "0-1"
    assert r["request_payload"]["processingType"] == "MANUAL"
print("get_or_create_manual_list OK (all 3 persona lists)")

# 3. add_contacts_to_list (simulated)
fake_ids = ["sim_aaa", "sim_bbb", "sim_ccc"]
r = add_contacts_to_list("sim_list_001", fake_ids)
assert r["success"] and r["simulated"]
assert r["list_id"] == "sim_list_001"
assert r["added_count"] == 3
assert "/memberships/add" in r["endpoint"]
assert r["request_payload"] == fake_ids
print("add_contacts_to_list OK")

# 4. empty list
r = add_contacts_to_list("sim_list_002", [])
assert r["success"] and r["added_count"] == 0
print("add_contacts_to_list (empty) OK")

print("\nALL LIST/SEGMENT TESTS PASSED")
