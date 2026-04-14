# Palona AI — Marketing Content Pipeline

A Streamlit app that generates persona-targeted marketing content using OpenAI, syncs contacts to HubSpot, and simulates campaign analytics.

## Folder Structure

```
palona-takehome/
├── app.py                  # Streamlit entry point
├── requirements.txt
├── .env.example
├── data/
│   ├── contacts_mock.json        # Sample CRM contacts
│   ├── generated_content.json    # Saved generated content
│   ├── campaign_log.json         # Campaign send log
│   └── performance_history.json  # Historical metrics
└── src/
    ├── generate_content.py   # Blog & newsletter generation
    ├── hubspot_client.py     # HubSpot API helpers
    ├── analytics.py          # Simulated metrics & summary
    ├── storage.py            # JSON read/write helpers
    ├── personas.py           # Persona definitions
    └── prompts.py            # Prompt templates
```

## Setup

```bash
cd palona-takehome
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optionally add your API keys
```

## Run

```bash
streamlit run app.py
```

## Mock vs Live Mode

| Feature | Without API keys | With API keys |
|---------|-----------------|---------------|
| Content generation | Returns placeholder text | Calls OpenAI |
| HubSpot sync | Returns mock success | Creates real contacts |
| Campaign metrics | Always simulated | Always simulated |

Set `OPENAI_API_KEY` and/or `HUBSPOT_API_KEY` in `.env` to enable live integrations.
