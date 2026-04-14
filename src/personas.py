"""Persona definitions for targeted newsletter generation."""

PERSONAS = [
    {
        "id": "agency_founder",
        "title": "Agency Founder",
        "pain_points": [
            "Scaling operations without losing quality",
            "Finding and retaining top talent",
            "Maintaining profitability as the agency grows",
        ],
        "messaging_angle": (
            "Focus on strategic growth, leadership leverage, "
            "and systems that free founders from day-to-day execution."
        ),
    },
    {
        "id": "ops_pm",
        "title": "Operations / Project Manager",
        "pain_points": [
            "Keeping projects on time and on budget",
            "Managing cross-functional communication",
            "Tool sprawl and process inconsistency",
        ],
        "messaging_angle": (
            "Emphasize efficiency gains, workflow automation, "
            "and practical frameworks that reduce chaos."
        ),
    },
    {
        "id": "creative_lead",
        "title": "Creative Lead / Strategist",
        "pain_points": [
            "Balancing creative vision with client constraints",
            "Getting buy-in on bold ideas",
            "Avoiding burnout while staying inspired",
        ],
        "messaging_angle": (
            "Highlight creative empowerment, storytelling techniques, "
            "and tools that protect creative energy."
        ),
    },
]


def get_persona_by_id(persona_id: str) -> dict | None:
    """Return a single persona dict by its id, or None."""
    for p in PERSONAS:
        if p["id"] == persona_id:
            return p
    return None
