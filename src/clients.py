"""Client list helpers — load, filter, and summarize clients."""

from src.storage import load_clients as _load_clients

CATEGORIES = [
    "established_prospects",
    "emerging_clients",
    "general_audience",
]


def load_clients() -> list[dict]:
    """Return all clients from data/clients.json."""
    return _load_clients()


def get_all_categories() -> list[str]:
    """Return the list of known client categories."""
    return list(CATEGORIES)


def filter_clients_by_category(category: str) -> list[dict]:
    """Return clients matching the given category."""
    return [c for c in load_clients() if c.get("category") == category]


def summarize_client_categories(clients: list[dict]) -> dict:
    """Return a {category: count} summary for a list of clients.

    Example:
        >>> summarize_client_categories(load_clients())
        {'established_prospects': 3, 'emerging_clients': 3, 'general_audience': 3}
    """
    summary: dict[str, int] = {}
    for c in clients:
        cat = c.get("category", "unknown")
        summary[cat] = summary.get(cat, 0) + 1
    return summary


def get_default_target_list(category: str) -> list[dict]:
    """Return a ready-to-use target list for a campaign.

    Each entry contains only the fields needed for sending:
    id, company_name, contact_name, email, preferred_send_time.
    """
    targets = []
    for c in filter_clients_by_category(category):
        targets.append({
            "id": c["id"],
            "company_name": c["company_name"],
            "contact_name": c["contact_name"],
            "email": c["email"],
            "preferred_send_time": c.get("preferred_send_time", "09:00"),
        })
    return targets
