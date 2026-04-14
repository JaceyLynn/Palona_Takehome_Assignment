"""Smoke test for structured content storage helpers."""

import os
import json
from src.storage import (
    save_generated_content_json,
    save_generated_content_markdown,
    load_generated_content_by_id,
    DATA_DIR,
)

# Sample content dict matching generate_full_campaign_content output
sample = {
    "thesis": "AI helps agencies scale",
    "blog_outline": "1. Intro\n2. Problem\n3. Solution",
    "blog_draft": "# AI helps agencies scale\n\nDraft body here.",
    "newsletter_versions": [
        {
            "category": "established_prospects",
            "clients": ["c001"],
            "subject": "Scale with AI",
            "body": "Newsletter body for established.",
        },
        {
            "category": "emerging_clients",
            "clients": ["c004"],
            "subject": "Get started with AI",
            "body": "Newsletter body for emerging.",
        },
    ],
    "linkedin_post": "AI is the future. #marketing",
    "edited": False,
    "approved": False,
}

campaign_id = "test_001"

# -- 1. save JSON record --
record = save_generated_content_json(campaign_id, sample)
assert record["campaign_id"] == campaign_id
assert record["thesis"] == "AI helps agencies scale"
assert "established_prospects" in record["newsletter_versions_by_persona"]
assert "created_at" in record
print("save_generated_content_json OK")

# -- 2. save Markdown --
md_path = save_generated_content_markdown(campaign_id, sample)
assert os.path.exists(md_path)
with open(md_path) as f:
    md = f.read()
assert "# Campaign:" in md
assert "## Blog Outline" in md
assert "Established Prospects" in md
print(f"save_generated_content_markdown OK -> {md_path}")

# -- 3. load by id --
loaded = load_generated_content_by_id(campaign_id)
assert loaded is not None
assert loaded["campaign_id"] == campaign_id
print("load_generated_content_by_id OK")

# -- 4. missing id returns None --
assert load_generated_content_by_id("nonexistent_999") is None
print("load_generated_content_by_id (missing) OK")

# -- cleanup test record from generated_content.json --
gc_path = os.path.join(DATA_DIR, "generated_content.json")
with open(gc_path) as f:
    records = json.load(f)
records = [r for r in records if r.get("campaign_id") != campaign_id]
with open(gc_path, "w") as f:
    json.dump(records, f, indent=2)
os.remove(md_path)
print("\nALL STORAGE CONTENT TESTS PASSED")
