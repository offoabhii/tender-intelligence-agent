from app.scraper import search_with_tavily_enriched, scrape_via_jina
from app.auditor import heuristic_from_search, audit_and_extract
from app.db import save_tender, log_system_status, init_db
from app.config import SEARCH_QUERIES
import time

def run_pipeline():
    init_db()
    log_system_status("RUNNING", "Fetching REAL via Jina")
    total=0
    # 1. Direct HTML via Jina - ALWAYS works, no key needed
    for url in ["https://etenders.gov.in/eprocure/app?page=FrontEndLatestActiveTenders&service=page","https://eprocure.gov.in/cppp/latestactivetenders"]:
        for res in scrape_via_jina(url):
            tenders=audit_and_extract(res["content"], res["url"])
            if not tenders: tenders=heuristic_from_search(res)
            for t in tenders: save_tender(t); total+=1

    # 2. Search GeM
    for cat, queries in SEARCH_QUERIES.items():
        for q in queries:
            for res in search_with_tavily_enriched(q, max_results=5):
                if "gov.in" not in res["url"]: continue
                tenders=heuristic_from_search(res)
                for t in tenders: save_tender(t); total+=1
                time.sleep(1)

    log_system_status("SUCCESS", f"Saved {total} REAL tenders from gov.in")
    print(f"Done {total} REAL")
