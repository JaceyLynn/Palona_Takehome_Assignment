# NovaMind AI-Powered Marketing Content Pipeline

A Streamlit-based prototype for an AI-assisted marketing workflow that generates blog and newsletter content, targets recipients through CRM logic, and evaluates campaign performance to inform future content decisions.

This project was built as a take-home assignment for a fictional early-stage AI startup, **NovaMind**, which helps small creative agencies automate their daily workflows.

---

## Assignment Coverage

This prototype is designed to cover the core requirements of the take-home assignment:

- **AI Content Generation**
  - generates a blog outline
  - generates a short-form blog draft
  - generates persona-targeted newsletter content

- **CRM + Newsletter Distribution**
  - creates or updates contacts in CRM or mock mode
  - tags or segments recipients by persona / branch logic
  - routes the selected newsletter content to the chosen recipient group
  - logs campaign metadata including title, newsletter selection, and send timing

- **Performance Logging & Analysis**
  - stores or simulates campaign performance metrics
  - supports historical comparison across campaigns
  - generates a brief AI-powered or rule-based performance summary
  - recommends a next-step content direction

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Flow Diagram](#flow-diagram)
- [Tools, APIs, and Models](#tools-apis-and-models)
- [Project Structure](#project-structure)
- [Instructions to Run Locally](#instructions-to-run-locally)
- [Assumptions and Mock Data](#assumptions-and-mock-data)
- [Core Workflow](#core-workflow)
- [Testing](#testing)

---

## Architecture Overview

The app is organized into five layers, all running locally in a single Streamlit process.

### 1. Streamlit UI Layer (`app.py`)
Three-page app with sidebar navigation:
- **Generate Content** — 3-step campaign workflow (Campaign Input → Choose Persona → Detail Edit & Send)
- **Marketing Settings** — CTA templates, layout templates, brand voice, heading/header image, signature/footer
- **Performance Report** — Campaign overview, drill-down analytics, AI-powered insights

### 2. AI Content Generation Layer (`src/content_generator.py`, `src/prompts.py`)
- Calls **OpenAI GPT-4o-mini** for blog outlines, blog drafts, persona-targeted newsletters, and thesis suggestions
- Every generator has a **built-in mock fallback** — the full workflow runs without any API keys
- Prompts are centralized in `src/prompts.py`

### 3. CRM / Contact Layer (`src/hubspot_client.py`, `src/contacts.py`)
- Loads 100 mock contacts from CSV (`data/hubspot_mock_contacts_100.csv`) with 29 fields each
- Contacts are segmented by 5 branch types: Demographic, Behavioral, Engagement, Lifecycle Stage, Interest
- **Live mode**: syncs contacts and creates marketing email drafts via HubSpot API (private-app token)
- **Mock mode**: simulates all CRM operations locally

### 4. Post-Approval Orchestration Layer (`src/zapier_client.py`)
- On campaign confirmation, sends a structured JSON payload to a **Zapier webhook**
- Payload includes campaign ID, thesis, persona, subject, body, recipients, and send time
- Falls back to simulated success when no webhook URL is configured
- Keeps all local generation and storage intact — Zapier handles downstream distribution only

### 5. Storage & Analytics Layer (`src/storage.py`, `src/analytics.py`, `src/send_engine.py`)
- Generated blog and newsletter outputs are stored in structured JSON files (generated_content.json) to satisfy the assignment requirement for structured content storage.
- Performance metrics are simulated with realistic distributions (open rates, click-through, demo clicks)
- Campaign reports include cross-campaign comparison, KPI trends, and rule-based AI recommendations

---

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      STREAMLIT UI                           │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────────┐  │
│  │  Step 1   │──▶│   Step 2     │──▶│      Step 3        │  │
│  │ Campaign  │   │ Choose       │   │ Edit, Preview,     │  │
│  │ Input     │   │ Persona      │   │ Select Recipients  │  │
│  └──────────┘   └──────────────┘   └────────┬───────────┘  │
│                                              │              │
│                                     Confirm & Send          │
└──────────────────────────────────────────────┼──────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────┐
                    ▼                          ▼                  ▼
          ┌─────────────────┐      ┌──────────────────┐  ┌──────────────┐
          │  Local Storage   │      │  HubSpot API     │  │ Zapier       │
          │  (JSON files)    │      │  (email drafts,  │  │ Webhook      │
          │  • campaign log  │      │   contacts)      │  │ (downstream  │
          │  • content       │      │  Mock if no token │  │  orchestration)
          │  • metrics       │      └──────────────────┘  └──────────────┘
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Performance      │
          │ Report Page      │
          │ • KPI trends     │
          │ • AI insights    │
          │ • Recommendations│
          └─────────────────┘
```

---

## Tools, APIs, and Models

| Category | Tool / Service | Purpose |
|----------|---------------|---------|
| **Frontend** | Streamlit | Web UI framework with session state, data editing, and sidebar navigation |
| **AI Model** | OpenAI GPT-4o-mini | Blog outlines, blog drafts, persona newsletters, thesis suggestions |
| **CRM** | HubSpot API (v3) | Contact sync, marketing email draft creation (private-app token auth) |
| **Automation** | Zapier Webhooks | Post-approval campaign orchestration (email distribution, notifications) |
| **Data** | pandas | Contact filtering, data display, CSV import/export |
| **Storage** | Local JSON files | Campaign logs, generated content, performance history, settings |
| **Environment** | python-dotenv | Load API keys from `.env` file |
| **HTTP** | requests | Zapier webhook calls, HubSpot API calls |
| **Language** | Python 3.13+ | Runtime |

---

## Project Structure

```
palona-takehome/
├── app.py                          # Main Streamlit app (all pages)
├── requirements.txt                # Python dependencies
├── .env.example                    # Template for environment variables
├── README.md
│
├── src/
│   ├── analytics.py                # Simulate metrics, generate reports, AI recommendations
│   ├── clients.py                  # Load/filter client list from JSON
│   ├── contacts.py                 # CSV contact loading, branch mapping, filtering
│   ├── content_generator.py        # OpenAI content generation with mock fallback
│   ├── generate_content.py         # Additional content generation helpers
│   ├── hubspot_client.py           # HubSpot API integration (contacts, email drafts)
│   ├── models.py                   # Data model factories (plain dicts)
│   ├── personas.py                 # Persona definitions (3 defaults)
│   ├── prompts.py                  # Prompt templates for OpenAI
│   ├── send_engine.py              # Campaign send simulation and logging
│   ├── storage.py                  # JSON file read/write helpers
│   └── zapier_client.py            # Zapier webhook client (live/mock)
│
├── data/
│   ├── campaign_log.json           # Campaign send history
│   ├── clients.json                # Client list (legacy)
│   ├── contacts_mock.json          # Mock contact data
│   ├── generated_content.json      # Persisted AI-generated content
│   ├── performance_history.json    # Simulated campaign metrics
│   └── generated_markdown/         # Exported markdown content
│
└── test_*.py                       # 9 test files (pytest)
```

---

## Instructions to Run Locally

### Prerequisites
- Python 3.10+ (developed on 3.13)
- pip

### 1. Clone the repository

```bash
git clone https://github.com/JaceyLynn/Palona_Takehome_Assignment.git
cd Palona_Takehome_Assignment/palona-takehome
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. (Optional) Configure API keys

Copy the example file and add your keys. **All keys are optional** — the app runs fully in demo/mock mode without them.

```bash
cp .env.example .env
```

Edit `.env`:
```
OPENAI_API_KEY=your-openai-api-key-here        # Enables live AI generation
HUBSPOT_ACCESS_TOKEN=your-hubspot-token-here    # Enables live CRM sync
ZAPIER_WEBHOOK_URL=https://hooks.zapier.com/... # Enables live webhook delivery
```

### 5. Run the app

```bash
streamlit run app.py
```

The app opens at **http://localhost:8501**.

### 6. Run tests

```bash
python3 -m pytest --ignore=test_smoke.py -v
```

---

## Assumptions and Mock Data

### Mock / Demo Mode (default — no API keys needed)

| Component | Mock Behavior |
|-----------|--------------|
| **AI Generation** | Returns hardcoded blog outlines, drafts, and newsletter bodies. Content is realistic but static. |
| **HubSpot CRM** | All contact sync and email draft creation is simulated locally. No API calls are made. |
| **Zapier Webhook** | Returns a simulated success response with a generated request ID and timestamp. |
| **Contact Data** | 100 mock contacts loaded from CSV with realistic fields (name, email, company, job title, priority, needs, send time preferences, branch segments). |
| **Performance Metrics** | Simulated with randomized but realistic distributions for open rates, click-through rates, and demo clicks. |
| **Campaign Logging** | All campaigns are logged to local JSON files regardless of mode. |

### Key Assumptions

1. **Single-user prototype** — No authentication, multi-tenancy, or concurrent access handling. Session state is per-browser-tab.
2. **Local-first storage** — All data lives in `data/*.json`. No database is used. This is intentional for a take-home demo.
3. **Simulated sends** — The "send" action simulates delivery. Actual email delivery would be handled by Zapier actions or a dedicated ESP in production.
4. **Persona-to-branch mapping** — Each persona maps to a demographic branch for contact pre-filtering (e.g., "Agency Founder" → "Decision Makers"). This mapping is hardcoded for the demo dataset.
5. **Campaign thesis pre-filled in demo mode** — When no OpenAI key is configured, Step 1 pre-fills a sample thesis for quick testing.
6. **Performance data is synthetic** — Metrics are generated per campaign with randomized values. No real email tracking is implemented.
7. **HubSpot private-app token auth** — The integration uses a simple bearer token (no OAuth flow). This is standard for internal/prototype tools.

### Live Mode

When API keys are provided in `.env`, the app:
- Generates content via **OpenAI GPT-4o-mini** (blog outlines, drafts, persona newsletters)
- Creates marketing email drafts in **HubSpot** and syncs contacts
- Posts campaign payloads to a **Zapier webhook** for downstream orchestration

The sidebar shows the current mode for each service: **AI**, **CRM**, and **Zapier** (Live or Mock).

---

## Core Workflow

### Step 1 — Campaign Content
The user enters a campaign thesis or brief. The app generates a blog outline and draft. The interface also supports optional image and document uploads for richer campaign context in the prototype.

### Step 2 — Choose Persona
The user selects one of three personas (or clicks "Suggest Different Categories" for 6 alternative personas across 2 sets). The selected persona drives newsletter content and recipient filtering.

### Step 3 — Detail Edit & Send
- Blog outline and draft (editable, with regenerate option)
- Three persona-tailored newsletter options (subject + body)
- Subject line and body editing
- Header image (from Marketing Settings or Step 1 upload) shown in preview
- Recipient list pre-filtered by persona's demographic branch
- Filters: persona, company, job title, priority level
- Full newsletter preview with heading, subject, hero image, body, and signature
- Send time setting (manual or per-contact preferred)
- Confirm & Send triggers the post-approval workflow, which may include simulated send behavior, HubSpot draft creation, campaign logging, performance metric generation, and Zapier webhook handoff depending on configured integrations.

### Performance Report
- Campaign Overview with multi-campaign history
- AI-powered performance insight (rule-based)
- Executive Snapshot with KPIs
- Campaign drill-down with segment-level breakdown

---

## Testing

9 test files covering:
- Campaign log record creation and formatting
- HubSpot client simulated behavior
- Content generator mock fallback
- Send engine simulation
- Storage persistence
- Analytics and mapping logic

Run all tests:
```bash
python3 -m pytest --ignore=test_smoke.py -v
```