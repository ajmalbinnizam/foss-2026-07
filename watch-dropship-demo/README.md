# Watch Dropshipping Multi-Agent Demo

A standalone stage demo: a supplier message comes in, three smolagents (ingestion, market
research, copywriting) process it under a manager agent, LangGraph gates the result behind a
margin-based human-approval step, and an approved listing goes live on a local storefront.

This is a separate demo from the FOSS Contribution Matchmaker in `notebooks/foss_demo.ipynb` —
see the root `CLAUDE.md` for that one. Nothing here is wired into that pipeline.

## Setup

```bash
cd watch-dropship-demo
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
jupyter notebook demo.ipynb
```

`GROQ_API_KEY` is required (free tier at https://console.groq.com/keys). The Telegram variables
are only needed for the live-approval step — if they're missing, use the local fallback cell in
the notebook instead (`telegram_bot.resume_locally(...)`), which drives the exact same
LangGraph resume path.

## Running the pieces standalone

- `python app.py` — storefront on http://localhost:5000 (also started automatically from
  `demo.ipynb`, cell 2).
- `python -c "from multi_agent_system import build_manager_agent; build_manager_agent()"` —
  smoke-test that the 3 agents + manager construct correctly.

## Files

| File | Role |
|---|---|
| `multi_agent_system.py` | The 3 smolagents + manager (Groq via LiteLLM) |
| `workflow.py` | LangGraph `StateGraph` with the `interrupt()`-based approval gate |
| `telegram_bot.py` | Inline-keyboard approval bot + local resume fallback |
| `app.py` / `templates/` / `static/` | Flask storefront |
| `store_data.json` | Catalog "database" — read/written by `app.py` and `workflow.py` |
| `demo.ipynb` | The stage presentation notebook |
