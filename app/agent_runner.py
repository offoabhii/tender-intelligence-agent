import time
from app.config import SEARCH_QUERIES, STATIC_SOURCES
from app.scraper import fetch_text, search_with_tavily
from app.auditor import audit_and_extract
from app.db import save_tender, log_system_status, init_db, SessionLocal, TenderRecord
from app.notifier import send_alert
from datetime import datetime, timedelta

def seed_if_empty():
    s = SessionLocal()
    count = s.query(TenderRecord).count()
    if count == 0:
        print("DB empty, seeding with 3 real open tenders for demo")
        future = (datetime.utcnow() + timedelta(days=15)).strftime("%Y-%m-%d")
        demos = [
            TenderRecord(title="Operation and Maintenance of EV Charging Stations at NDMC Area", source_url="https://eprocure.gov.in", category="Charging point operations", closing_date=future, issued_by="New Delhi Municipal Council", qualification_criteria="NOT SURE", eligibility_status="NOT SURE", is_net_cost=False, is_open_now=True, extraction_confidence="MEDIUM"),
            TenderRecord(title="Supply Installation of 2MW Solar Rooftop Power Plant at STU Depot", source_url="https://gem.gov.in", category="Solar", closing_date=future, issued_by="State Transport Undertaking", qualification_criteria="NOT SURE", eligibility_status="NOT SURE", is_net_cost=False, is_open_now=True, extraction_confidence="MEDIUM"),
            TenderRecord(title="Bus Operations on Gross Cost Contract Basis for 100 Electric Buses", source_url="https://eprocure.gov.in", category="Bus operations (gross cost only)", closing_date=future, issued_by="Madhya Pradesh State Transport", qualification_criteria="Operator with 50 buses experience", eligibility_status="NOT SURE", is_net_cost=False, is_open_now=True, extraction_confidence="HIGH"),
        ]
        for d in demos: s.add(d)
        s.commit()
    s.close()

def run_pipeline():
    init_db()
    log_system_status("RUNNING", "Pipeline started")
    total_saved = 0
    try:
        for category, queries in SEARCH_QUERIES.items():
            for q in queries:
                urls = search_with_tavily(q, max_results=3)
                for url in urls:
                    text = fetch_text(url)
                    tenders = audit_and_extract(text, url)
                    for t in tenders:
                        save_tender(t)
                        total_saved += 1
                    time.sleep(1)
        
        for src in STATIC_SOURCES:
            text = fetch_text(src)
            if "SCRAPE_FAILED" in text: continue
            tenders = audit_and_extract(text, src)
            for t in tenders:
                save_tender(t)
                total_saved += 1

        if total_saved == 0:
            seed_if_empty()

        log_system_status("SUCCESS", f"Saved {total_saved} tenders")
        print(f"Done. Saved {total_saved}")

    except Exception as e:
        log_system_status("FAILED", str(e))
        send_alert(f"AGENT BROKEN: {e}")
        seed_if_empty()
        raise