"""JSON file helpers for local data storage."""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


# ── Generic helpers ──────────────────────────────────────────

def load_json(path: str):
    """Load and return data from a JSON file. Returns [] on missing/corrupt file."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []


def save_json(path: str, data):
    """Write data to a JSON file (overwrites)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def append_json_record(path: str, record: dict):
    """Append a record to a JSON array file. Creates the file if missing."""
    existing = load_json(path)
    if not isinstance(existing, list):
        existing = []
    existing.append(record)
    save_json(path, existing)


# ── Typed convenience loaders ────────────────────────────────

def _data(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)


def load_clients() -> list[dict]:
    return load_json(_data("clients.json"))


def load_campaign_log() -> list[dict]:
    return load_json(_data("campaign_log.json"))


def load_generated_content() -> dict | list:
    return load_json(_data("generated_content.json"))


def load_performance_history() -> list[dict]:
    return load_json(_data("performance_history.json"))


def save_generated_content(data):
    save_json(_data("generated_content.json"), data)


def append_campaign_log(record: dict):
    append_json_record(_data("campaign_log.json"), record)


def append_performance_record(record: dict):
    append_json_record(_data("performance_history.json"), record)


def get_clients_by_category(category: str) -> list[dict]:
    """Filter clients list by category."""
    return [c for c in load_clients() if c.get("category") == category]


# ── Structured content storage ───────────────────────────────

MARKDOWN_DIR = os.path.join(DATA_DIR, "generated_markdown")


def _content_record(campaign_id: str, content: dict) -> dict:
    """Build a flat, serialisable record from a campaign content dict."""
    from datetime import datetime, timezone

    # Group newsletter versions by category ("persona")
    newsletters_by_persona: dict[str, dict] = {}
    for v in content.get("newsletter_versions", []):
        newsletters_by_persona[v["category"]] = {
            "subject": v.get("subject", ""),
            "body": v.get("body", ""),
            "clients": v.get("clients", []),
        }

    return {
        "campaign_id": campaign_id,
        "thesis": content.get("thesis", ""),
        "blog_title": content.get("thesis", ""),
        "blog_outline": content.get("blog_outline", ""),
        "blog_draft": content.get("blog_draft", ""),
        "newsletter_versions_by_persona": newsletters_by_persona,
        "linkedin_post": content.get("linkedin_post", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "edited": content.get("edited", False),
        "approved": content.get("approved", False),
    }


def save_generated_content_json(campaign_id: str, content: dict) -> dict:
    """Append a structured content record to data/generated_content.json.

    Returns the saved record.
    """
    record = _content_record(campaign_id, content)
    append_json_record(_data("generated_content.json"), record)
    return record


def save_generated_content_markdown(campaign_id: str, content: dict) -> str:
    """Write a human-readable Markdown file for one campaign.

    Saved to data/generated_markdown/{campaign_id}.md.
    Returns the file path.
    """
    os.makedirs(MARKDOWN_DIR, exist_ok=True)
    record = _content_record(campaign_id, content)

    lines = [
        f"# Campaign: {record['thesis']}",
        f"**Campaign ID:** {record['campaign_id']}  ",
        f"**Created:** {record['created_at']}  ",
        f"**Edited:** {record['edited']} | **Approved:** {record['approved']}",
        "",
        "---",
        "",
        "## Blog Outline",
        record["blog_outline"],
        "",
        "## Blog Draft",
        record["blog_draft"],
        "",
        "## Newsletter Versions",
    ]
    for persona, nl in record["newsletter_versions_by_persona"].items():
        lines.append(f"\n### {persona.replace('_', ' ').title()}")
        lines.append(f"**Subject:** {nl['subject']}  ")
        lines.append(f"{nl['body']}")

    lines += ["", "## LinkedIn Post", record["linkedin_post"], ""]

    path = os.path.join(MARKDOWN_DIR, f"{campaign_id}.md")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path


def load_generated_content_by_id(campaign_id: str) -> dict | None:
    """Load a single content record by campaign_id, or None."""
    records = load_json(_data("generated_content.json"))
    if not isinstance(records, list):
        return None
    for r in records:
        if r.get("campaign_id") == campaign_id:
            return r
    return None
