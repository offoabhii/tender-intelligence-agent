from app.config import SEARCH_QUERIES
from app.scraper import search_with_tavily_enriched, scrape_etenders_direct, scrape_cppp_direct, fetch_text
from app.auditor import audit_and_extract, heuristic_from_search
from app.db import save_tender, log_system_status, init_db
import time

def run_pipeline():
    init_db()
    log_system_status("RUNNING", "Fetching REAL from etenders.gov.in + cppp")
    total=0
    # 1. Direct HTML scrape - ALWAYS works
    for res in scrape_etenders_direct() + scrape_cppp_direct():
        if not any(x in res["url"] for x in ["gov.in"]): continue
        tenders=audit_and_extract(res["content"], res["url"])
        if not tenders: tenders=heuristic_from_search(res)
        for t in tenders: save_tender(t); total+=1

    # 2. Search fallback
    for cat, queries in SEARCH_QUERIES.items():
        for q in queries:
            for res in search_with_tavily_enriched(q, max_results=5):
                url=res.get("url")
                if not url or "gov.in" not in url: continue
                text=fetch_text(url)
                if "SCRAPE_FAILED" in text: text=res.get("title","")+"\n"+res.get("content","")
                tenders=audit_and_extract(text, url)
                if not tenders: tenders=heuristic_from_search(res)
                for t in tenders: save_tender(t); total+=1
                time.sleep(1)

    log_system_status("SUCCESS", f"Saved {total} REAL tenders from gov.in")
    print(f"Done {total} REAL")
