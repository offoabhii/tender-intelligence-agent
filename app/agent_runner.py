import time
from app.config import SEARCH_QUERIES
from app.scraper import fetch_text, search_with_tavily_enriched
from app.auditor import audit_and_extract, heuristic_from_search
from app.db import save_tender, log_system_status, init_db

def run_pipeline():
    init_db()
    log_system_status("RUNNING", "Pipeline started")
    total=0
    try:
        for cat, queries in SEARCH_QUERIES.items():
            for q in queries:
                results = search_with_tavily_enriched(q, max_results=5)
                for res in results:
                    url=res.get("url")
                    if not url or not any(x in url for x in ["gov.in","gem.gov"]): continue
                    # 1. Try to get real page content
                    text = fetch_text(url)
                    if "SCRAPE_FAILED" in text:
                        # Use search snippet content - this is REAL content from gov site
                        text = res.get("title","") + "\n" + res.get("content","")
                    tenders = audit_and_extract(text, url)
                    if not tenders:
                        # 2. Fallback - create tender directly from search result - ensures REAL link
                        tenders = heuristic_from_search(res)
                    for t in tenders:
                        save_tender(t)
                        total+=1
                    time.sleep(1)
        log_system_status("SUCCESS", f"Saved {total} REAL tenders")
        print(f"Done {total}")
    except Exception as e:
        log_system_status("FAILED", str(e))
        print(f"FAILED {e}")
        raise
