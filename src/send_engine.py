"""Campaign send engine — simulate (or later, really send) emails.

All sends are simulated in this MVP. The module is structured so a
real integration (HubSpot, SendGrid, Zapier webhook) can replace
_deliver_to_client() without changing the public API.
"""

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from src.storage import append_campaign_log


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Resolve newsletter versions ──────────────────────────────

def _resolve_versions(campaign_content: dict) -> dict[str, dict]:
    """Return {category: {subject, body, ...}} from either format.

    Supports two shapes that appear in the codebase:
    - newsletter_versions_by_persona: {cat: {subject, body, ...}}
    - newsletter_versions: [{category, subject, body, ...}, ...]
    """
    by_persona = campaign_content.get("newsletter_versions_by_persona")
    if isinstance(by_persona, dict) and by_persona:
        return by_persona

    version_map: dict[str, dict] = {}
    for v in campaign_content.get("newsletter_versions", []):
        version_map[v["category"]] = v
    return version_map


# ── 1. Map newsletters to target clients ─────────────────────

def map_newsletters_to_target_clients(
    campaign_content: dict,
    target_clients: list[dict],
) -> list[dict]:
    """Group clients by persona and pair each group with its newsletter.

    Returns a list of per-persona send payloads:
        [
          {
            "campaign_id": str,
            "blog_title": str,
            "persona": str,
            "newsletter_subject": str,
            "newsletter_body": str,
            "recipients": [{id, contact_name, email, preferred_send_time}, ...],
          },
          ...
        ]
    """
    campaign_id = campaign_content.get("campaign_id", _new_id())
    blog_title = campaign_content.get("thesis", "")
    version_map = _resolve_versions(campaign_content)

    # Group clients by category (= persona segment)
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for c in target_clients:
        by_cat[c.get("category", "general_audience")].append(c)

    payloads = []
    for persona, clients in by_cat.items():
        version = version_map.get(persona, {})
        payloads.append({
            "campaign_id": campaign_id,
            "blog_title": blog_title,
            "persona": persona,
            "newsletter_subject": version.get("subject", f"Update: {blog_title}"),
            "newsletter_body": version.get("body", ""),
            "recipients": [
                {
                    "id": c["id"],
                    "contact_name": c.get("contact_name", ""),
                    "email": c["email"],
                    "preferred_send_time": c.get("preferred_send_time", "09:00"),
                }
                for c in clients
            ],
        })
    return payloads


# ── 2. Prepare send payload (legacy-compatible) ──────────────

def prepare_send_payload(campaign_content: dict,
                         target_clients: list[dict]) -> dict:
    """Build a structured payload ready for sending.

    Groups clients by category and pairs each group with its
    matching newsletter version from campaign_content.
    """
    campaign_id = campaign_content.get("campaign_id", _new_id())
    mapped = map_newsletters_to_target_clients(campaign_content, target_clients)

    groups = []
    for m in mapped:
        groups.append({
            "category": m["persona"],
            "subject": m["newsletter_subject"],
            "body": m["newsletter_body"],
            "recipients": m["recipients"],
        })

    return {
        "campaign_id": campaign_id,
        "thesis": campaign_content.get("thesis", ""),
        "groups": groups,
    }


# ── 2. Simulate sending ──────────────────────────────────────

def _deliver_to_client(recipient: dict, subject: str, body: str) -> dict:
    """Simulate delivering an email to one recipient.

    TODO: Replace with a real integration (e.g. HubSpot transactional
    email, SendGrid, or a Zapier webhook) for production use.
    """
    return {
        "email": recipient["email"],
        "status": "simulated_sent",
        "delivered_at": _now_iso(),
    }


def simulate_send_campaign(campaign_id: str,
                           campaign_content: dict,
                           target_clients: list[dict]) -> dict:
    """Run through the full send flow and return a campaign record.

    Each persona segment receives its own newsletter version.
    The returned record includes per-group subjects for easy auditing.
    """
    payload = prepare_send_payload(campaign_content, target_clients)

    group_results = []
    total_sent = 0

    for group in payload["groups"]:
        deliveries = []
        for r in group["recipients"]:
            result = _deliver_to_client(r, group["subject"], group["body"])
            deliveries.append(result)
        total_sent += len(deliveries)
        group_results.append({
            "category": group["category"],
            "subject": group["subject"],
            "sent": len(deliveries),
            "deliveries": deliveries,
        })

    return {
        "campaign_id": campaign_id,
        "thesis": payload["thesis"],
        "send_status": "sent",
        "send_time": _now_iso(),
        "targeted_categories": [g["category"] for g in payload["groups"]],
        "sent_count": total_sent,
        "group_results": group_results,
    }


# ── 3. Persist the log ───────────────────────────────────────

def log_send_result(campaign_record: dict) -> None:
    """Append a campaign record to data/campaign_log.json."""
    append_campaign_log(campaign_record)


# ── 4. Campaign log records (per-persona) ─────────────────────

def create_campaign_log_record(
    campaign_content: dict,
    send_results: dict,
    email_results: list[dict],
) -> list[dict]:
    """Build per-persona campaign log records for local + CRM storage.

    Each record captures: campaign_id, blog_title, send_date, persona,
    newsletter_id, newsletter_subject, crm_mode, send_status,
    recipient_count, and optional HubSpot email endpoint / id.
    """
    campaign_id = send_results.get("campaign_id", campaign_content.get("campaign_id", ""))
    blog_title = campaign_content.get("thesis", "")
    send_date = send_results.get("send_time", _now_iso())

    # Build a lookup from persona -> email_result
    email_lookup: dict[str, dict] = {}
    for er in email_results:
        email_lookup[er.get("persona", "")] = er

    records = []
    for group in send_results.get("group_results", []):
        persona = group["category"]
        er = email_lookup.get(persona, {})

        record = {
            "campaign_id": campaign_id,
            "blog_title": blog_title,
            "send_date": send_date,
            "persona": persona,
            "newsletter_id": er.get("email_id", ""),
            "newsletter_subject": group.get("subject", ""),
            "crm_mode": "live" if er.get("simulated") is False else "mock",
            "send_status": send_results.get("send_status", "sent"),
            "recipient_count": group.get("sent", 0),
        }

        # Attach HubSpot info when available
        if er.get("endpoint"):
            record["hubspot_email_endpoint"] = er["endpoint"]
        if er.get("email_id"):
            record["hubspot_email_id"] = er["email_id"]

        records.append(record)

    return records


def save_campaign_log_records(records: list[dict]) -> None:
    """Persist a list of campaign-log records to data/campaign_log.json."""
    for r in records:
        append_campaign_log(r)
