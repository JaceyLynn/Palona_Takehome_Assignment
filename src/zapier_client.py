"""Lightweight Zapier webhook client.

If ZAPIER_WEBHOOK_URL is set, sends a real POST to the webhook.
Otherwise falls back to a simulated/demo success response.
"""

import os
import uuid
from datetime import datetime, timezone

import requests

def _is_live() -> bool:
    """Return True when a real webhook URL is configured."""
    return bool(os.getenv("ZAPIER_WEBHOOK_URL"))


def launch_zapier_workflow(payload: dict) -> dict:
    """Send *payload* to the Zapier webhook and return a normalised result.

    Returns a dict with keys:
        success      – bool
        status_code  – int  (200 for simulated)
        message      – str
        request_id   – str  (UUID for traceability)
        launched_at  – str  (ISO-8601 UTC timestamp)
        simulated    – bool (True when no real webhook is configured)
    """
    request_id = uuid.uuid4().hex
    launched_at = datetime.now(timezone.utc).isoformat()
    webhook_url = os.getenv("ZAPIER_WEBHOOK_URL")

    if not webhook_url:
        return {
            "success": True,
            "status_code": 200,
            "message": "Simulated — no ZAPIER_WEBHOOK_URL configured",
            "request_id": request_id,
            "launched_at": launched_at,
            "simulated": True,
        }

    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            timeout=15,
            headers={"Content-Type": "application/json"},
        )
        return {
            "success": resp.ok,
            "status_code": resp.status_code,
            "message": resp.text[:300] if resp.text else "OK",
            "request_id": request_id,
            "launched_at": launched_at,
            "simulated": False,
        }
    except requests.RequestException as exc:
        return {
            "success": False,
            "status_code": 0,
            "message": str(exc)[:300],
            "request_id": request_id,
            "launched_at": launched_at,
            "simulated": False,
        }
