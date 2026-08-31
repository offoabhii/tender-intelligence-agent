"""
Real Tender Intelligence Pipeline.

Tavily -> Gemini -> strict Python validation -> JSON -> Streamlit.
"""

import json
import os
from datetime import datetime, timezone

from app.auditor import IntelligentAuditor
from app.config import SEARCHES, TAVILY_RESULTS_PER_CATEGORY
from app.db import init_db, log_system_status, save_tender
from app.notifier import send_alert
from app.scraper import fetch_tender_sources

DATA_DIR = "data"
LIVE_TENDERS_FILE = os.path.join(DATA_DIR, "live_tenders.json")
HEALTH_FILE = os.path.join(DATA_DIR, "health.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(file_path: str, payload: dict):
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def write_health(status: str, message: str, details: list[str] | None = None):
    payload = {
        "status": status,
        "message": message,
        "updated_at": utc_now(),
        "details": details or [],
    }

    write_json(HEALTH_FILE, payload)

    try:
        log_system_status(status, message)
    except Exception as error:
        print(f"[HEALTH] SQLite health logging warning: {error}")


def deduplicate_tenders(tenders: list[dict]) -> list[dict]:
    unique_tenders = []
    seen = set()

    for tender in tenders:
        title = str(tender.get("title", "")).strip().lower()
        url = str(tender.get("source_url", "")).strip().lower()

        key = (title, url)

        if not title or not url or key in seen:
            continue

        seen.add(key)
        unique_tenders.append(tender)

    return unique_tenders


def run_pipeline() -> int:
    """
    Run the complete real-data pipeline.

    Returns:
        Number of strictly verified tender opportunities.

    Raises:
        RuntimeError only if every search source failed.
    """

    print("=" * 70)
    print("TENDER INTELLIGENCE AGENT — LIVE REAL DATA SCAN")
    print(f"Started: {utc_now()}")
    print("=" * 70)

    os.makedirs(DATA_DIR, exist_ok=True)

    init_db()

    write_health(
        "RUNNING",
        "Live tender scan started.",
    )

    auditor = IntelligentAuditor()

    all_tenders = []
    errors = []
    summary = []

    for category, search_query in SEARCHES.items():
        print(f"\n[SEARCH] Category: {category}")
        print(f"[SEARCH] Query: {search_query}")

        try:
            documents = fetch_tender_sources(
                search_query=search_query,
                max_results=TAVILY_RESULTS_PER_CATEGORY,
            )

            print(f"[SEARCH] Documents returned: {len(documents)}")

            if not documents:
                summary.append(
                    f"{category}: no web documents returned."
                )
                continue

            verified_count = 0

            for document in documents:
                source_url = document["url"]

                print(f"[AUDIT] Source: {source_url}")

                extracted = auditor.analyze_document(
                    document_content=document["content"],
                    document_url=source_url,
                    target_category=category,
                )

                for tender in extracted:
                    tender["found_at"] = utc_now()
                    all_tenders.append(tender)
                    verified_count += 1

            summary.append(
                f"{category}: {verified_count} verified tender(s)."
            )

        except Exception as error:
            error_message = (
                f"{category}: {type(error).__name__}: {error}"
            )

            errors.append(error_message)
            summary.append(error_message)

            print(f"[ERROR] {error_message}")

    verified_tenders = deduplicate_tenders(all_tenders)

    # Optional SQLite audit persistence.
    for tender in verified_tenders:
        try:
            save_tender(tender)
        except Exception as error:
            print(
                f"[DATABASE WARNING] Could not save "
                f"{tender.get('title', 'Unknown tender')}: {error}"
            )

    # This is the real dashboard data source.
    # No fake data is ever added.
    live_payload = {
        "data_source": "LIVE_FETCHED_DATA",
        "generated_at": utc_now(),
        "record_count": len(verified_tenders),
        "tenders": verified_tenders,
        "source_summary": summary,
    }

    write_json(LIVE_TENDERS_FILE, live_payload)

    # All category searches failing is a genuine system failure.
    if len(errors) == len(SEARCHES):
        message = (
            "Pipeline failed: every live search source failed. "
            + " | ".join(errors)
        )

        write_health("FAILED", message, summary)
        send_alert(message, severity="CRITICAL")
        raise RuntimeError(message)

    # Zero results can be correct under strict filters.
    if not verified_tenders:
        message = (
            "Scan completed, but no verified open tenders met all strict rules."
        )

        write_health(
            "SUCCESS_ZERO_RESULTS",
            message,
            summary,
        )

    else:
        message = (
            f"Scan completed successfully. "
            f"{len(verified_tenders)} verified open tender(s) found."
        )

        write_health("SUCCESS", message, summary)

    print("\n" + "=" * 70)
    print(message)
    print(f"Saved live data: {LIVE_TENDERS_FILE}")
    print("=" * 70)

    return len(verified_tenders)
