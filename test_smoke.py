"""Quick smoke test — run with: python3 test_smoke.py"""
from src.clients import load_clients, get_all_categories, filter_clients_by_category, summarize_client_categories, get_default_target_list
from src.generate_content import (
    generate_blog_outline, generate_blog_draft,
    generate_newsletter, generate_newsletters_for_categories,
    generate_linkedin_post,
)
from src.analytics import simulate_campaign_metrics, generate_performance_summary, recommend_next_direction
from src.hubspot_client import sync_contacts, log_campaign
from src.storage import load_json, save_json, load_campaign_log, load_performance_history
from src.models import (
    make_campaign_input, make_client, make_generated_content,
    make_campaign_log, make_performance_record,
)
from src.prompts import (
    blog_outline_prompt, blog_draft_prompt, newsletter_prompt,
    linkedin_post_prompt, performance_summary_prompt, next_direction_prompt,
    CATEGORY_TONE,
)
from src.personas import PERSONAS

# -- Prompts --
p1 = blog_outline_prompt("AI workflows")
assert "AI workflows" in p1 and len(p1) > 50

p2 = blog_draft_prompt("AI workflows", "outline here")
assert "outline here" in p2

p3 = newsletter_prompt("AI workflows", "established_prospects", "scaling ops", "Book a demo")
assert "established_prospects" in p3 and "Book a demo" in p3
assert "direct and conversion" in p3

p4 = newsletter_prompt("AI workflows", "emerging_clients")
assert "educational" in p4

assert "LinkedIn" in linkedin_post_prompt("AI workflows")
assert len(CATEGORY_TONE) == 3
print("prompts OK")

# -- Content generation (mock) --
outline = generate_blog_outline("test thesis")
assert len(outline) > 0
draft = generate_blog_draft("test thesis", outline)
assert len(draft) > 0
nl = generate_newsletter("test thesis", "established_prospects", cta="Book demo")
assert "Book demo" in nl
nls = generate_newsletters_for_categories("test", ["established_prospects", "emerging_clients", "general_audience"])
assert len(nls) == 3 and nls[0]["category"] == "established_prospects"
lp = generate_linkedin_post("test thesis")
assert "#AI" in lp
print("generation OK")

# -- Models --
ci = make_campaign_input("Test thesis", audience_category="emerging_clients")
assert ci["thesis"] == "Test thesis" and len(ci["campaign_id"]) == 8
cl = make_client("Acme", "Jane", "j@acme.co", "established_prospects")
assert cl["category"] == "established_prospects"
gc = make_generated_content(ci["campaign_id"], ci["thesis"])
assert gc["edited"] is False
clog = make_campaign_log(ci["campaign_id"], ci["thesis"])
assert clog["send_status"] == "draft"
pr = make_performance_record(ci["campaign_id"], "emerging_clients", open_rate=42.0)
assert pr["open_rate"] == 42.0
print("models OK")

# -- Clients --
clients = load_clients()
assert len(clients) == 9
assert len(get_all_categories()) == 3
assert len(filter_clients_by_category("established_prospects")) == 3
assert summarize_client_categories(clients) == {"established_prospects": 3, "emerging_clients": 3, "general_audience": 3}
targets = get_default_target_list("emerging_clients")
assert len(targets) == 3
print("clients OK")

# -- Storage --
assert load_campaign_log() == []
assert load_performance_history() == []
print("storage OK")

# -- Analytics --
metrics = simulate_campaign_metrics(PERSONAS)
assert len(metrics) == 3
assert len(generate_performance_summary(metrics)) > 0
assert len(recommend_next_direction("AI workflows", metrics)) > 0
print("analytics OK")

# -- HubSpot mock --
sync_result = sync_contacts(clients[:1])
assert sync_result[0]["status"] == "mock_success"
print("hubspot OK")

print("ALL PASSED")
