"""Prompt templates for OpenAI content generation.

Each function returns a plain string prompt. No API calls happen here.
"""

# ── Tone guidance per client category ────────────────────────

CATEGORY_TONE = {
    "established_prospects": (
        "Tone: direct and conversion-focused. Emphasize business value, "
        "ROI, and competitive advantage. Assume the reader already "
        "understands the problem space."
    ),
    "emerging_clients": (
        "Tone: educational and trust-building. Lead with practical value "
        "they can use immediately. Avoid jargon; build credibility."
    ),
    "general_audience": (
        "Tone: broad and thought-leadership oriented. Focus on awareness, "
        "industry trends, and big-picture ideas. Keep it inviting."
    ),
}


def _tone_for(category: str) -> str:
    return CATEGORY_TONE.get(category, CATEGORY_TONE["general_audience"])


# ── 1. Blog outline ─────────────────────────────────────────
# Expected output: numbered list of 5-7 section titles with 1-line descriptions

def blog_outline_prompt(thesis: str) -> str:
    return (
        f"You are a B2B marketing strategist at an AI startup.\n"
        f"Campaign thesis: \"{thesis}\"\n\n"
        "Create a blog outline with 5-7 sections. "
        "For each section return a numbered title and a one-sentence description.\n"
        "Format:\n1. Section Title — description\n"
    )


# ── 2. Blog draft ───────────────────────────────────────────
# Expected output: 400-600 word blog post in markdown

def blog_draft_prompt(thesis: str, outline: str) -> str:
    return (
        f"You are a B2B content writer for an AI startup.\n"
        f"Campaign thesis: \"{thesis}\"\n\n"
        f"Outline:\n{outline}\n\n"
        "Write a 400-600 word blog post following this outline. "
        "Use a professional but approachable tone. "
        "Include a short intro, body sections with subheadings, "
        "and a brief conclusion with a call-to-action."
    )


# ── 3. Newsletter copy ──────────────────────────────────────
# Expected output: 150-250 word email body with subject line and CTA

def newsletter_prompt(thesis: str, category: str,
                      client_needs: str = "", cta: str = "",
                      tone_notes: str = "") -> str:
    tone = _tone_for(category)
    parts = [
        "You are writing a short marketing newsletter for a B2B AI startup.",
        f"Campaign thesis: \"{thesis}\"",
        f"Target audience category: {category}",
        tone,
    ]
    if client_needs:
        parts.append(f"Reader's key need: {client_needs}")
    if cta:
        parts.append(f"Call-to-action: {cta}")
    if tone_notes:
        parts.append(f"Additional tone notes: {tone_notes}")
    parts.append(
        "\nWrite a 150-250 word email newsletter. "
        "Start with a compelling subject line on its own line "
        "(prefix it with 'Subject: '). "
        "Then write the body. End with the CTA."
    )
    return "\n".join(parts)


# ── 4. LinkedIn post ────────────────────────────────────────
# Expected output: 100-180 word LinkedIn post with hook and hashtags

def linkedin_post_prompt(thesis: str, category: str = "general_audience") -> str:
    tone = _tone_for(category)
    return (
        "You are a startup founder posting on LinkedIn.\n"
        f"Campaign thesis: \"{thesis}\"\n"
        f"{tone}\n\n"
        "Write a 100-180 word LinkedIn post. "
        "Open with a bold hook sentence. "
        "Include 1-2 key insights. "
        "End with a question or soft CTA. "
        "Add 3-5 relevant hashtags on the last line."
    )


# ── 5. Performance summary + next recommendation ────────────
# Expected output: 3-5 sentence summary, then a suggested next thesis

def performance_summary_prompt(metrics: list[dict]) -> str:
    lines = [
        f"- {m.get('category', m.get('persona', '?'))}: "
        f"open={m['open_rate']}%, click={m['click_rate']}%, "
        f"unsub={m['unsubscribe_rate']}%"
        for m in metrics
    ]
    return (
        "You are a marketing analyst at an AI startup.\n"
        "Here are the latest campaign metrics by audience segment:\n"
        + "\n".join(lines)
        + "\n\nProvide a 3-4 sentence performance summary. "
        "Identify the best and worst performing segment."
    )


def next_direction_prompt(thesis: str, metrics: list[dict]) -> str:
    lines = [
        f"- {m.get('category', m.get('persona', '?'))}: "
        f"open={m['open_rate']}%, click={m['click_rate']}%, "
        f"unsub={m['unsubscribe_rate']}%"
        for m in metrics
    ]
    return (
        "You are a marketing strategist at an AI startup.\n"
        f"The last campaign thesis was: \"{thesis}\"\n"
        "Results:\n" + "\n".join(lines) + "\n\n"
        "Based on these results, suggest one concise next campaign thesis "
        "(one sentence) and explain why in 2-3 sentences."
    )
