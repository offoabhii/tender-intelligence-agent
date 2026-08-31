"""
Real Tender Intelligence Pipeline.

Pipeline:
1. Tavily searches real tender-related web pages.
2. Groq/OpenAI audits each actual source.
3. Python validates current date/category/Gross Cost rules.
4. Results are saved to data/live_tenders.json.
5. GitHub Actions commits the JSON so Streamlit Cloud can display it.
"""

import json
import os
from datetime import datetime, timezone

from app.auditor import IntelligentAuditor
from app.db import init_db, log_system_status, save_tender
from app.notifier import send_alert
from app.scraper import fetch_tender_sources
from config import SEARCHES, TAVILY_RESULTS_PER_CATEGORY


DATA_DIR = "data"
LIVE_TENDERS_FILE = os.path.join(DATA_DIR, "live_tenders.json")
HEALTH_FILE = os.path.join(DATA_DIR, "health.json")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path: str, payload: dict):
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


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
        print(f"[HEALTH] SQLite health logging failed: {error}")


def deduplicate(tenders: list[dict]) -> list[dict]:
    unique = []
    seen = set()

    for tender in tenders:
        key = (
            tender.get("title", "").strip().lower(),
            tender.get("source_url", "").strip().lower(),
        )

        if not key[0] or not key[1] or key in seen:
            continue

        seen.add(key)
        unique.append(tender)

    return unique


def run_pipeline() -> int:
    """
    Execute a real tender scan.

    Returns:
        The number of verified, currently open tenders found.

    Raises:
        RuntimeError if all searches fail.
    """

    started_at = utc_now()

    print("=" * 72)
    print("TENDER INTELLIGENCE AGENT — REAL LIVE DATA PIPELINE")
    print(f"Started at: {started_at}")
    print("=" * 72)

    os.makedirs(DATA_DIR, exist_ok=True)
    init_db()

    write_health(
        "RUNNING",
        "Tender scan started.",
    )

    auditor = IntelligentAuditor()

    all_verified_tenders = []
    source_failures = []
    source_summary = []

    for category, search_query in SEARCHES.items():
        print(f"\n[SEARCH] Category: {category}")
        print(f"[SEARCH] Query: {search_query}")

        try:
            documents = fetch_tender_sources(
                search_query=search_query,
                max_results=TAVILY_RESULTS_PER_CATEGORY,
            )

            print(f"[SEARCH] Tavily returned {len(documents)} document(s).")

            if not documents:
                source_summary.append(
                    f"{category}: search returned zero documents."
                )
                continue

            category_count = 0

            for document in documents:
                document_url = document["url"]
                document_content = document["content"]

                print(f"[AUDIT] Checking: {document_url}")

                extracted = auditor.analyze_document(
                    document_content=document_content,
                    document_url=document_url,
                    target_category=category,
                )

                for tender in extracted:
                    all_verified_tenders.append(tender)
                    category_count += 1

            source_summary.append(
                f"{category}: {category_count} verified tender(s)."
            )

        except Exception as error:
            failure = f"{category}: {type(error).__name__}: {error}"
            source_failures.append(failure)
            source_summary.append(failure)

            print(f"[ERROR] {failure}")

    verified_tenders = deduplicate(all_verified_tenders)

    # Save each verified tender in local SQLite audit storage.
    for tender in verified_tenders:
        try:
            save_tender(tender)
        except Exception as error:
            print(
                f"[DATABASE WARNING] Could not save SQLite record "
                f"for {tender.get('title', 'Unknown')}: {error}"
            )

    # This JSON is the only dashboard data source.
    # No fake records are added here.
    live_payload = {
        "data_source": "LIVE_FETCHED_DATA",
        "generated_at": utc_now(),
        "started_at": started_at,
        "record_count": len(verified_tenders),
        "tenders": verified_tenders,
        "source_summary": source_summary,
    }

    write_json(LIVE_TENDERS_FILE, live_payload)

    # If every category failed, this is a true system failure.
    if len(source_failures) == len(SEARCHES):
        message = (
            "Pipeline failed: all live data sources failed. "
            + " | ".join(source_failures)
        )

        write_health(
            "FAILED",
            message,
            source_summary,
        )

        send_alert(message, severity="CRITICAL")
        raise RuntimeError(message)

    # Zero verified tenders is NOT automatically a system failure.
    # It may mean all results were irrelevant, expired, Net Cost,
    # or lacked a verifiable closing date.
    if len(verified_tenders) == 0:
        message = (
            "Scan completed successfully, but no verified current tenders "
            "matched the strict rules."
        )

        write_health(
            "SUCCESS_ZERO_RESULTS",
            message,
            source_summary,
        )

    else:
        message = (
            f"Scan completed successfully. "
            f"{len(verified_tenders)} verified current tender(s) found."
        )

        write_health(
            "SUCCESS",
            message,
            source_summary,
        )

    print("\n" + "=" * 72)
    print(message)
    print(f"Real data saved to: {LIVE_TENDERS_FILE}")
    print("=" * 72)

    return len(verified_tenders)
