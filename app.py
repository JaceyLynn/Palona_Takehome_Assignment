"""Palona AI — Marketing Content Pipeline (Streamlit MVP)."""

import os
import uuid

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from src.clients import (
    load_clients,
    get_all_categories,
    filter_clients_by_category,
    summarize_client_categories,
    get_default_target_list,
)
from src.content_generator import generate_full_campaign_content
from src.send_engine import (
    simulate_send_campaign,
    log_send_result,
    map_newsletters_to_target_clients,
    create_campaign_log_record,
    save_campaign_log_records,
)
from src.hubspot_client import (
    upsert_contacts_to_hubspot,
    _is_live as hubspot_is_live,
    build_marketing_email_payload,
    create_marketing_email_draft,
)
from src.analytics import (
    simulate_performance_metrics,
    save_performance_records,
    generate_campaign_report,
)
from src.storage import (
    save_generated_content_json,
    save_generated_content_markdown,
)


load_dotenv()

# ── Mode detection ─────────────────────────────────────────────
LIVE_MODE = bool(os.getenv("OPENAI_API_KEY"))
MODE_LABEL = "🟢 Live (OpenAI)" if LIVE_MODE else "🟡 Demo (mock data)"
HUBSPOT_LIVE = hubspot_is_live()
HUBSPOT_LABEL = "🟢 Live (HubSpot)" if HUBSPOT_LIVE else "🟡 Mock (no token)"

st.set_page_config(page_title="Palona Content Pipeline", layout="wide")

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    st.markdown(f"**AI Mode:** {MODE_LABEL}")
    st.markdown(f"**CRM Mode:** {HUBSPOT_LABEL}")
    if not LIVE_MODE:
        st.caption(
            "Set `OPENAI_API_KEY` in your `.env` file to "
            "switch to live AI-generated content."
        )
    if not HUBSPOT_LIVE:
        st.caption(
            "Set `HUBSPOT_ACCESS_TOKEN` in your `.env` file to "
            "enable real HubSpot API calls."
        )
    st.divider()
    st.caption("Sends are always simulated in this MVP.")

st.title("📬 AI Marketing Content Pipeline")
st.caption("End-to-end campaign workflow — thesis → clients → content → send → report")
if not LIVE_MODE:
    st.info("Running in **demo mode** — all content is mock-generated. Add an OpenAI API key to enable live generation.", icon="💡")

# ═══════════════════════════════════════════════════════════════
# Section 1 — Campaign Setup
# ═══════════════════════════════════════════════════════════════
st.header("1 · Campaign Setup")

thesis = st.text_input(
    "Campaign thesis",
    placeholder="e.g. AI-powered workflows help agencies scale without burnout",
)
category = st.selectbox("Client category", get_all_categories())
cta = st.text_input("Call-to-action (CTA)", placeholder="e.g. Book a free demo →")
tone_notes = st.text_area(
    "Tone notes (optional)",
    placeholder="e.g. Keep it conversational and upbeat",
    height=80,
)

if st.button("🔍 Load Target Clients"):
    clients = filter_clients_by_category(category)
    targets = get_default_target_list(category)
    st.session_state["clients"] = clients
    st.session_state["targets"] = targets
    st.session_state["category"] = category
    # Reset downstream state when clients change
    for key in ("content", "approved", "campaign_record", "report"):
        st.session_state.pop(key, None)

# ═══════════════════════════════════════════════════════════════
# Section 2 — Targeted Clients
# ═══════════════════════════════════════════════════════════════
if st.session_state.get("clients"):
    st.header("2 · Targeted Clients")
    clients = st.session_state["clients"]
    df = pd.DataFrame(clients)
    display_cols = [c for c in ["company_name", "contact_name", "email", "category", "needs"] if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True)

    summary = summarize_client_categories(clients)
    st.markdown(
        "**Category summary:** "
        + ", ".join(f"{cat.replace('_', ' ')} ({n})" for cat, n in summary.items())
    )

    # ── CRM sync ──────────────────────────────────────────────
    if st.button("🔄 Sync Contacts to HubSpot"):
        with st.spinner("Upserting contacts…"):
            result = upsert_contacts_to_hubspot(clients)
        st.session_state["crm_sync"] = result

    if st.session_state.get("crm_sync"):
        sync = st.session_state["crm_sync"]
        mode = "🟢 live" if not sync.get("simulated", True) else "🟡 mock"
        st.caption(f"CRM mode: {mode} · Endpoint: `{sync.get('endpoint', '')}`")
        if not sync["success"]:
            st.error(f"Sync failed: {sync.get('error', 'unknown')}")
        rows = []
        ids = sync.get("returned_ids", [])
        for idx, c in enumerate(clients):
            rows.append({
                "email": c["email"],
                "persona": c.get("subcategory", c.get("category", "")),
                "sync_status": "✅ synced" if sync["success"] else "❌ failed",
                "hubspot_id": ids[idx] if idx < len(ids) else "",
                "mode": mode,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ═══════════════════════════════════════════════════════════════
# Section 3 — Generate Content
# ═══════════════════════════════════════════════════════════════
if st.session_state.get("clients") and thesis:
    st.header("3 · Generated Content")

    if st.button("✨ Generate Content"):
        with st.spinner("Generating campaign content…"):
            content = generate_full_campaign_content(
                thesis=thesis,
                clients=st.session_state["clients"],
                cta=cta,
                tone_notes=tone_notes,
            )
            content["campaign_id"] = uuid.uuid4().hex[:8]
            st.session_state["content"] = content
            # Reset downstream state
            for key in ("approved", "campaign_record", "report"):
                st.session_state.pop(key, None)

            # Persist structured content (JSON + Markdown)
            cid = content["campaign_id"]
            save_generated_content_json(cid, content)
            md_path = save_generated_content_markdown(cid, content)
            st.caption(f"💾 Saved to `generated_content.json` and `{md_path}`")

    content = st.session_state.get("content")
    if content:
        # Blog outline
        st.subheader("Blog Outline")
        edited_outline = st.text_area(
            "Edit outline", content["blog_outline"], height=180, key="ed_outline"
        )

        # Blog draft
        st.subheader("Blog Draft")
        edited_draft = st.text_area(
            "Edit draft", content["blog_draft"], height=260, key="ed_draft"
        )

        # Newsletter versions
        st.subheader("Newsletter Versions")
        edited_versions = []
        for i, v in enumerate(content.get("newsletter_versions", [])):
            label = v["category"].replace("_", " ").title()
            with st.expander(f"📧 {label}"):
                subj = st.text_input(
                    f"Subject — {label}", v["subject"], key=f"nl_subj_{i}"
                )
                body = st.text_area(
                    f"Body — {label}", v["body"], height=180, key=f"nl_body_{i}"
                )
                edited_versions.append({**v, "subject": subj, "body": body})

        # LinkedIn post
        st.subheader("LinkedIn Post")
        edited_post = st.text_area(
            "Edit post", content["linkedin_post"], height=160, key="ed_linkedin"
        )

        # Persist edits back into session state
        content["blog_outline"] = edited_outline
        content["blog_draft"] = edited_draft
        content["newsletter_versions"] = edited_versions
        content["linkedin_post"] = edited_post

    # ── Create Marketing Email Drafts ─────────────────────────
    if content and st.button("📧 Create Marketing Email Drafts in HubSpot"):
        draft_results = []
        for v in content.get("newsletter_versions", []):
            persona = v.get("category", "general_audience")
            email_payload = build_marketing_email_payload(content, persona)
            hs_result = create_marketing_email_draft(email_payload)
            email_id = ""
            if hs_result.get("returned_ids"):
                email_id = hs_result["returned_ids"][0]
            draft_results.append({
                "persona": persona.replace("_", " ").title(),
                "subject": email_payload["subject"],
                "email_id": email_id,
                "endpoint": hs_result.get("endpoint", ""),
                "mode": "🟢 live" if not hs_result.get("simulated", True) else "🟡 mock",
                "status": "✅ created" if hs_result["success"] else "❌ failed",
            })
        st.session_state["draft_results"] = draft_results

    if st.session_state.get("draft_results"):
        st.subheader("Email Draft Results")
        st.dataframe(pd.DataFrame(st.session_state["draft_results"]), use_container_width=True)

# ═══════════════════════════════════════════════════════════════
# Section 4 — Review & Confirm
# ═══════════════════════════════════════════════════════════════
if st.session_state.get("content"):
    st.header("4 · Review & Confirm")

    approved = st.checkbox(
        "I have reviewed all content and approve sending",
        value=st.session_state.get("approved", False),
        key="approve_check",
    )
    st.session_state["approved"] = approved

    if approved:
        if st.button("🚀 Confirm & Autosend"):
            content = st.session_state["content"]
            campaign_id = content.get("campaign_id", uuid.uuid4().hex[:8])
            targets = st.session_state.get("targets", [])
            # Enrich targets with category so grouping works
            cat = st.session_state.get("category", "general_audience")
            enriched_targets = [
                {**t, "category": t.get("category", cat)} for t in targets
            ]

            with st.spinner("Sending campaign…"):
                record = simulate_send_campaign(campaign_id, content, enriched_targets)
                log_send_result(record)
                st.session_state["campaign_record"] = record
                # Reset report so it regenerates
                st.session_state.pop("report", None)

                # Create marketing email drafts per persona → HubSpot
                email_results = []
                for g in record["group_results"]:
                    persona = g["category"]
                    email_payload = build_marketing_email_payload(content, persona)
                    hs_result = create_marketing_email_draft(email_payload)
                    email_id = ""
                    if hs_result.get("returned_ids"):
                        email_id = hs_result["returned_ids"][0]
                    email_results.append({
                        "persona": persona,
                        "email_id": email_id,
                        "endpoint": hs_result.get("endpoint", ""),
                        "simulated": hs_result.get("simulated", True),
                    })

                # Build & save campaign log records
                log_records = create_campaign_log_record(content, record, email_results)
                save_campaign_log_records(log_records)
                st.session_state["campaign_log_records"] = log_records

            st.success(
                f"Campaign **{campaign_id}** sent to "
                f"{record['sent_count']} recipient(s)!"
            )

            # Per-persona send summary
            st.subheader("Send Summary by Persona")
            summary_rows = []
            for g in record["group_results"]:
                summary_rows.append({
                    "persona": g["category"].replace("_", " ").title(),
                    "recipients": g["sent"],
                    "subject": g.get("subject", ""),
                    "status": "✅ sent (simulated)",
                })
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

            # Email draft results
            st.subheader("Marketing Email Drafts (HubSpot)")
            draft_rows = []
            for er in email_results:
                draft_rows.append({
                    "persona": er["persona"].replace("_", " ").title(),
                    "email_id": er["email_id"],
                    "endpoint": er["endpoint"],
                    "mode": "🟢 live" if not er["simulated"] else "🟡 mock",
                })
            st.dataframe(pd.DataFrame(draft_rows), use_container_width=True)

    # ── Campaign Log ──────────────────────────────────────────
    if st.session_state.get("campaign_log_records"):
        st.subheader("Campaign Log (CRM)")
        log_df = pd.DataFrame(st.session_state["campaign_log_records"])
        display_cols = [
            c for c in [
                "campaign_id", "blog_title", "send_date", "persona",
                "newsletter_id", "newsletter_subject", "crm_mode",
                "send_status", "recipient_count",
            ] if c in log_df.columns
        ]
        st.dataframe(log_df[display_cols], use_container_width=True)

# ═══════════════════════════════════════════════════════════════
# Section 5 — Performance Report & Recommendation
# ═══════════════════════════════════════════════════════════════
if st.session_state.get("campaign_record"):
    st.header("5 · Performance Report")

    record = st.session_state["campaign_record"]
    campaign_id = record["campaign_id"]

    # Simulate + persist metrics once per send
    if "report" not in st.session_state:
        targets = st.session_state.get("targets", [])
        # Add category to targets for metric simulation
        cat = st.session_state.get("category", "general_audience")
        enriched = [
            {**t, "category": t.get("category", cat)} for t in targets
        ]
        metrics = simulate_performance_metrics(campaign_id, enriched)
        save_performance_records(metrics)
        report = generate_campaign_report(campaign_id, thesis, metrics)
        st.session_state["report"] = report

    report = st.session_state["report"]
    summary = report["summary"]
    best = summary["by_category"].get(summary["best_category"], {})

    # ── Top-line metric cards ─────────────────────────────────
    total_recipients = sum(m.get("recipients", 0) for m in report["metrics"])
    avg_open = round(sum(m["open_rate"] for m in report["metrics"]) / len(report["metrics"]), 1)
    avg_ctr = round(sum(m["click_rate"] for m in report["metrics"]) / len(report["metrics"]), 1)
    total_demos = sum(m["demo_clicks"] for m in report["metrics"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Recipients", total_recipients)
    col2.metric("Avg Open Rate", f"{avg_open}%")
    col3.metric("Avg CTR", f"{avg_ctr}%")
    col4.metric("Demo Clicks", total_demos)

    # ── Category breakdown table ──────────────────────────────
    st.subheader("Performance by Category")
    metrics_df = pd.DataFrame(report["metrics"])
    display_cols = [
        c for c in [
            "category", "recipients", "open_rate", "click_rate",
            "demo_clicks", "dwell_time_seconds", "linkedin_engagement_rate",
            "unsubscribe_rate",
        ] if c in metrics_df.columns
    ]
    st.dataframe(metrics_df[display_cols], use_container_width=True)

    # ── Campaign summary ──────────────────────────────────────
    st.subheader("Campaign Summary")
    st.info(summary["summary_text"])

    # ── Next-content recommendation ───────────────────────────
    st.subheader("📌 Next Content Recommendation")
    st.success(report["recommendation"])
