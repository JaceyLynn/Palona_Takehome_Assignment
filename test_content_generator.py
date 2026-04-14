"""Test content_generator.py functions."""
from src.content_generator import (
    generate_blog_outline,
    generate_blog_draft,
    generate_newsletter_versions,
    generate_linkedin_post,
    generate_full_campaign_content,
)
from src.clients import load_clients

clients = load_clients()

# 1 - outline
o = generate_blog_outline("AI helps agencies scale")
assert o["thesis"] == "AI helps agencies scale"
assert "Introduction" in o["outline"]
print("outline OK")

# 2 - draft
d = generate_blog_draft(o["thesis"], o["outline"])
assert len(d["draft"]) > 100
assert d["outline"] == o["outline"]
print("draft OK")

# 3 - newsletters grouped by category
nv = generate_newsletter_versions("AI helps agencies scale", clients, cta="Book a demo")
assert nv["thesis"] == "AI helps agencies scale"
cats = {v["category"] for v in nv["versions"]}
assert cats == {"established_prospects", "emerging_clients", "general_audience"}
for v in nv["versions"]:
    assert len(v["clients"]) == 3
    assert len(v["subject"]) > 0
    assert len(v["body"]) > 0
print("newsletters OK")

# 4 - linkedin
lp = generate_linkedin_post("AI helps agencies scale", tone_notes="Keep it punchy")
assert "#AI" in lp["post"]
print("linkedin OK")

# 5 - full campaign
fc = generate_full_campaign_content("AI helps agencies scale", clients, cta="Book a demo")
assert fc["thesis"] == "AI helps agencies scale"
assert len(fc["blog_outline"]) > 0
assert len(fc["blog_draft"]) > 0
assert len(fc["newsletter_versions"]) == 3
assert len(fc["linkedin_post"]) > 0
assert fc["edited"] is False
assert fc["approved"] is False
print("full campaign OK")

print("ALL CONTENT_GENERATOR TESTS PASSED")
