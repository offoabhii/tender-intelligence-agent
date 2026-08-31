import time
from app.config import SEARCH_QUERIES
from app.scraper import fetch_text, search_with_tavily
from app.auditor import audit_and_extract
from app.db import save_tender, log_system_status, init_db

def run_pipeline():
    init_db()
    log_system_status("RUNNING", "Pipeline started")
    total = 0
    try:
        for cat, queries in SEARCH_QUERIES.items():
            for q in queries:
                urls = search_with_tavily(q, max_results=5)
                for url in urls:
                    if not any(x in url for x in ["gov.in", "gem.gov"]): continue
                    text = fetch_text(url)
                    tenders = audit_and_extract(text, url)
                    for t in tenders:
                        if t.is_open_now:
                            save_tender(t)
                            total += 1
                    time.sleep(1)
        log_system_status("SUCCESS", f"Saved {total} REAL open tenders")
        print(f"Done {total}")
    except Exception as e:
        log_system_status("FAILED", str(e))
        raise
