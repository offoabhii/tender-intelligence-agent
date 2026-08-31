import time
from app.config import SEARCH_QUERIES
from app.scraper import fetch_text, search_with_tavily
from app.auditor import audit_and_extract
from app.db import save_tender, log_system_status, init_db
from app.notifier import send_alert

def run_pipeline():
    init_db()
    log_system_status("RUNNING", "Pipeline started")
    total_saved = 0
    try:
        for category, queries in SEARCH_QUERIES.items():
            for q in queries:
                urls = search_with_tavily(q, max_results=5)
                for url in urls:
                    # Only accept gov / gem domains for REAL proof
                    if not any(x in url for x in ["gov.in", "gem.gov", "etenders", "eprocure"]):
                        continue
                    text = fetch_text(url)
                    tenders = audit_and_extract(text, url)
                    for t in tenders:
                        # CRITICAL: Only save if closing date is future and link is gov
                        if t.is_open_now and t.closing_date != "NOT SURE":
                            save_tender(t)
                            total_saved += 1
                    time.sleep(1)
        
        log_system_status("SUCCESS", f"Saved {total_saved} REAL tenders")
        print(f"Done. Saved {total_saved} REAL")

    except Exception as e:
        log_system_status("FAILED", str(e))
        send_alert(f"AGENT BROKEN: {e}")
        # DO NOT SEED FAKE - show empty with FAILED status instead
        raise
