"""NovaMind — Marketing Content Pipeline (Streamlit MVP).

Three-page app: Generate Content (3-step workflow) | Info Setting | Performance Report.
Newsletter is the only working generation mode in this demo.
"""

import json
import os
import uuid
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import numpy as np
from dotenv import load_dotenv

from src.clients import load_clients
from src.contacts import (
    load_contacts_csv,
    BRANCH_BASIS_MAP,
    get_branch_column,
    get_branch_options,
    filter_contacts_by_branch,
    merge_uploaded_contacts,
    DISPLAY_COLUMNS,
    PERSONALIZATION_FIELDS,
)
from src.content_generator import (
    generate_newsletter_outlines,
    generate_newsletter_full,
    generate_blog_outline,
    generate_blog_draft,
    generate_persona_newsletters,
    suggest_thesis,
)
from src.personas import PERSONAS
from src.send_engine import (
    simulate_send_campaign,
    log_send_result,
    create_campaign_log_record,
    save_campaign_log_records,
)
from src.hubspot_client import (
    _is_live as hubspot_is_live,
    build_marketing_email_payload,
    create_marketing_email_draft,
    fetch_hubspot_contacts,
)
from src.analytics import (
    simulate_performance_metrics,
    save_performance_records,
    generate_campaign_report,
)
from src.storage import (
    save_generated_content_json,
    load_performance_history,
)

load_dotenv()

# ── Mode detection ────────────────────────────────────────────
LIVE_MODE = bool(os.getenv("OPENAI_API_KEY"))
HUBSPOT_LIVE = hubspot_is_live()

# ── Page config & CSS ─────────────────────────────────────────
st.set_page_config(page_title="NovaMind Content Pipeline", layout="wide")

ACCENT = "#a90066"
st.markdown(f"""<style>
/* ── Global accent override (checkboxes, radios, focus rings, sliders, toggles) ── */
:root {{
    --primary-color: {ACCENT};
}}
/* Checkbox & radio checked state */
input[type="checkbox"]:checked + span svg,
[data-testid="stCheckbox"] svg {{
    fill: {ACCENT} !important;
    color: {ACCENT} !important;
}}
[data-testid="stCheckbox"] input:checked ~ div[data-testid="stMarkdownContainer"] {{
    color: {ACCENT};
}}
/* Primary button */
button[kind="primary"], .stButton > button[kind="primary"],
button[data-testid="stFormSubmitButton"] {{
    background-color: {ACCENT} !important;
    border-color: {ACCENT} !important;
    color: white !important;
}}
button[kind="primary"]:hover {{
    background-color: #8a0054 !important;
    border-color: #8a0054 !important;
}}
/* Regular buttons */
.stButton > button {{border-color: {ACCENT}; color: {ACCENT};}}
.stButton > button:hover {{background-color: {ACCENT}; color: white; border-color: {ACCENT};}}
/* Radio buttons */
[data-testid="stRadio"] div[role="radiogroup"] label div:first-child {{
    border-color: {ACCENT} !important;
}}
[data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"] div:first-child {{
    background-color: {ACCENT} !important;
}}
/* Selectbox / multiselect focus */
.stSelectbox > div > div:focus-within,
.stMultiSelect > div > div:focus-within {{
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 1px {ACCENT} !important;
}}
/* Multiselect tags */
.stMultiSelect span[data-baseweb="tag"] {{
    background-color: {ACCENT} !important;
}}
/* Text input / textarea focus */
.stTextInput > div > div:focus-within,
.stTextArea > div > div:focus-within {{
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 1px {ACCENT} !important;
}}
/* Slider */
[data-testid="stSlider"] div[role="slider"] {{
    background-color: {ACCENT} !important;
}}
/* Toggle */
[data-testid="stToggle"] label span {{
    background-color: {ACCENT} !important;
}}
/* Links & st.info/success accent overrides */
a {{color: {ACCENT} !important;}}
hr {{border-color: {ACCENT} !important;}}
/* Fixed-height option cards in Step 2 */
.option-card {{min-height:260px; max-height:260px; overflow-y:auto;}}
/* Sidebar nav styling */
div[data-testid="stSidebar"] .nav-link {{
    display:block; padding:8px 14px; margin:2px 0; border-radius:6px;
    color:#333; text-decoration:none; font-size:0.95em; cursor:pointer;
    border:none; background:transparent; width:100%; text-align:left;
}}
div[data-testid="stSidebar"] .nav-link:hover {{background:#f0f0f0;}}
div[data-testid="stSidebar"] .nav-link.active {{background:{ACCENT}; color:white; font-weight:600;}}
/* Main nav buttons */
div[data-testid="stSidebar"] > div > div > div > .stButton > button {{
    font-size:0.95em !important;
    padding:8px 14px !important;
    font-weight:500 !important;
}}
</style>""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────

# Branch basis labels (order for the UI selector)
BRANCH_BASIS_LABELS = list(BRANCH_BASIS_MAP.keys())

DEFAULT_LAYOUTS = [
    {"name": "Clean & Minimal", "desc": "Simple layout with clear hierarchy and white space"},
    {"name": "Bold & Visual", "desc": "Image-forward layout with strong visual CTAs"},
    {"name": "Classic Professional", "desc": "Traditional business newsletter format"},
]
DEFAULT_CTA_TEMPLATES = [
    {"label": "Book a Demo", "url": "https://novamind.ai/demo"},
    {"label": "Learn More", "url": "https://novamind.ai"},
    {"label": "Contact Us", "url": "https://novamind.ai/contact"},
]
DEFAULT_BRAND_VOICE = {
    "tone": "Professional but approachable",
    "personality": "Innovative, helpful, trustworthy",
    "guidelines": "Use active voice. Keep sentences concise. Focus on value over features.",
}
DEFAULT_HEADING = "NovaMind Newsletter"
DEFAULT_SIGNATURE = "The NovaMind Team\nwww.novamind.ai"

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "data", "settings.json")


# ── Settings persistence ──────────────────────────────────────

def _load_saved_settings() -> dict:
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    return {}


def _save_settings():
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump({
            "layouts": st.session_state.layouts,
            "cta_templates": st.session_state.cta_templates,
            "brand_voice": st.session_state.brand_voice,
            "heading": st.session_state.heading,
            "signature": st.session_state.signature,
        }, f, indent=2)


# ── Session-state initialization ──────────────────────────────

def _init():
    saved = _load_saved_settings()
    defaults = {
        "gen_step": 1,
        "layouts": saved.get("layouts") or [dict(d) for d in DEFAULT_LAYOUTS],
        "cta_templates": saved.get("cta_templates") or [dict(d) for d in DEFAULT_CTA_TEMPLATES],
        "brand_voice": saved.get("brand_voice") or dict(DEFAULT_BRAND_VOICE),
        "heading": saved.get("heading") or DEFAULT_HEADING,
        "signature": saved.get("signature") or DEFAULT_SIGNATURE,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    # Load the master contact CSV once per session
    if "contacts_df" not in st.session_state:
        df = load_contacts_csv()
        if df.empty:
            st.warning(
                "Contact CSV not found at `data/hubspot_mock_contacts_100.csv`. "
                "Some features will be limited."
            )
        st.session_state["contacts_df"] = df

_init()


# ── Sidebar navigation ───────────────────────────────────────

# Main pages and Info Setting sub-pages
NAV_ITEMS = [
    {"label": "Generate Content", "key": "generate"},
    {"label": "Info Setting", "key": "settings"},
    {"label": "Performance Report", "key": "report"},
]

with st.sidebar:
    st.markdown(
        "<h2 style='margin-bottom:0.2em;'>NovaMind</h2>"
        "<p style='color:grey;margin-top:0;font-size:0.85em;'>"
        "Marketing Content Pipeline</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.session_state.setdefault("page", "generate")

    for item in NAV_ITEMS:
        key = item["key"]
        label = item["label"]

        is_active = st.session_state.page == key
        cls = "nav-link active" if is_active else "nav-link"

        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state.page = key
            st.rerun()

    st.divider()

    # Mode indicators
    ai_label = "Live (OpenAI)" if LIVE_MODE else "Demo (mock)"
    crm_label = "Live (HubSpot)" if HUBSPOT_LIVE else "Mock"
    st.caption(f"**AI:** {ai_label}")
    st.caption(f"**CRM:** {crm_label}")
    if not LIVE_MODE:
        st.caption("Set `OPENAI_API_KEY` in .env for live AI.")
    if not HUBSPOT_LIVE:
        st.caption("Set `HUBSPOT_ACCESS_TOKEN` in .env for HubSpot.")

page = st.session_state.page


# =====================================================================
# PAGE 1 — Generate Content (3-step workflow)
# =====================================================================

def _step_indicator():
    """Render a visual step progress bar."""
    step = st.session_state.gen_step
    names = ["Campaign Content", "Choose Persona", "Detail Edit & Send"]
    cols = st.columns(3)
    for i, (col, name) in enumerate(zip(cols, names)):
        n = i + 1
        if n < step:
            col.markdown(f"~~Step {n}: {name}~~")
        elif n == step:
            col.markdown(f"**Step {n}: {name}**")
        else:
            col.caption(f"Step {n}: {name}")


def render_generate_content():
    st.title("Generate Content")
    if not LIVE_MODE:
        st.info("Demo mode — content is mock-generated. Add OPENAI_API_KEY for live AI generation.")
    _step_indicator()
    st.divider()
    {1: _step1, 2: _step2, 3: _step3}[st.session_state.gen_step]()


# -- Step 1: Campaign Content -------------------------------------------

def _step1():
    st.subheader("Step 1 — Campaign Content")

    thesis = st.text_area(
        "Campaign thesis / content brief",
        height=140,
        placeholder="e.g. AI-powered workflows help agencies scale without burnout",
        key="campaign_thesis_input",
    )

    # AI thesis suggestion
    if thesis and len(thesis) > 10:
        if st.button("Suggest improved thesis"):
            with st.spinner("Thinking..."):
                st.session_state["thesis_suggestion"] = suggest_thesis(thesis)
        if st.session_state.get("thesis_suggestion"):
            sug = st.session_state["thesis_suggestion"]
            st.info(f"**Suggestion:** {sug}")

    # File uploaders
    c1, c2 = st.columns(2)
    with c1:
        st.file_uploader(
            "Upload images",
            type=["png", "jpg", "jpeg", "gif"],
            accept_multiple_files=True,
            key="uploaded_images",
        )
    with c2:
        st.file_uploader(
            "Upload documents (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="uploaded_docs",
        )

    # Content type info — always generates both blog + newsletter
    st.markdown(
        f"**Content types:** This campaign will generate a **blog outline**, "
        f"a **short blog draft**, and **persona-targeted newsletter options**."
    )

    st.divider()

    # Branch basis selector (drives CSV column lookup)
    st.selectbox(
        "Provide personas based on:",
        BRANCH_BASIS_LABELS,
        key="seg_type_select",
    )

    # Next step
    _, _, _col_r1 = st.columns([4, 1, 1])
    with _col_r1:
        next_clicked = st.button("Next Step →", type="primary", key="step1_next")
    if next_clicked:
        t = st.session_state.get("campaign_thesis_input", "").strip()
        if len(t) < 5:
            st.error("Please enter a campaign thesis (at least 5 characters).")
        else:
            st.session_state["campaign_thesis"] = t
            st.session_state["segmentation_type"] = st.session_state.seg_type_select

            # Generate blog outline + draft
            with st.spinner("Generating blog outline and draft..."):
                outline_data = generate_blog_outline(t)
                st.session_state["blog_outline"] = outline_data["outline"]
                draft_data = generate_blog_draft(t, outline_data["outline"])
                st.session_state["blog_draft"] = draft_data["draft"]

            # Clear downstream caches
            for k in (
                "newsletter_options",
                "selected_options",
                "newsletter_full",
                "step3_clients",
                "send_result",
                "nl_edit_subject",
                "nl_edit_body",
                "selected_persona",
                "persona_newsletter_cache",
                "selected_nl_idx",
                "blog_edit_outline",
                "blog_edit_draft",
                "selected_emails",
            ):
                st.session_state.pop(k, None)
            st.session_state.gen_step = 2
            st.rerun()


# -- Step 2: Option Preview ---------------------------------------------

def _step2():
    thesis = st.session_state["campaign_thesis"]

    st.subheader("Step 2 — Choose Persona")
    st.caption(f"Campaign: *{thesis}*")

    # ── Show 3 persona cards ──
    st.session_state.setdefault("selected_persona", None)
    current_sel = st.session_state.get("selected_persona")

    cols = st.columns(3)
    for i, (col, persona) in enumerate(zip(cols, PERSONAS)):
        with col:
            is_selected = current_sel == persona["id"]
            border_css = (
                f"border:2px solid {ACCENT};background:#fdf0f7;"
                if is_selected
                else "border:1px solid #ddd;background:#fafafa;"
            )
            pain_html = "".join(
                f"<li style='font-size:0.82em;color:#444;margin:2px 0;'>{p}</li>"
                for p in persona["pain_points"]
            )
            st.markdown(
                f"<div class='option-card' style='{border_css}border-radius:10px;padding:16px;'>"
                f"<h4 style='margin:0 0 6px;color:#111;'>{persona['title']}</h4>"
                f"<p style='color:#555;font-size:0.8em;margin:0 0 6px;'>{persona['messaging_angle']}</p>"
                f"<ul style='padding-left:18px;margin:6px 0 0;'>{pain_html}</ul>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if st.button(
                "Selected ✓" if is_selected else f"Select {persona['title']}",
                key=f"persona_btn_{i}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
            ):
                if not is_selected:
                    st.session_state["selected_persona"] = persona["id"]
                    st.rerun()

    if current_sel:
        sel_persona = next(p for p in PERSONAS if p["id"] == current_sel)
        st.info(f"Selected persona: **{sel_persona['title']}**")

    # ── Navigation ──
    st.divider()
    c_back, _, c_next = st.columns([1, 3, 1])
    with c_back:
        if st.button("Back", key="step2_back"):
            st.session_state.gen_step = 1
            st.rerun()
    with c_next:
        if st.button("Next Step →", type="primary", key="step2_next"):
            if not current_sel:
                st.error("Please select a persona before proceeding.")
            else:
                for k in (
                    "newsletter_full",
                    "step3_clients",
                    "send_result",
                    "nl_edit_subject",
                    "nl_edit_body",
                    "selected_emails",
                    "selected_nl_idx",
                ):
                    st.session_state.pop(k, None)
                st.session_state.gen_step = 3
                st.rerun()


# -- HubSpot contact sync helper ----------------------------------------

def _sync_contacts_to_hubspot(rows: list[dict]):
    """Attempt to sync contacts to HubSpot. Shows result in the UI."""
    if HUBSPOT_LIVE:
        try:
            contacts = [
                {
                    "email": r.get("Email", ""),
                    "contact_name": f"{r.get('First Name', '')} {r.get('Last Name', '')}".strip(),
                    "company_name": r.get("Company Name", ""),
                }
                for r in rows
            ]
            from src.hubspot_client import upsert_contacts_to_hubspot
            result = upsert_contacts_to_hubspot(contacts)
            st.success(f"Synced {len(rows)} contact(s) to HubSpot.")
        except Exception as exc:
            st.warning(f"HubSpot sync failed: {exc}")
    else:
        st.info(f"HubSpot sync simulated for {len(rows)} contact(s) (mock mode).")


# -- Step 3: Detail Edit & Send -----------------------------------------

def _step3():
    thesis = st.session_state["campaign_thesis"]
    seg_type = st.session_state["segmentation_type"]
    persona_id = st.session_state["selected_persona"]
    persona = next(p for p in PERSONAS if p["id"] == persona_id)

    st.subheader("Step 3 — Detail Edit & Send")
    st.caption(f"Persona: **{persona['title']}**  |  Campaign: *{thesis}*")

    # ── Blog content (generated in Step 1) ──
    st.markdown("#### Blog Content")
    blog_outline = st.session_state.get("blog_outline", "")
    blog_draft = st.session_state.get("blog_draft", "")
    st.text_area("Blog Outline", value=blog_outline, height=150, key="blog_edit_outline")
    st.text_area("Blog Draft", value=blog_draft, height=250, key="blog_edit_draft")
    if st.button("Regenerate Blog Draft", key="regen_blog"):
        edited_outline = st.session_state.get("blog_edit_outline", blog_outline)
        with st.spinner("Regenerating blog draft from updated outline..."):
            draft_data = generate_blog_draft(thesis, edited_outline)
            st.session_state["blog_outline"] = edited_outline
            st.session_state["blog_draft"] = draft_data["draft"]
            st.rerun()

    st.divider()

    # ── Generate 3 newsletter options for this persona (cached) ──
    cache_key = "persona_newsletter_cache"
    if cache_key not in st.session_state or st.session_state.get("_cached_persona") != persona_id:
        with st.spinner(f"Generating newsletter options for {persona['title']}..."):
            brand = st.session_state.brand_voice
            cta_list = st.session_state.cta_templates
            cta_str = (
                f"{cta_list[0]['label']} ({cta_list[0]['url']})" if cta_list else ""
            )
            nl_options = generate_persona_newsletters(
                thesis, persona,
                cta=cta_str,
                tone_notes=brand.get("tone", ""),
            )
            st.session_state[cache_key] = nl_options
            st.session_state["_cached_persona"] = persona_id
            # Default to first option
            st.session_state.setdefault("selected_nl_idx", 0)
            chosen = nl_options[0]
            st.session_state["nl_edit_subject"] = chosen["subject"]
            st.session_state["nl_edit_body"] = chosen["body"]

    nl_options = st.session_state[cache_key]

    # ── Newsletter option selector ──
    st.markdown("#### Choose a Newsletter Version")
    nl_cols = st.columns(3)
    cur_idx = st.session_state.get("selected_nl_idx", 0)
    for i, (col, opt) in enumerate(zip(nl_cols, nl_options)):
        with col:
            is_sel = i == cur_idx
            border = (
                f"border:2px solid {ACCENT};background:#fdf0f7;"
                if is_sel
                else "border:1px solid #ddd;background:#fafafa;"
            )
            angle_label = opt["angle"].split(":")[0] if ":" in opt["angle"] else f"Option {i+1}"
            body_preview = opt["body"][:120].replace("\n", " ") + "..."
            st.markdown(
                f"<div style='{border}border-radius:10px;padding:14px;min-height:180px;max-height:180px;overflow-y:auto;'>"
                f"<p style='margin:0 0 4px;font-weight:600;color:{ACCENT};font-size:0.82em;'>{angle_label}</p>"
                f"<p style='margin:0 0 8px;color:#222;font-size:0.88em;font-weight:500;'>{opt['subject']}</p>"
                f"<p style='margin:0;color:#555;font-size:0.8em;'>{body_preview}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if st.button(
                "Selected ✓" if is_sel else f"Select Option {i+1}",
                key=f"nl_opt_btn_{i}",
                type="primary" if is_sel else "secondary",
                use_container_width=True,
            ):
                if not is_sel:
                    st.session_state["selected_nl_idx"] = i
                    st.session_state["nl_edit_subject"] = opt["subject"]
                    st.session_state["nl_edit_body"] = opt["body"]
                    st.rerun()

    st.divider()

    # ── Layout template dropdown ──
    layouts = st.session_state.layouts
    st.selectbox(
        "Layout Template",
        [lay["name"] for lay in layouts],
        key="layout_select",
        help="Configure layout templates on the Info Setting page.",
    )

    # ── Load contacts (all, not branch-filtered) ──
    if "step3_clients" not in st.session_state:
        contacts_df = st.session_state.get("contacts_df", pd.DataFrame())
        if not contacts_df.empty:
            st.session_state["step3_clients"] = contacts_df.reset_index(drop=True)
        else:
            all_clients = load_clients()
            st.session_state["step3_clients"] = pd.DataFrame(all_clients)

    # ── Selected-email tracking ──
    if "selected_emails" not in st.session_state:
        st.session_state["selected_emails"] = set(
            st.session_state["step3_clients"]["Email"].tolist()
            if "Email" in st.session_state["step3_clients"].columns
            else []
        )

    # ================================================================
    # TWO-COLUMN LAYOUT
    # ================================================================
    left, right = st.columns([1, 1], gap="large")

    # ── LEFT COLUMN: Newsletter edit + preview ─────────────────────
    with left:
        st.markdown("#### Newsletter Content")

        st.text_input("Subject Line", key="nl_edit_subject")
        st.text_area(
            "Newsletter Body",
            height=300,
            key="nl_edit_body",
            help="Edit the newsletter text directly. Markdown formatting is supported.",
        )

        # Collect all images: Step 1 uploads + Step 3 upload
        step1_imgs = st.session_state.get("uploaded_images") or []
        step3_imgs = st.session_state.get("step3_images") or []
        all_imgs = list(step1_imgs) + list(step3_imgs)

        with st.expander("Preview", expanded=True):
            subj = st.session_state.get("nl_edit_subject", "")
            body = st.session_state.get("nl_edit_body", "")
            heading = st.session_state.get("heading", DEFAULT_HEADING)
            signature = st.session_state.get("signature", DEFAULT_SIGNATURE)
            sig_html = signature.replace("\n", "<br>")
            st.markdown(
                f"<div style='border:1px solid #ddd;border-radius:8px;padding:16px;"
                f"background:#fafafa;'>"
                f"<h2 style='margin:0 0 8px;color:{ACCENT};'>{heading}</h2>"
                f"<p style='color:#888;font-size:0.8em;margin:0 0 4px;'>Subject</p>"
                f"<h3 style='margin:0 0 12px;color:#111;'>{subj}</h3>"
                f"<hr style='border-color:#eee;'>"
                f"<div style='white-space:pre-wrap;font-size:0.95em;color:#222;'>"
                f"{body}</div>"
                f"<hr style='border-color:#eee;margin:16px 0 8px;'>"
                f"<div style='font-size:0.85em;color:#666;'>{sig_html}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            # Show first image inside the preview
            if all_imgs:
                st.image(all_imgs[0], use_container_width=True, caption="Newsletter hero image")

        # Step 3 image upload
        st.file_uploader(
            "Add image",
            type=["png", "jpg", "jpeg", "gif"],
            accept_multiple_files=True,
            key="step3_images",
        )

        if all_imgs and len(all_imgs) > 1:
            st.markdown("**Attached Images**")
            img_cols = st.columns(min(len(all_imgs), 3))
            for i, img in enumerate(all_imgs):
                img_cols[i % 3].image(img, width=130, caption=f"Image {i + 1}")

        docs = st.session_state.get("uploaded_docs") or []
        if docs:
            st.markdown("**Attached Documents**")
            for doc in docs:
                st.caption(doc.name)

    # ── RIGHT COLUMN: Targeted recipient list ───────────────────────
    with right:
        st.markdown("#### Recipients")

        clients_df: pd.DataFrame = st.session_state["step3_clients"]
        branch_col = get_branch_column(seg_type)

        if not clients_df.empty and "Email" in clients_df.columns:
            # ── Filters ──
            with st.expander("Filters", expanded=False):
                fc1, fc2 = st.columns(2)
                with fc1:
                    persona_titles = ["All"] + [p["title"] for p in PERSONAS]
                    persona_filter = st.selectbox("Persona", persona_titles, key="cl_persona_filter")
                with fc2:
                    companies = sorted(clients_df["Company Name"].dropna().unique().tolist()) if "Company Name" in clients_df.columns else []
                    company_filter = st.multiselect("Company Name", companies, key="cl_company_filter")
                fc3, fc4 = st.columns(2)
                with fc3:
                    job_titles = sorted(clients_df["Job Title"].dropna().unique().tolist()) if "Job Title" in clients_df.columns else []
                    job_title_filter = st.multiselect("Job Title", job_titles, key="cl_job_title_filter")
                with fc4:
                    priorities = sorted(clients_df["Priority Level"].dropna().unique().tolist()) if "Priority Level" in clients_df.columns else []
                    priority_filter = st.multiselect("Priority Level", priorities, key="cl_priority_filter")

            # Apply filters
            filtered = clients_df.copy()
            if persona_filter and persona_filter != "All":
                # Map persona title to demographic branch
                _persona_branch_map = {
                    "Agency Founder": "Decision Makers",
                    "Operations / Project Manager": "Operational Users",
                    "Creative Lead": "Creative Practitioners",
                }
                target_branch = _persona_branch_map.get(persona_filter, "")
                if target_branch and "Demographic Branch" in filtered.columns:
                    filtered = filtered[filtered["Demographic Branch"] == target_branch]
            if company_filter:
                filtered = filtered[filtered["Company Name"].isin(company_filter)]
            if job_title_filter and "Job Title" in filtered.columns:
                filtered = filtered[filtered["Job Title"].isin(job_title_filter)]
            if priority_filter and "Priority Level" in filtered.columns:
                filtered = filtered[filtered["Priority Level"].isin(priority_filter)]

            # Build display columns
            show_cols = []
            for c in DISPLAY_COLUMNS:
                if c in filtered.columns:
                    show_cols.append(c)
            if branch_col in filtered.columns and branch_col not in show_cols:
                show_cols.insert(5, branch_col)

            display = filtered[show_cols].copy()
            display.insert(0, "Send", filtered["Email"].isin(st.session_state["selected_emails"]))

            # Select All toggle
            all_selected = bool(display["Send"].all()) if len(display) > 0 else False
            if st.checkbox("Select All", value=all_selected, key="select_all_contacts"):
                if not all_selected:
                    st.session_state["selected_emails"] = set(clients_df["Email"].tolist())
                    st.session_state.pop("client_editor", None)
                    st.rerun()
            else:
                if all_selected and len(display) > 0:
                    st.session_state["selected_emails"] = set()
                    st.session_state.pop("client_editor", None)
                    st.rerun()

            edited_df = st.data_editor(
                display,
                column_config={
                    "Send": st.column_config.CheckboxColumn("Send", default=True),
                },
                hide_index=True,
                use_container_width=True,
                key="client_editor",
            )

            # Sync selections back to session state
            if "Send" in edited_df.columns and "Email" in edited_df.columns:
                st.session_state["selected_emails"] = set(
                    edited_df.loc[edited_df["Send"], "Email"].tolist()
                )

            sel_count = int(edited_df["Send"].sum()) if "Send" in edited_df.columns else 0
            total = len(edited_df)
            st.caption(f"**{sel_count}** of **{total}** contacts selected for send")
        else:
            edited_df = pd.DataFrame()
            st.info("No contacts found for this branch.")

        # ── Add contacts section ──
        with st.expander("Add More Contacts"):
            add_tab, csv_tab, hs_tab = st.tabs(["Manual", "CSV Upload", "HubSpot"])

            with add_tab:
                ac1, ac2 = st.columns(2)
                with ac1:
                    mfn = st.text_input("First Name", key="m_fname", placeholder="Jane")
                    mln = st.text_input("Last Name", key="m_lname", placeholder="Doe")
                    me = st.text_input("Email", key="m_email", placeholder="jane@example.com")
                with ac2:
                    mc = st.text_input("Company", key="m_comp", placeholder="Acme Corp")
                    mj = st.text_input("Job Title", key="m_job", placeholder="Director")
                    st.write("")
                    sync_hs_manual = st.checkbox("Sync to HubSpot too", key="m_sync_hs")
                    if st.button("Add Contact", key="m_add"):
                        if mfn and me:
                            new_row = {
                                "Email": me,
                                "First Name": mfn,
                                "Last Name": mln,
                                "Company Name": mc,
                                "Job Title": mj,
                                "Priority Level": "",
                                "Primary Need": "",
                                "Preferred Send Time": "09:00",
                            }
                            # Fill branch column
                            branch_col = get_branch_column(seg_type)
                            new_row[branch_col] = ""
                            new_df = pd.DataFrame([new_row])
                            st.session_state["step3_clients"] = merge_uploaded_contacts(
                                st.session_state["step3_clients"], new_df
                            )
                            st.session_state["selected_emails"].add(me)
                            st.session_state.pop("client_editor", None)
                            if sync_hs_manual:
                                _sync_contacts_to_hubspot([new_row])
                            st.rerun()
                        else:
                            st.warning("First name and email are required.")

            with csv_tab:
                ucsv = st.file_uploader("Upload CSV", type=["csv"], key="csv_up3")
                sync_hs_csv = st.checkbox("Sync to HubSpot too", key="csv_sync_hs")
                if ucsv and st.button("Import CSV", key="csv_imp"):
                    uploaded = pd.read_csv(ucsv)
                    # Map common alternate column names
                    col_map = {
                        "email": "Email",
                        "first_name": "First Name",
                        "last_name": "Last Name",
                        "company_name": "Company Name",
                        "company": "Company Name",
                        "name": "First Name",
                        "job_title": "Job Title",
                    }
                    uploaded.rename(columns={k: v for k, v in col_map.items() if k in uploaded.columns}, inplace=True)
                    if "Email" in uploaded.columns:
                        before = len(st.session_state["step3_clients"])
                        st.session_state["step3_clients"] = merge_uploaded_contacts(
                            st.session_state["step3_clients"], uploaded
                        )
                        added = len(st.session_state["step3_clients"]) - before
                        # Auto-select newly added contacts
                        st.session_state["selected_emails"].update(uploaded["Email"].tolist())
                        st.session_state.pop("client_editor", None)
                        if sync_hs_csv:
                            rows = uploaded.to_dict(orient="records")
                            _sync_contacts_to_hubspot(rows)
                        st.success(f"Imported {added} new contacts.")
                        st.rerun()
                    else:
                        st.error("CSV must contain an 'Email' column.")

            with hs_tab:
                if st.button("Fetch from HubSpot", key="hs_fetch"):
                    with st.spinner("Fetching..."):
                        res = fetch_hubspot_contacts()
                    if res.get("contacts"):
                        existing_emails = set(st.session_state["step3_clients"]["Email"].tolist())
                        rows = []
                        for hc in res["contacts"]:
                            email = hc.get("email", "")
                            if email and email not in existing_emails:
                                rows.append({
                                    "Email": email,
                                    "First Name": hc.get("contact_name", "").split()[0] if hc.get("contact_name") else "",
                                    "Last Name": " ".join(hc.get("contact_name", "").split()[1:]) if hc.get("contact_name") else "",
                                    "Company Name": hc.get("company_name", ""),
                                    "Job Title": "",
                                })
                        if rows:
                            hs_df = pd.DataFrame(rows)
                            st.session_state["step3_clients"] = merge_uploaded_contacts(
                                st.session_state["step3_clients"], hs_df
                            )
                            st.session_state["selected_emails"].update(r["Email"] for r in rows)
                            st.session_state.pop("client_editor", None)
                            st.success(f"Added {len(rows)} HubSpot contacts.")
                            st.rerun()
                        else:
                            st.info("No new contacts to add.")

    # ================================================================
    # SEND TIME SETTING
    # ================================================================
    st.divider()
    st.markdown("#### Send Time")
    send_mode = st.radio(
        "Choose send timing",
        ["Manual send time", "Use each contact's preferred send time"],
        key="send_time_mode",
        horizontal=True,
    )
    if send_mode == "Manual send time":
        sc1, sc2 = st.columns(2)
        with sc1:
            send_date = st.date_input("Send date", key="send_date")
        with sc2:
            from datetime import time as _time
            send_time = st.time_input("Send time", value=_time(9, 0), key="send_time")
        st.session_state["send_time_value"] = f"{send_date} {send_time.strftime('%H:%M')}"
    else:
        st.caption("Each contact will be sent at their preferred time from the contact record.")
        st.session_state["send_time_value"] = "per_contact"

    # ================================================================
    # BOTTOM BAR: Navigation + Send
    # ================================================================
    st.divider()
    col_back, _, col_send = st.columns([1, 2, 1])
    with col_back:
        if st.button("Back to Personas", key="step3_back"):
            st.session_state.gen_step = 2
            for k in (
                "newsletter_full",
                "step3_clients",
                "send_result",
                "nl_edit_subject",
                "nl_edit_body",
                "selected_emails",
                "selected_nl_idx",
            ):
                st.session_state.pop(k, None)
            st.rerun()
    with col_send:
        if st.button("Confirm and Send via HubSpot", type="primary", key="step3_send"):
            _execute_send(thesis, seg_type, edited_df)


def _execute_send(thesis: str, seg_type: str, edited_df: pd.DataFrame):
    """Run the full send workflow: simulate → HubSpot draft → log → metrics."""
    clients_df: pd.DataFrame = st.session_state["step3_clients"]
    selected_emails = st.session_state.get("selected_emails", set())

    # Resolve selected contacts
    if not clients_df.empty and "Email" in clients_df.columns and selected_emails:
        sel_df = clients_df[clients_df["Email"].isin(selected_emails)]
    else:
        sel_df = pd.DataFrame()

    if sel_df.empty:
        st.error("No contacts selected.")
        return

    # Convert to list-of-dicts for the send engine (expects id, email, contact_name, etc.)
    selected: list[dict] = []
    for _, row in sel_df.iterrows():
        selected.append({
            "id": f"csv_{uuid.uuid4().hex[:6]}",
            "contact_name": f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip(),
            "email": row["Email"],
            "company_name": row.get("Company Name", ""),
            "category": seg_type,
            "subcategory": row.get(get_branch_column(seg_type), "") if seg_type in BRANCH_BASIS_MAP else "",
            "needs": row.get("Primary Need", ""),
            "preferred_send_time": row.get("Preferred Send Time", "09:00"),
        })

    subject = st.session_state.get("nl_edit_subject", "")
    body = st.session_state.get("nl_edit_body", "")
    send_time_mode = st.session_state.get("send_time_mode", "Manual send time")
    send_time_value = st.session_state.get("send_time_value", "")

    with st.spinner("Sending campaign..."):
        campaign_id = uuid.uuid4().hex[:8]

        # Group by category for the send engine
        cats: dict[str, list[str]] = {}
        for c in selected:
            cat = c.get("category", seg_type)
            cats.setdefault(cat, []).append(c["id"])

        nl_versions = [
            {"category": cat, "clients": ids, "subject": subject, "body": body}
            for cat, ids in cats.items()
        ]

        content_dict = {
            "campaign_id": campaign_id,
            "thesis": thesis,
            "selected_persona": st.session_state.get("selected_persona", ""),
            "blog_outline": st.session_state.get("blog_edit_outline", st.session_state.get("blog_outline", "")),
            "blog_draft": st.session_state.get("blog_edit_draft", st.session_state.get("blog_draft", "")),
            "newsletter_versions": nl_versions,
            "selected_newsletter_option": {"subject": subject, "body": body},
            "edited": True,
            "approved": True,
            "send_time_mode": send_time_mode,
            "send_time_value": send_time_value,
        }

        # Simulate send
        record = simulate_send_campaign(campaign_id, content_dict, selected)
        log_send_result(record)

        # HubSpot email drafts
        email_results = []
        for g in record.get("group_results", []):
            ep = build_marketing_email_payload(content_dict, g["category"])
            hr = create_marketing_email_draft(ep)
            email_results.append(
                {
                    "persona": g["category"],
                    "email_id": (hr.get("returned_ids") or [""])[0],
                    "endpoint": hr.get("endpoint", ""),
                    "simulated": hr.get("simulated", True),
                }
            )

        # Campaign log
        logs = create_campaign_log_record(content_dict, record, email_results)
        save_campaign_log_records(logs)

        # Persist content
        save_generated_content_json(campaign_id, content_dict)

        # Performance metrics
        metrics = simulate_performance_metrics(campaign_id, selected)
        save_performance_records(metrics)
        report = generate_campaign_report(campaign_id, thesis, metrics)

        st.session_state["last_report"] = report
        # Enrich report with campaign context for the Performance Report page
        report["campaign_context"] = {
            "campaign_id": campaign_id,
            "thesis": thesis,
            "send_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "basis": seg_type,
            "branch": st.session_state.get("selected_persona", ""),
            "layout": st.session_state.get("layout_select", ""),
            "heading": st.session_state.get("heading", DEFAULT_HEADING),
            "signature": st.session_state.get("signature", DEFAULT_SIGNATURE),
            "cta_label": (st.session_state.cta_templates[0]["label"]
                          if st.session_state.cta_templates else ""),
            "cta_url": (st.session_state.cta_templates[0]["url"]
                        if st.session_state.cta_templates else ""),
            "send_time_mode": send_time_mode,
            "send_time_value": send_time_value,
            "total_targeted": len(clients_df),
            "total_sent": len(sel_df),
            "subject": subject,
        }
        # Attach per-contact detail for breakdown analysis
        report["contact_details"] = selected
        st.session_state["send_result"] = record

    st.success(
        f"Campaign **{campaign_id}** sent to {record['sent_count']} recipients!"
    )
    with st.expander("Send Summary", expanded=True):
        rows = [
            {
                "Persona": g["category"].replace("_", " ").title(),
                "Recipients": g["sent"],
                "Subject": g.get("subject", ""),
                "Status": "Sent (simulated)",
            }
            for g in record["group_results"]
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        if send_time_mode == "Manual send time":
            st.caption(f"Scheduled send time: **{send_time_value}**")
        else:
            st.caption("Send timing: **Per-contact preferred send time**")
    st.info("View detailed results on the **Performance Report** page.")

    # ── Brief performance summary ──
    with st.expander("Performance Summary", expanded=True):
        if metrics:
            cats = list({m.get("category", "") for m in metrics})
            best = max(metrics, key=lambda m: m.get("open_rate", 0))
            avg_open = round(sum(m.get("open_rate", 0) for m in metrics) / len(metrics), 1)
            avg_click = round(sum(m.get("click_rate", 0) for m in metrics) / len(metrics), 1)
            total_demo = sum(m.get("demo_clicks", 0) for m in metrics)
            persona_label = st.session_state.get("selected_persona", "").replace("_", " ").title()

            st.markdown(
                f"**Campaign sent to {len(selected)} contacts** across {len(cats)} segment(s).\n\n"
                f"- **Avg Open Rate:** {avg_open}%\n"
                f"- **Avg Click-Through:** {avg_click}%\n"
                f"- **Total Demo Clicks:** {total_demo}\n"
                f"- **Best Segment:** {best.get('category', 'N/A')} "
                f"(open rate {best.get('open_rate', 0)}%)\n"
                f"- **Persona Used:** {persona_label}\n\n"
                f"**Recommended next step:** Double down on **{best.get('category', 'your top segment')}** — "
                f"they showed the strongest engagement. Consider A/B testing subject lines "
                f"for lower-performing segments to lift open rates."
            )
        else:
            st.caption("No performance data available yet.")


# =====================================================================
# PAGE 2 — Info Setting
# =====================================================================

def render_info_setting():
    st.title("Info Setting")
    st.caption(
        "Configure templates and brand settings used by the content generation flow."
    )

    t_cta, t_lay, t_voice, t_heading, t_sig = st.tabs(
        ["CTA Templates", "Layout Templates", "Brand Voice", "Heading", "Signature / Footer"]
    )

    # --- CTA Templates ---
    with t_cta:
        st.subheader("CTA Templates")
        ctas = st.session_state.cta_templates
        for i, cta in enumerate(list(ctas)):
            c1, c2, c3 = st.columns([3, 5, 1])
            cta["label"] = c1.text_input(
                "Label", value=cta["label"], key=f"cta_l_{i}"
            )
            cta["url"] = c2.text_input("URL", value=cta["url"], key=f"cta_u_{i}")
            with c3:
                st.write("")
                if st.button("Delete", key=f"cta_d_{i}"):
                    ctas.pop(i)
                    st.rerun()
        if st.button("+ Add CTA Template"):
            ctas.append({"label": "", "url": ""})
            st.rerun()

    # --- Layout Templates ---
    with t_lay:
        st.subheader("Layout Templates")
        lays = st.session_state.layouts
        for i, lay in enumerate(list(lays)):
            c1, c2, c3 = st.columns([3, 5, 1])
            lay["name"] = c1.text_input(
                "Name", value=lay["name"], key=f"lay_n_{i}"
            )
            lay["desc"] = c2.text_input(
                "Description", value=lay["desc"], key=f"lay_d_{i}"
            )
            with c3:
                st.write("")
                if st.button("Delete", key=f"lay_x_{i}"):
                    lays.pop(i)
                    st.rerun()
        if st.button("+ Add Layout Template"):
            lays.append({"name": "", "desc": ""})
            st.rerun()

    # --- Brand Voice ---
    with t_voice:
        st.subheader("Brand Voice")
        v = st.session_state.brand_voice
        v["tone"] = st.text_input("Tone", value=v["tone"], key="v_tone")
        v["personality"] = st.text_input(
            "Personality", value=v["personality"], key="v_pers"
        )
        v["guidelines"] = st.text_area(
            "Guidelines", value=v["guidelines"], height=120, key="v_guide"
        )

    # --- Heading ---
    with t_heading:
        st.subheader("Heading")
        st.caption("This heading appears at the top of every generated newsletter.")
        st.session_state["heading"] = st.text_input(
            "Newsletter Heading",
            value=st.session_state.get("heading", DEFAULT_HEADING),
            key="v_heading",
        )

    # --- Signature / Footer ---
    with t_sig:
        st.subheader("Signature / Footer")
        st.caption("This signature is appended to the bottom of every newsletter.")
        st.session_state["signature"] = st.text_area(
            "Signature / Footer",
            value=st.session_state.get("signature", DEFAULT_SIGNATURE),
            height=120,
            key="v_signature",
        )

    st.divider()
    if st.button("Save Settings to Disk"):
        _save_settings()
        st.success("Settings saved to data/settings.json!")
    st.caption("Settings are stored in session and used by the Generate Content workflow.")


# =====================================================================
# PAGE 3 — Performance Report
# =====================================================================

# Engagement-tier performance multipliers so mock data is realistic:
# highly-engaged contacts outperform low-engagement ones, high-priority
# contacts convert better, etc.
_BRANCH_PERF = {
    "Highly Engaged":       {"open": (50, 68), "click": (14, 24), "unsub": (0.05, 0.4), "demo": (3, 9)},
    "Moderately Engaged":   {"open": (35, 52), "click": (7, 16),  "unsub": (0.2, 0.9),  "demo": (1, 5)},
    "Low Engagement":       {"open": (18, 35), "click": (2, 8),   "unsub": (0.6, 2.0),  "demo": (0, 2)},
    "Decision Makers":      {"open": (48, 65), "click": (12, 22), "unsub": (0.05, 0.5), "demo": (3, 8)},
    "Operational Users":    {"open": (32, 48), "click": (6, 14),  "unsub": (0.3, 1.0),  "demo": (1, 4)},
    "Creative Practitioners":{"open": (28, 44), "click": (5, 12), "unsub": (0.4, 1.2),  "demo": (0, 3)},
}
_PRIORITY_PERF = {
    "High":   {"open": (50, 66), "click": (14, 24), "unsub": (0.05, 0.4), "demo": (3, 8)},
    "Medium": {"open": (36, 52), "click": (7, 15),  "unsub": (0.2, 0.9),  "demo": (1, 5)},
    "Low":    {"open": (20, 38), "click": (2, 9),   "unsub": (0.5, 1.8),  "demo": (0, 2)},
}
_DEFAULT_PERF = {"open": (30, 55), "click": (5, 16), "unsub": (0.2, 1.2), "demo": (0, 5)}


def _rand_perf(r: dict, n: int = 1) -> dict:
    """Return one simulated row dict from a range dict."""
    return {
        "open_rate":        round(np.random.uniform(*r["open"]), 1),
        "click_rate":       round(np.random.uniform(*r["click"]), 1),
        "unsubscribe_rate": round(np.random.uniform(*r["unsub"]), 2),
        "demo_clicks":      int(np.random.randint(r["demo"][0], r["demo"][1] + 1)),
        "recipients":       n,
    }


def _generate_seed_performance_data() -> dict:
    """Generate believable mock data tied to real CSV contact attributes."""
    np.random.seed(42)
    contacts_df = st.session_state.get("contacts_df", pd.DataFrame())

    # --- Per-branch breakdown ---
    branch_rows = []
    branches = ["Decision Makers", "Operational Users", "Creative Practitioners"]
    for br in branches:
        r = _BRANCH_PERF.get(br, _DEFAULT_PERF)
        cnt = int((contacts_df["Demographic Branch"] == br).sum()) if not contacts_df.empty and "Demographic Branch" in contacts_df.columns else np.random.randint(20, 45)
        row = _rand_perf(r, cnt)
        row["branch"] = br
        branch_rows.append(row)

    # --- Per-priority breakdown ---
    priority_rows = []
    for pri in ["High", "Medium", "Low"]:
        r = _PRIORITY_PERF.get(pri, _DEFAULT_PERF)
        cnt = int((contacts_df["Priority Level"] == pri).sum()) if not contacts_df.empty and "Priority Level" in contacts_df.columns else np.random.randint(15, 40)
        row = _rand_perf(r, cnt)
        row["priority"] = pri
        priority_rows.append(row)

    # --- Trend data (8 weeks) ---
    today = datetime.now()
    dates = [(today - timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(8, 0, -1)]
    trend_rows = []
    for d in dates:
        for br in branches:
            r = _BRANCH_PERF.get(br, _DEFAULT_PERF)
            row = _rand_perf(r, np.random.randint(25, 60))
            row["date"] = d
            row["segment"] = br
            trend_rows.append(row)
    trend_df = pd.DataFrame(trend_rows)

    # --- Top job titles ---
    job_rows = []
    top_jobs = ["CEO", "Head of Growth", "Managing Director", "Content Strategist", "Founder"]
    for jt in top_jobs:
        r_map = _PRIORITY_PERF["High"] if jt in ("CEO", "Founder", "Managing Director") else _DEFAULT_PERF
        row = _rand_perf(r_map, np.random.randint(4, 14))
        row["job_title"] = jt
        job_rows.append(row)

    # --- Aggregate metrics (use branch_rows as the "current campaign" segment metrics) ---
    metrics = []
    for br_row in branch_rows:
        metrics.append({**br_row, "category": br_row["branch"]})

    total_recip = sum(m["recipients"] for m in metrics)
    avg_open = round(sum(m["open_rate"] * m["recipients"] for m in metrics) / max(total_recip, 1), 1)
    avg_click = round(sum(m["click_rate"] * m["recipients"] for m in metrics) / max(total_recip, 1), 1)
    total_demo = sum(m["demo_clicks"] for m in metrics)
    avg_unsub = round(sum(m["unsubscribe_rate"] * m["recipients"] for m in metrics) / max(total_recip, 1), 2)

    best = max(metrics, key=lambda m: m["open_rate"])
    summary_text = (
        f"This campaign reached **{total_recip} contacts** across {len(metrics)} audience branches. "
        f"Weighted open rate was **{avg_open}%** and click-through was **{avg_click}%**. "
        f"**{best['category']}** had the strongest engagement at {best['open_rate']}% open rate."
    )

    # --- Previous benchmark (fake) ---
    prev_benchmark = {
        "open_rate": round(avg_open - np.random.uniform(1.5, 4.5), 1),
        "click_rate": round(avg_click - np.random.uniform(0.5, 2.5), 1),
        "demo_clicks": max(0, total_demo - int(np.random.randint(1, 4))),
        "unsubscribe_rate": round(avg_unsub + np.random.uniform(0.05, 0.25), 2),
        "recipients": max(20, total_recip - int(np.random.randint(5, 20))),
    }

    return {
        "metrics": metrics,
        "summary": {"summary_text": summary_text},
        "recommendation": (
            f"**Double down on {best['category']}** — they convert at the highest rate. "
            f"Consider A/B testing subject lines for lower-performing branches. "
            f"Try a more urgent CTA for medium-priority contacts to lift click-through."
        ),
        "trend_df": trend_df,
        "branch_breakdown": branch_rows,
        "priority_breakdown": priority_rows,
        "job_title_breakdown": job_rows,
        "campaign_context": {
            "campaign_id": "seed_demo",
            "thesis": "AI-powered workflows help agencies scale without burnout",
            "send_date": today.strftime("%Y-%m-%d %H:%M"),
            "basis": "Demographic",
            "branch": best["category"],
            "layout": st.session_state.get("selected_layout", "Clean & Minimal"),
            "heading": st.session_state.get("heading", DEFAULT_HEADING),
            "signature": st.session_state.get("signature", DEFAULT_SIGNATURE),
            "cta_label": st.session_state.cta_templates[0]["label"] if st.session_state.cta_templates else "Book a Demo",
            "cta_url": st.session_state.cta_templates[0]["url"] if st.session_state.cta_templates else "",
            "send_time_mode": "Manual send time",
            "send_time_value": today.strftime("%Y-%m-%d") + " 09:00",
            "total_targeted": total_recip + int(np.random.randint(5, 15)),
            "total_sent": total_recip,
            "subject": f"How AI workflows help {best['category'].lower()} scale",
        },
        "prev_benchmark": prev_benchmark,
    }


def _build_breakdowns_from_contacts(contact_details: list[dict]) -> dict:
    """Build branch / priority / job-title breakdowns from the actual send contacts."""
    np.random.seed(None)
    result = {"branch_breakdown": [], "priority_breakdown": [], "job_title_breakdown": []}
    if not contact_details:
        return result

    cdf = pd.DataFrame(contact_details)

    # Branch breakdown (subcategory field)
    if "subcategory" in cdf.columns:
        for br, grp in cdf.groupby("subcategory"):
            if not br:
                continue
            r = _BRANCH_PERF.get(br, _DEFAULT_PERF)
            row = _rand_perf(r, len(grp))
            row["branch"] = br
            result["branch_breakdown"].append(row)

    # Priority breakdown (not in send payload, simulate from branch)
    for pri in ["High", "Medium", "Low"]:
        r = _PRIORITY_PERF[pri]
        cnt = max(1, len(contact_details) // 3 + int(np.random.randint(-2, 3)))
        row = _rand_perf(r, cnt)
        row["priority"] = pri
        result["priority_breakdown"].append(row)

    # Job title breakdown
    if "company_name" in cdf.columns or True:
        top_jobs = ["CEO", "Head of Growth", "Managing Director", "Content Strategist", "Founder"]
        for jt in top_jobs:
            r_map = _PRIORITY_PERF["High"] if jt in ("CEO", "Founder", "Managing Director") else _DEFAULT_PERF
            row = _rand_perf(r_map, max(1, int(np.random.randint(2, 8))))
            row["job_title"] = jt
            result["job_title_breakdown"].append(row)

    return result


def _generate_campaign_history(current_seed: dict) -> list[dict]:
    """Return a list of 6-8 simulated past campaign records for the overview chart.

    Each record is a self-contained dict with enough data to populate the
    drill-down section when the user selects it from the dropdown.
    """
    np.random.seed(99)
    today = datetime.now()
    theses = [
        "How AI workflows help decision makers scale",
        "Top 5 automation wins for operational teams",
        "Brand storytelling that converts creative professionals",
        "Quarterly industry trends for senior leadership",
        "Personalization tactics that drive demo requests",
        "Data-driven content strategy for growth teams",
        "Reducing churn with proactive outreach",
        "Building trust through thought leadership",
    ]
    branches_pool = list(_BRANCH_PERF.keys())
    layouts = ["Clean & Minimal", "Bold & Visual", "Classic Professional"]
    campaigns: list[dict] = []

    for i in range(7):
        send_dt = today - timedelta(days=(7 - i) * 14 + int(np.random.randint(0, 5)))
        branch = branches_pool[i % len(branches_pool)]
        r = _BRANCH_PERF.get(branch, _DEFAULT_PERF)
        recip = int(np.random.randint(50, 130))

        perf = _rand_perf(r, recip)
        # Per-branch breakdown
        br_rows = []
        for br_name in ["Decision Makers", "Operational Users", "Creative Practitioners"]:
            br_r = _BRANCH_PERF.get(br_name, _DEFAULT_PERF)
            cnt = max(5, recip // 3 + int(np.random.randint(-5, 6)))
            row = _rand_perf(br_r, cnt)
            row["branch"] = br_name
            br_rows.append(row)

        # Per-priority breakdown
        pri_rows = []
        for pri in ["High", "Medium", "Low"]:
            pr_r = _PRIORITY_PERF[pri]
            cnt = max(3, recip // 3 + int(np.random.randint(-4, 5)))
            row = _rand_perf(pr_r, cnt)
            row["priority"] = pri
            pri_rows.append(row)

        # Job title breakdown
        jt_rows = []
        for jt in ["CEO", "Head of Growth", "Managing Director", "Content Strategist", "Founder"]:
            jt_r = _PRIORITY_PERF["High"] if jt in ("CEO", "Founder", "Managing Director") else _DEFAULT_PERF
            row = _rand_perf(jt_r, int(np.random.randint(3, 10)))
            row["job_title"] = jt
            jt_rows.append(row)

        # Trend data (8 weeks ending at send_dt)
        trend_rows = []
        for w in range(8, 0, -1):
            d = (send_dt - timedelta(weeks=w)).strftime("%Y-%m-%d")
            for seg in ["Decision Makers", "Operational Users", "Creative Practitioners"]:
                sr = _BRANCH_PERF.get(seg, _DEFAULT_PERF)
                row = _rand_perf(sr, int(np.random.randint(20, 55)))
                row["date"] = d
                row["segment"] = seg
                trend_rows.append(row)

        # Metrics list (one per branch, used as segment rows)
        metrics = [{**br, "category": br["branch"]} for br in br_rows]
        total_r = sum(m["recipients"] for m in metrics)
        w_open = round(sum(m["open_rate"] * m["recipients"] for m in metrics) / max(total_r, 1), 1)
        w_click = round(sum(m["click_rate"] * m["recipients"] for m in metrics) / max(total_r, 1), 1)
        t_demo = sum(m["demo_clicks"] for m in metrics)
        w_unsub = round(sum(m.get("unsubscribe_rate", 0) * m["recipients"] for m in metrics) / max(total_r, 1), 2)

        best = max(metrics, key=lambda m: m["open_rate"])
        cid = f"camp_{i+1:03d}"
        thesis = theses[i]
        subj = thesis[:50]

        prev_bench = {
            "open_rate": round(w_open - np.random.uniform(1.0, 4.0), 1),
            "click_rate": round(w_click - np.random.uniform(0.5, 2.0), 1),
            "demo_clicks": max(0, t_demo - int(np.random.randint(0, 3))),
            "unsubscribe_rate": round(w_unsub + np.random.uniform(0.02, 0.2), 2),
            "recipients": max(20, total_r - int(np.random.randint(3, 12))),
        }

        campaigns.append({
            "campaign_name": f"Campaign {i+1} — {thesis[:40]}",
            "campaign_id": cid,
            "send_date": send_dt.strftime("%Y-%m-%d %H:%M"),
            "open_rate": w_open,
            "click_rate": w_click,
            "demo_clicks": t_demo,
            "unsubscribe_rate": w_unsub,
            "recipients": total_r,
            "metrics": metrics,
            "summary": {
                "summary_text": (
                    f"Campaign {i+1} reached **{total_r} contacts**. "
                    f"Weighted open rate was **{w_open}%** and CTR **{w_click}%**. "
                    f"**{best['category']}** led engagement."
                ),
            },
            "recommendation": (
                f"Focus on **{best['category']}** for follow-ups. "
                f"Test alternative CTAs for lower-performing branches."
            ),
            "trend_df": pd.DataFrame(trend_rows),
            "branch_breakdown": br_rows,
            "priority_breakdown": pri_rows,
            "job_title_breakdown": jt_rows,
            "campaign_context": {
                "campaign_id": cid,
                "thesis": thesis,
                "send_date": send_dt.strftime("%Y-%m-%d %H:%M"),
                "basis": "Demographic",
                "branch": branch,
                "layout": layouts[i % len(layouts)],
                "heading": st.session_state.get("heading", DEFAULT_HEADING),
                "signature": st.session_state.get("signature", DEFAULT_SIGNATURE),
                "cta_label": "Book a Demo",
                "cta_url": "https://novamind.ai/demo",
                "send_time_mode": "Manual send time" if i % 2 == 0 else "Use each contact's preferred send time",
                "send_time_value": send_dt.strftime("%Y-%m-%d") + " 09:00",
                "total_targeted": total_r + int(np.random.randint(3, 12)),
                "total_sent": total_r,
                "subject": subj,
            },
            "prev_benchmark": prev_bench,
        })

    # Append the current / seed campaign as the latest entry
    cur_ctx = current_seed.get("campaign_context", {})
    cur_metrics = current_seed["metrics"]
    total_r = sum(m.get("recipients", 0) for m in cur_metrics)
    w_open = round(sum(m["open_rate"] * m["recipients"] for m in cur_metrics) / max(total_r, 1), 1)
    w_click = round(sum(m["click_rate"] * m["recipients"] for m in cur_metrics) / max(total_r, 1), 1)
    t_demo = sum(m.get("demo_clicks", 0) for m in cur_metrics)
    w_unsub = round(sum(m.get("unsubscribe_rate", 0) * m["recipients"] for m in cur_metrics) / max(total_r, 1), 2)

    campaigns.append({
        "campaign_name": f"Campaign 8 (Latest) — {cur_ctx.get('thesis', 'Current campaign')[:40]}",
        "campaign_id": cur_ctx.get("campaign_id", "latest"),
        "send_date": cur_ctx.get("send_date", today.strftime("%Y-%m-%d %H:%M")),
        "open_rate": w_open,
        "click_rate": w_click,
        "demo_clicks": t_demo,
        "unsubscribe_rate": w_unsub,
        "recipients": total_r,
        **{k: current_seed[k] for k in ("metrics", "summary", "recommendation", "trend_df",
                                          "branch_breakdown", "priority_breakdown",
                                          "job_title_breakdown", "campaign_context", "prev_benchmark")
           if k in current_seed},
    })
    return campaigns


def render_performance_report():
    st.title("Performance Report")

    # Prefer latest session report, fall back to persisted history
    report = st.session_state.get("last_report")
    if not report:
        history = load_performance_history()
        if history:
            latest_id = history[-1].get("campaign_id", "")
            latest = [r for r in history if r.get("campaign_id") == latest_id]
            if latest:
                report = generate_campaign_report(
                    latest_id, "Previous Campaign", latest
                )

    # Seed with realistic mock data so the dashboard is never empty
    seed = _generate_seed_performance_data()
    is_seed = not report
    if not report:
        report = seed

    # ================================================================
    # 0. CAMPAIGN OVERVIEW (cross-campaign)
    # ================================================================
    all_campaigns = _generate_campaign_history(report if not is_seed else seed)

    st.subheader("Campaign Overview")

    if is_seed:
        st.info("Showing demo data.")

    # -- Overview KPI row (averages across all campaigns) --
    all_open = [c["open_rate"] for c in all_campaigns]
    all_click = [c["click_rate"] for c in all_campaigns]
    all_demo = [c["demo_clicks"] for c in all_campaigns]
    all_recip = [c["recipients"] for c in all_campaigns]

    ov_kpi = st.columns(5)
    ov_kpi[0].metric("Total Campaigns", len(all_campaigns))
    ov_kpi[1].metric("Avg Open Rate", f"{np.mean(all_open):.1f}%")
    ov_kpi[2].metric("Avg CTR", f"{np.mean(all_click):.1f}%")
    ov_kpi[3].metric("Total Demo Clicks", sum(all_demo))
    ov_kpi[4].metric("Total Recipients", sum(all_recip))

    # -- Large cross-campaign chart --
    overview_df = pd.DataFrame({
        "Campaign": [c["campaign_name"].split(" — ")[0] for c in all_campaigns],
        "Open Rate %": all_open,
        "Click Rate %": all_click,
        "Demo Clicks": all_demo,
    }).set_index("Campaign")
    st.line_chart(overview_df)

    # -- Campaign selector dropdown --
    campaign_names = [c["campaign_name"] for c in all_campaigns]
    st.caption(
        "These are mock history campaigns for demo purposes. "
        "Once you create a campaign of your own, it will appear here."
    )
    selected_name = st.selectbox(
        "Select a campaign to drill down",
        campaign_names,
        index=len(campaign_names) - 1,
        key="overview_campaign_select",
    )
    selected_camp = next(c for c in all_campaigns if c["campaign_name"] == selected_name)

    st.divider()

    # ================================================================
    # DRILL-DOWN: use the selected campaign's data
    # ================================================================
    metrics = selected_camp["metrics"]
    summary = selected_camp.get("summary", {})
    trend_df = selected_camp.get("trend_df", seed["trend_df"])
    ctx = selected_camp.get("campaign_context", seed.get("campaign_context", {}))

    # Build breakdowns: prefer actual contact_details if available, else stored breakdowns
    contact_details = selected_camp.get("contact_details", [])
    if contact_details:
        breakdowns = _build_breakdowns_from_contacts(contact_details)
    else:
        breakdowns = {
            "branch_breakdown": selected_camp.get("branch_breakdown", seed.get("branch_breakdown", [])),
            "priority_breakdown": selected_camp.get("priority_breakdown", seed.get("priority_breakdown", [])),
            "job_title_breakdown": selected_camp.get("job_title_breakdown", seed.get("job_title_breakdown", [])),
        }

    prev_benchmark = selected_camp.get("prev_benchmark", seed.get("prev_benchmark", {}))

    # ================================================================
    # 0.5 AI PERFORMANCE SUMMARY
    # ================================================================
    _ps_metrics = selected_camp["metrics"]
    _ps_total = sum(m.get("recipients", 0) for m in _ps_metrics)
    _ps_open = round(sum(m["open_rate"] * m["recipients"] for m in _ps_metrics) / max(_ps_total, 1), 1)
    _ps_click = round(sum(m["click_rate"] * m["recipients"] for m in _ps_metrics) / max(_ps_total, 1), 1)
    _ps_demo = sum(m.get("demo_clicks", 0) for m in _ps_metrics)
    _ps_best = max(_ps_metrics, key=lambda m: m["open_rate"])
    _ps_best_label = _ps_best.get("category", _ps_best.get("branch", "top segment"))
    # Actionable suggestion based on simple rules
    if _ps_click < 8:
        _ps_suggestion = "Consider testing a stronger CTA or moving it higher in the email body to lift click-through."
    elif _ps_open < 35:
        _ps_suggestion = "Try A/B testing subject lines — a more curiosity-driven hook could improve open rates."
    else:
        _ps_suggestion = f"Double down on the {_ps_best_label} segment with tailored follow-up content to maximize conversions."

    st.markdown(
        f"<div style='background:#f8f0f5;border-left:4px solid {ACCENT};"
        f"border-radius:6px;padding:14px 18px;margin-bottom:16px;'>"
        f"<p style='margin:0 0 6px;font-weight:600;color:{ACCENT};font-size:0.9em;'>"
        f"Performance Insight</p>"
        f"<p style='margin:0;color:#333;font-size:0.88em;line-height:1.55;'>"
        f"This campaign reached <b>{_ps_total} contacts</b> with a "
        f"<b>{_ps_open}%</b> open rate and <b>{_ps_click}%</b> click-through, "
        f"generating <b>{_ps_demo}</b> demo clicks. "
        f"<b>{_ps_best_label}</b> was the highest-performing segment at "
        f"{_ps_best['open_rate']}% opens. "
        f"{_ps_suggestion}</p></div>",
        unsafe_allow_html=True,
    )

    # ================================================================
    # 1. EXECUTIVE SNAPSHOT
    # ================================================================
    st.subheader("Executive Snapshot")

    # Campaign identity row
    id_cols = st.columns(5)
    id_cols[0].markdown(f"**Campaign**<br><span style='color:{ACCENT};'>{ctx.get('campaign_id', 'N/A')}</span>", unsafe_allow_html=True)
    id_cols[1].markdown(f"**Sent**<br>{ctx.get('send_date', 'N/A')}", unsafe_allow_html=True)
    id_cols[2].markdown(f"**Basis**<br>{ctx.get('basis', 'N/A')}", unsafe_allow_html=True)
    id_cols[3].markdown(f"**Branch**<br>{ctx.get('branch', 'N/A')}", unsafe_allow_html=True)
    id_cols[4].markdown(f"**Targeted / Sent**<br>{ctx.get('total_targeted', 0)} / {ctx.get('total_sent', 0)}", unsafe_allow_html=True)

    total_recip = sum(m.get("recipients", 0) for m in metrics)
    avg_open = round(sum(m["open_rate"] * m["recipients"] for m in metrics) / max(total_recip, 1), 1)
    avg_click = round(sum(m["click_rate"] * m["recipients"] for m in metrics) / max(total_recip, 1), 1)
    total_demo = sum(m.get("demo_clicks", 0) for m in metrics)
    avg_unsub = round(sum(m.get("unsubscribe_rate", 0) * m["recipients"] for m in metrics) / max(total_recip, 1), 2)

    # KPI cards
    kpi = st.columns(4)
    kpi[0].metric("Open Rate", f"{avg_open}%")
    kpi[1].metric("Click-Through Rate", f"{avg_click}%")
    kpi[2].metric("Demo Clicks", total_demo)
    kpi[3].metric("Unsubscribe Rate", f"{avg_unsub}%")

    st.markdown(summary.get("summary_text", ""))
    st.divider()

    # ================================================================
    # 2. MAIN VISUAL AREA
    # ================================================================
    left_vis, right_vis = st.columns([2, 3], gap="large")

    with left_vis:
        st.subheader("Campaign at a Glance")
        st.markdown(f"**Subject line:** {ctx.get('subject', 'N/A')}")
        st.markdown(f"**Thesis:** {ctx.get('thesis', 'N/A')}")
        st.caption(f"Send mode: {ctx.get('send_time_mode', 'N/A')} — {ctx.get('send_time_value', '')}")

        # Funnel numbers
        st.markdown("---")
        funnel_c = st.columns(3)
        funnel_c[0].metric("Sent", ctx.get("total_sent", total_recip))
        opens = int(round(avg_open / 100 * total_recip))
        funnel_c[1].metric("Est. Opens", opens)
        clicks = int(round(avg_click / 100 * total_recip))
        funnel_c[2].metric("Est. Clicks", clicks)

    with right_vis:
        st.subheader("Engagement Over Time")
        if not trend_df.empty:
            pivot = trend_df.pivot_table(
                index="date", columns="segment", values="open_rate", aggfunc="mean"
            )
            st.line_chart(pivot)
        else:
            cdf = pd.DataFrame(metrics)
            if not cdf.empty and "category" in cdf.columns:
                chart = cdf.set_index("category")[["open_rate", "click_rate"]].rename(
                    columns={"open_rate": "Open Rate %", "click_rate": "Click Rate %"}
                )
                st.bar_chart(chart)

    st.divider()

    # ================================================================
    # 3. BREAKDOWN SECTIONS
    # ================================================================
    st.subheader("Performance Breakdowns")
    br_tab, pri_tab, job_tab = st.tabs(["By Branch", "By Priority Level", "By Job Title"])

    with br_tab:
        br_data = breakdowns.get("branch_breakdown", [])
        if br_data:
            br_df = pd.DataFrame(br_data)
            # Bar chart: open rate vs click rate by branch
            if "branch" in br_df.columns:
                chart_df = br_df.set_index("branch")[["open_rate", "click_rate"]].rename(
                    columns={"open_rate": "Open Rate %", "click_rate": "Click Rate %"}
                )
                st.bar_chart(chart_df)
                st.dataframe(
                    br_df[["branch", "recipients", "open_rate", "click_rate", "demo_clicks", "unsubscribe_rate"]].rename(
                        columns={"branch": "Branch", "recipients": "Recipients", "open_rate": "Open %",
                                 "click_rate": "Click %", "demo_clicks": "Demo Clicks", "unsubscribe_rate": "Unsub %"}
                    ),
                    hide_index=True, use_container_width=True,
                )
        else:
            st.caption("No branch breakdown available.")

    with pri_tab:
        pri_data = breakdowns.get("priority_breakdown", [])
        if pri_data:
            pri_df = pd.DataFrame(pri_data)
            if "priority" in pri_df.columns:
                chart_df = pri_df.set_index("priority")[["open_rate", "click_rate"]].rename(
                    columns={"open_rate": "Open Rate %", "click_rate": "Click Rate %"}
                )
                st.bar_chart(chart_df)
                st.dataframe(
                    pri_df[["priority", "recipients", "open_rate", "click_rate", "demo_clicks", "unsubscribe_rate"]].rename(
                        columns={"priority": "Priority", "recipients": "Recipients", "open_rate": "Open %",
                                 "click_rate": "Click %", "demo_clicks": "Demo Clicks", "unsubscribe_rate": "Unsub %"}
                    ),
                    hide_index=True, use_container_width=True,
                )
        else:
            st.caption("No priority breakdown available.")

    with job_tab:
        jt_data = breakdowns.get("job_title_breakdown", [])
        if jt_data:
            jt_df = pd.DataFrame(jt_data)
            if "job_title" in jt_df.columns:
                chart_df = jt_df.set_index("job_title")[["open_rate", "click_rate"]].rename(
                    columns={"open_rate": "Open Rate %", "click_rate": "Click Rate %"}
                )
                st.bar_chart(chart_df)
                st.dataframe(
                    jt_df[["job_title", "recipients", "open_rate", "click_rate", "demo_clicks"]].rename(
                        columns={"job_title": "Job Title", "recipients": "Recipients", "open_rate": "Open %",
                                 "click_rate": "Click %", "demo_clicks": "Demo Clicks"}
                    ),
                    hide_index=True, use_container_width=True,
                )
        else:
            st.caption("No job title breakdown available.")

    st.divider()

    # ================================================================
    # 4. CONTENT & SEND INSIGHTS
    # ================================================================
    st.subheader("Content & Send Insights")
    ins_left, ins_right = st.columns(2, gap="large")

    with ins_left:
        st.markdown("**Campaign Settings Used**")
        settings_items = {
            "Heading": ctx.get("heading", "N/A"),
            "CTA": f"{ctx.get('cta_label', 'N/A')} — {ctx.get('cta_url', '')}",
            "Layout Template": ctx.get("layout", "N/A"),
            "Signature / Footer": ctx.get("signature", "N/A").replace("\n", " | "),
            "Send Mode": ctx.get("send_time_mode", "N/A"),
            "Send Time": ctx.get("send_time_value", "N/A"),
        }
        for label, val in settings_items.items():
            st.markdown(f"- **{label}:** {val}")

    with ins_right:
        st.markdown("**What Worked & What Didn't**")
        # Generate simple rule-based insights
        best_branch = max(breakdowns.get("branch_breakdown", [{}]), key=lambda x: x.get("open_rate", 0), default={})
        worst_branch = min(breakdowns.get("branch_breakdown", [{}]), key=lambda x: x.get("open_rate", 100), default={})
        insights = []
        if best_branch.get("branch"):
            insights.append(
                f"**{best_branch['branch']}** had the highest open rate at "
                f"{best_branch.get('open_rate', 0)}% — the subject line and CTA resonated well with this audience."
            )
        if worst_branch.get("branch") and worst_branch.get("branch") != best_branch.get("branch"):
            insights.append(
                f"**{worst_branch['branch']}** underperformed at {worst_branch.get('open_rate', 0)}% open rate. "
                f"Consider testing a different subject line or more targeted content for this group."
            )
        if avg_unsub > 0.8:
            insights.append(
                f"Unsubscribe rate ({avg_unsub}%) is above the 0.8% benchmark — review send frequency and content relevance."
            )
        elif avg_unsub <= 0.4:
            insights.append(
                f"Unsubscribe rate ({avg_unsub}%) is well below industry average — content relevance is strong."
            )
        if total_demo > 3:
            insights.append(f"{total_demo} demo clicks indicate strong conversion intent from this campaign.")
        if ctx.get("send_time_mode") == "Use each contact's preferred send time":
            insights.append("Per-contact send timing was used, which typically improves open rates by 5-12%.")

        for ins in insights:
            st.markdown(f"- {ins}")
        if not insights:
            st.caption("Not enough data to generate insights yet.")

    st.divider()

    # ================================================================
    # 5. RECOMMENDATION
    # ================================================================
    st.subheader("Recommendations & Next Steps")
    rec_left, rec_right = st.columns([3, 2])

    with rec_left:
        st.success(report.get("recommendation", "No recommendation available."))
        # Suggested next thesis
        thesis = ctx.get("thesis", "")
        best_cat = best_branch.get("branch", "your top segment")
        st.markdown(
            f"**Suggested next campaign thesis:**\n\n"
            f"*\"How {best_cat.lower()} teams can leverage {thesis.split()[0:4] and ' '.join(thesis.split()[0:4]) or 'targeted strategies'} "
            f"for measurable results\"*"
        )

    with rec_right:
        st.markdown("**Quick Actions**")
        st.markdown(
            "1. Re-run campaign for under-performing segments with new subject line\n"
            "2. Create a follow-up for contacts who opened but didn't click\n"
            "3. Review CTA placement — try a mid-body CTA for longer newsletters\n"
            "4. Schedule next campaign for top-performing send time window"
        )

    st.divider()

    # ================================================================
    # 6. HISTORICAL COMPARISON
    # ================================================================
    st.subheader("Historical Comparison")

    if not prev_benchmark:
        # Fabricate a benchmark
        prev_benchmark = {
            "open_rate": round(avg_open - np.random.uniform(1.5, 4.5), 1),
            "click_rate": round(avg_click - np.random.uniform(0.5, 2.5), 1),
            "demo_clicks": max(0, total_demo - int(np.random.randint(1, 4))),
            "unsubscribe_rate": round(avg_unsub + np.random.uniform(0.05, 0.25), 2),
            "recipients": max(20, total_recip - int(np.random.randint(5, 15))),
        }

    delta_open = round(avg_open - prev_benchmark.get("open_rate", avg_open), 1)
    delta_click = round(avg_click - prev_benchmark.get("click_rate", avg_click), 1)
    delta_demo = total_demo - prev_benchmark.get("demo_clicks", total_demo)
    delta_unsub = round(avg_unsub - prev_benchmark.get("unsubscribe_rate", avg_unsub), 2)

    hc = st.columns(4)
    hc[0].metric("Open Rate", f"{avg_open}%", delta=f"{delta_open:+.1f}pp", delta_color="normal")
    hc[1].metric("Click Rate", f"{avg_click}%", delta=f"{delta_click:+.1f}pp", delta_color="normal")
    hc[2].metric("Demo Clicks", total_demo, delta=f"{delta_demo:+d}", delta_color="normal")
    hc[3].metric("Unsub Rate", f"{avg_unsub}%", delta=f"{delta_unsub:+.2f}pp", delta_color="inverse")

    comp_data = {
        "Metric": ["Open Rate", "Click Rate", "Demo Clicks", "Unsub Rate", "Recipients"],
        "Previous": [
            f"{prev_benchmark.get('open_rate', 0)}%",
            f"{prev_benchmark.get('click_rate', 0)}%",
            prev_benchmark.get("demo_clicks", 0),
            f"{prev_benchmark.get('unsubscribe_rate', 0)}%",
            prev_benchmark.get("recipients", 0),
        ],
        "Current": [f"{avg_open}%", f"{avg_click}%", total_demo, f"{avg_unsub}%", total_recip],
        "Change": [
            f"{delta_open:+.1f}pp",
            f"{delta_click:+.1f}pp",
            f"{delta_demo:+d}",
            f"{delta_unsub:+.2f}pp",
            f"{total_recip - prev_benchmark.get('recipients', total_recip):+d}",
        ],
    }
    st.dataframe(pd.DataFrame(comp_data), hide_index=True, use_container_width=True)

    st.divider()

    # ── Detailed metrics table (preserved) ──
    with st.expander("Full Segment Metrics Table"):
        df = pd.DataFrame(metrics)
        if not df.empty:
            show = [c for c in ["category", "recipients", "open_rate", "click_rate",
                                 "demo_clicks", "unsubscribe_rate"] if c in df.columns]
            st.dataframe(df[show].rename(columns={
                "category": "Segment", "recipients": "Recipients", "open_rate": "Open %",
                "click_rate": "Click %", "demo_clicks": "Demo Clicks", "unsubscribe_rate": "Unsub %",
            }), hide_index=True, use_container_width=True)


# =====================================================================
# PAGE ROUTING
# =====================================================================

if page == "generate":
    render_generate_content()
elif page == "settings":
    render_info_setting()
elif page == "report":
    render_performance_report()
