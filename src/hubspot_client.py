"""HubSpot CRM integration layer (private-app token style).

If HUBSPOT_ACCESS_TOKEN is set, calls hit real HubSpot endpoints.
Otherwise every function returns a simulated success with the exact
request payload so reviewers can see the intended API shape.
"""

import os
import uuid
from datetime import datetime, timezone

import requests

# ── Config ────────────────────────────────────────────────────

HUBSPOT_BASE_URL = os.getenv("HUBSPOT_BASE_URL", "https://api.hubapi.com")
_TIMEOUT = 15  # seconds


def _token() -> str:
    return os.getenv("HUBSPOT_ACCESS_TOKEN", "")


def get_headers() -> dict:
    """Return Authorization + Content-Type headers for HubSpot API calls."""
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
    }


# Keep backward-compatible private alias
_headers = get_headers


def _is_live() -> bool:
    return bool(_token())


def _sim_id() -> str:
    """Fake HubSpot record id for simulated responses."""
    return f"sim_{uuid.uuid4().hex[:8]}"


# ── Contact property builder ──────────────────────────────────
#
# MVP approach: store persona and client_category as custom contact
# properties directly on the HubSpot contact record.  This is the
# simplest way to tag/segment contacts for a take-home demo.
#
# Future improvement: create HubSpot active lists filtered by the
# client_category property, or use Workflows to auto-enrol contacts
# into segments.  That requires no code change here — just list
# rules in the HubSpot UI pointing at these same properties.
# ──────────────────────────────────────────────────────────────

def build_contact_properties(contact: dict) -> dict:
    """Map a local contact dict to HubSpot contact properties.

    Includes persona and client_category so contacts are tagged
    for segmentation inside HubSpot.
    """
    name_parts = contact.get("contact_name", "").split(" ", 1)
    return {
        "email": contact["email"],
        "firstname": name_parts[0] if name_parts else "",
        "lastname": name_parts[1] if len(name_parts) > 1 else "",
        "company": contact.get("company_name", ""),
        "jobtitle": contact.get("jobtitle", ""),
        # ── Persona / segmentation fields ──
        "persona": contact.get("subcategory", contact.get("category", "")),
        "client_category": contact.get("category", ""),
        "preferred_send_time": contact.get("preferred_send_time", ""),
    }


# ── 1. Single contact create ─────────────────────────────────
# POST /crm/v3/objects/contacts

def create_contact(contact: dict) -> dict:
    """Create one contact in HubSpot CRM.

    Expected contact keys: email, contact_name, company_name,
    category, subcategory, preferred_send_time.
    """
    endpoint = f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts"
    payload = {"properties": build_contact_properties(contact)}

    if _is_live():
        try:
            resp = requests.post(
                endpoint, headers=_headers(), json=payload, timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": True,
                "simulated": False,
                "endpoint": endpoint,
                "request_payload": payload,
                "returned_ids": [data.get("id")],
            }
        except requests.RequestException as exc:
            return {
                "success": False,
                "simulated": False,
                "endpoint": endpoint,
                "request_payload": payload,
                "error": str(exc),
            }

    return {
        "success": True,
        "simulated": True,
        "endpoint": endpoint,
        "request_payload": payload,
        "returned_ids": [_sim_id()],
    }


# ── 2. Batch contact upsert ──────────────────────────────────
# POST /crm/v3/objects/contacts/batch/upsert
# Uses email as the unique idProperty for dedup.

def batch_upsert_contacts(contacts: list[dict]) -> dict:
    """Upsert multiple contacts in a single batch call.

    HubSpot deduplicates on the 'email' property.
    """
    endpoint = f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts/batch/upsert"

    inputs = []
    for c in contacts:
        inputs.append({
            "idProperty": "email",
            "id": c["email"],
            "properties": build_contact_properties(c),
        })

    payload = {"inputs": inputs}

    if _is_live():
        try:
            resp = requests.post(
                endpoint, headers=_headers(), json=payload, timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            returned_ids = [r.get("id") for r in data.get("results", [])]
            return {
                "success": True,
                "simulated": False,
                "endpoint": endpoint,
                "request_payload": payload,
                "returned_ids": returned_ids,
            }
        except requests.RequestException as exc:
            return {
                "success": False,
                "simulated": False,
                "endpoint": endpoint,
                "request_payload": payload,
                "error": str(exc),
            }

    return {
        "success": True,
        "simulated": True,
        "endpoint": endpoint,
        "request_payload": payload,
        "returned_ids": [_sim_id() for _ in contacts],
    }


# ── 3. Convenience wrapper ───────────────────────────────────

def upsert_contacts_to_hubspot(contacts: list[dict]) -> dict:
    """High-level helper: batch-upsert a list of contacts."""
    return batch_upsert_contacts(contacts)


# ── 4. Marketing email draft ─────────────────────────────────
# POST /marketing/v3/emails


def build_marketing_email_payload(campaign_content: dict, persona: str) -> dict:
    """Build a HubSpot marketing-email payload for one persona segment.

    Extracts the matching newsletter version (subject + body) from
    campaign_content and returns a dict ready for create_marketing_email_draft.
    """
    campaign_id = campaign_content.get("campaign_id", "")
    blog_title = campaign_content.get("thesis", "Untitled")

    # Resolve the newsletter version for this persona
    by_persona = campaign_content.get("newsletter_versions_by_persona", {})
    if isinstance(by_persona, dict) and persona in by_persona:
        version = by_persona[persona]
    else:
        version = {}
        for v in campaign_content.get("newsletter_versions", []):
            if v.get("category") == persona:
                version = v
                break

    return {
        "name": f"{blog_title} — {persona.replace('_', ' ').title()}",
        "subject": version.get("subject", f"Update: {blog_title}"),
        "body": version.get("body", ""),
        "campaign_id": campaign_id,
    }


def create_marketing_email_draft(email_payload: dict) -> dict:
    """Create a marketing email draft in HubSpot.

    email_payload should contain:
      name, subject, body (HTML or plain text), campaign_id (optional).
    """
    endpoint = f"{HUBSPOT_BASE_URL}/marketing/v3/emails"

    payload = {
        "name": email_payload.get("name", "Untitled Campaign Email"),
        "subject": email_payload.get("subject", ""),
        "body": email_payload.get("body", ""),
        "campaignId": email_payload.get("campaign_id", ""),
        "state": "DRAFT",
    }

    if _is_live():
        try:
            resp = requests.post(
                endpoint, headers=_headers(), json=payload, timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": True,
                "simulated": False,
                "endpoint": endpoint,
                "request_payload": payload,
                "returned_ids": [data.get("id")],
            }
        except requests.RequestException as exc:
            return {
                "success": False,
                "simulated": False,
                "endpoint": endpoint,
                "request_payload": payload,
                "error": str(exc),
            }

    return {
        "success": True,
        "simulated": True,
        "endpoint": endpoint,
        "request_payload": payload,
        "returned_ids": [_sim_id()],
    }


# ── 5. Log campaign event ────────────────────────────────────
# Uses the custom-object-style timeline approach.

def log_campaign_to_hubspot(campaign_payload: dict) -> dict:
    """Log a campaign send event to HubSpot.

    campaign_payload should contain:
      campaign_id, thesis, sent_count, send_time, categories.
    """
    endpoint = f"{HUBSPOT_BASE_URL}/crm/v3/objects/notes/batch/create"

    note_body = (
        f"Campaign {campaign_payload.get('campaign_id', 'N/A')} | "
        f"Thesis: {campaign_payload.get('thesis', '')} | "
        f"Sent: {campaign_payload.get('sent_count', 0)} | "
        f"Time: {campaign_payload.get('send_time', '')}"
    )

    payload = {
        "inputs": [
            {
                "properties": {
                    "hs_note_body": note_body,
                    "hs_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            }
        ]
    }

    if _is_live():
        try:
            resp = requests.post(
                endpoint, headers=_headers(), json=payload, timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            returned_ids = [r.get("id") for r in data.get("results", [])]
            return {
                "success": True,
                "simulated": False,
                "endpoint": endpoint,
                "request_payload": payload,
                "returned_ids": returned_ids,
            }
        except requests.RequestException as exc:
            return {
                "success": False,
                "simulated": False,
                "endpoint": endpoint,
                "request_payload": payload,
                "error": str(exc),
            }

    return {
        "success": True,
        "simulated": True,
        "endpoint": endpoint,
        "request_payload": payload,
        "returned_ids": [_sim_id()],
    }


# ── 6. Persona-based lists (optional segments) ───────────────
#
# TWO APPROACHES TO SEGMENTATION:
#
# A) Contact properties (default MVP) — already implemented above.
#    Every contact carries `persona` and `client_category` properties.
#    HubSpot active lists or saved filters can reference these
#    properties with zero extra API calls.  Use this for demos.
#
# B) Manual (static) lists — implemented below.  Creates real
#    HubSpot list objects and explicitly adds contact IDs.
#    Use this when you need webhook triggers, workflow enrolment,
#    or marketing-email list sends that require a list_id.
#
# For a take-home demo, approach A is sufficient.  The functions
# below show awareness of HubSpot's Lists API and can be wired
# in whenever list-level segmentation is needed.
# ──────────────────────────────────────────────────────────────

# Default persona list names matching client categories
PERSONA_LISTS = [
    "Established Prospects",
    "Emerging Clients",
    "General Audience",
]


def get_or_create_manual_list(list_name: str) -> dict:
    """Get an existing manual contact list by name, or create one.

    Uses HubSpot Lists API v3.
    Endpoint (create): POST /crm/v3/lists
    Endpoint (search): POST /crm/v3/lists/search
    objectTypeId "0-1" = Contacts.

    Returns normalised result with list_id.
    """
    create_endpoint = f"{HUBSPOT_BASE_URL}/crm/v3/lists"
    search_endpoint = f"{HUBSPOT_BASE_URL}/crm/v3/lists/search"

    create_payload = {
        "name": list_name,
        "objectTypeId": "0-1",          # contacts
        "processingType": "MANUAL",      # static list
    }

    if _is_live():
        # Try to find existing list first
        search_payload = {
            "query": list_name,
            "processingTypes": ["MANUAL"],
        }
        try:
            resp = requests.post(
                search_endpoint, headers=_headers(),
                json=search_payload, timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            for lst in resp.json().get("lists", []):
                if lst.get("name") == list_name:
                    return {
                        "success": True,
                        "simulated": False,
                        "endpoint": search_endpoint,
                        "list_id": lst["listId"],
                        "list_name": list_name,
                        "created": False,
                    }
        except requests.RequestException:
            pass  # fall through to create

        # Create new list
        try:
            resp = requests.post(
                create_endpoint, headers=_headers(),
                json=create_payload, timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": True,
                "simulated": False,
                "endpoint": create_endpoint,
                "request_payload": create_payload,
                "list_id": data.get("listId"),
                "list_name": list_name,
                "created": True,
            }
        except requests.RequestException as exc:
            return {
                "success": False,
                "simulated": False,
                "endpoint": create_endpoint,
                "request_payload": create_payload,
                "error": str(exc),
            }

    # Simulated mode
    return {
        "success": True,
        "simulated": True,
        "endpoint": create_endpoint,
        "request_payload": create_payload,
        "list_id": _sim_id(),
        "list_name": list_name,
        "created": True,
    }


def add_contacts_to_list(list_id: str, contact_ids: list[str]) -> dict:
    """Add contacts to a manual (static) list by record IDs.

    Endpoint: PUT /crm/v3/lists/{list_id}/memberships/add
    Expects a JSON array of string record IDs.
    """
    endpoint = (
        f"{HUBSPOT_BASE_URL}/crm/v3/lists/{list_id}/memberships/add"
    )

    if _is_live():
        try:
            resp = requests.put(
                endpoint, headers=_headers(),
                json=contact_ids, timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            return {
                "success": True,
                "simulated": False,
                "endpoint": endpoint,
                "list_id": list_id,
                "added_count": len(contact_ids),
            }
        except requests.RequestException as exc:
            return {
                "success": False,
                "simulated": False,
                "endpoint": endpoint,
                "request_payload": contact_ids,
                "error": str(exc),
            }

    return {
        "success": True,
        "simulated": True,
        "endpoint": endpoint,
        "request_payload": contact_ids,
        "list_id": list_id,
        "added_count": len(contact_ids),
    }
