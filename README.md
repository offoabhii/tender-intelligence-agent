# Tender Intelligence Agent - Autonomous

We want an agent that we can leave running. Every time we open the page, it already shows new, real, currently open tenders.

### Quick Start
1. `cp .env.example .env` and fill keys
2. `pip install -r requirements.txt`
3. `python run_agent.py` # first run populates DB
4. `streamlit run app/dashboard.py`

### Engineering Decisions (why this won't break every week)
- **Tavily Search API over BeautifulSoup selectors:** Selectors break when site changes. AI search returns URLs by meaning, then LLM parses page by context.
- **SQLite/Postgres + Streamlit:** Persistence so page is never empty. Dashboard reads DB, not live LLM call.
- **Auditor Agent:** Second pass with temp=0.1, strict JSON, hard filter for Gross Cost.
- **Health Check:** SystemLog table + file + Discord alert.

### Demo Video Script
1. Open dashboard - show 2-3 real open tenders, green Active.
2. Show filter: Bus Ops only Gross Cost.
3. Show a NOT SURE field.
4. Show .github/workflows/agent.yml running every 6h.
5. Show system_health.log.