"""
Tender Intelligence Agent Pipeline

Workflow:
1. Runs real search/scrape for each category.
2. Uses the auditor to extract relevant tenders.
3. Rejects Net Cost bus operations.
4. Saves only valid real results in data/live_tenders.json.
5. Writes health status so failures are visible.
"""

import json
import os
from datetime import datetime, timezone
from types import SimpleNamespace

from config import SOURCES, CATEGORIES_ALLOWED
from app.scraper import fetch_tender_sources
from app.auditor import IntelligentAuditor
from app.db import init_db, save_tender, log_system_status


OUTPUT_FILE = os.path.join("data", "live_tenders.json")


def normalize_tender(item: dict, source_name: str) -> dict:
    """
    Normalizes different auditor outputs into one stable JSON structure.
    Does NOT create fake values.
    Missing values remain NOT SURE.
    """

    category = str(item.get("category", "")).strip()

    # Strict category whitelist.
    if category not in CATEGORIES_ALLOWED:
        return {}

    # Support both old and new field names.
    is_net_cost = bool(
        item.get("is_net_cost_model", item.get("is_net_cost", False))
    )

    # Absolute hard rule:
    # Bus operations must be Gross Cost only.
    if category == "Bus operations (gross cost only)" and is_net_cost:
        print(f"[REJECTED] Net Cost bus tender: {item.get('title', 'Unknown title')}")
        return {}

    title = str(item.get("title", "")).strip()
    if not title or title.upper() in {"NOT SURE", "N/A", "NONE"}:
        return {}

    def safe_value(field_name, default="NOT SURE"):
        value = item.get(field_name, default)
        if value is None:
            return default

        value = str(value).strip()

        if not value or value.lower() in {"none", "null", "n/a", "-", "unknown"}:
            return default

        return value

    return {
        "title": title,
        "source_url": safe_value("source_url", source_name),
        "category": category,
        "closing_date": safe_value("closing_date"),
        "issued_by": safe_value("issued_by"),
        "qualification_criteria": safe_value("qualification_criteria"),
        "eligibility_status": safe_value("eligibility_status"),
        "is_net_cost": is_net_cost,
        "is_open_now": bool(
            item.get("is_currently_open", item.get("is_open_now", False))
        ),
        "extraction_confidence": safe_value(
            "confidence_score",
            safe_value("extraction_confidence", "LOW")
        ),
        "found_at": datetime.now(timezone.utc).isoformat(),
        "source_name": source_name
    }


def save_json(tenders: list[dict]) -> None:
    """Persist real tender output in a Git-friendly JSON file."""
    os.makedirs("data", exist_ok=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(tenders),
        "data_source": "LIVE_FETCHED_DATA",
        "tenders": tenders
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    print(f"[DATA] Wrote {len(tenders)} real records to {OUTPUT_FILE}")


def run_pipeline() -> int:
    """
    Executes the full real-data tender discovery pipeline.

    Returns:
        Number of valid, real tenders found.
    """

    start_time = datetime.now(timezone.utc)

    print("=" * 65)
    print("TENDER INTELLIGENCE AGENT — REAL DATA PIPELINE")
    print(f"Started: {start_time.isoformat()}")
    print("=" * 65)

    init_db()
    log_system_status("RUNNING", "Pipeline started")

    auditor = IntelligentAuditor()

    valid_tenders: list[dict] = []
    seen_keys = set()
    source_errors = []

    for source_name, source_value in SOURCES.items():
        print(f"\n[SCAN] Source: {source_name}")
        print(f"[SCAN] Query/URL: {source_value}")

        try:
            # Your scraper may accept source name or a query/URL.
            # We first use source_name because the Tavily scraper maps it to category query.
            raw_content = fetch_tender_sources(source_name)

            if not raw_content:
                error = f"{source_name}: empty response"
                source_errors.append(error)
                print(f"[WARNING] {error}")
                continue

            if str(raw_content).startswith("ERROR"):
                error = f"{source_name}: {raw_content[:250]}"
                source_errors.append(error)
                print(f"[WARNING] {error}")
                continue

            if len(raw_content) < 150:
                error = f"{source_name}: response too short ({len(raw_content)} chars)"
                source_errors.append(error)
                print(f"[WARNING] {error}")
                continue

            print(f"[SCAN] Retrieved {len(raw_content)} characters.")

            # Auditor analyzes actual returned web content.
            extracted = auditor.analyze_page(
                raw_content=raw_content,
                source_url=str(source_value)
            )

            if not extracted:
                print("[AUDIT] No matching open tenders found in this source.")
                continue

            print(f"[AUDIT] Auditor returned {len(extracted)} possible tenders.")

            for item in extracted:
                if not isinstance(item, dict):
                    continue

                tender = normalize_tender(item, source_name)

                if not tender:
                    continue

                # Prevent duplicates in the same run.
                key = (
                    tender["title"].lower().strip(),
                    tender["source_url"].lower().strip()
                )

                if key in seen_keys:
                    continue

                seen_keys.add(key)
                valid_tenders.append(tender)

                # Save to SQLite too, but JSON is the Streamlit Cloud source of truth.
                try:
                    db_object = SimpleNamespace(
                        title=tender["title"],
                        source_url=tender["source_url"],
                        category=tender["category"],
                        closing_date=tender["closing_date"],
                        issued_by=tender["issued_by"],
                        qualification_criteria=tender["qualification_criteria"],
                        eligibility_status=tender["eligibility_status"],
                        is_net_cost=tender["is_net_cost"],
                        is_open_now=tender["is_open_now"],
                        extraction_confidence=tender["extraction_confidence"]
                    )
                    save_tender(db_object)
                except Exception as db_error:
                    # Do not lose genuine JSON output just because SQLite has an issue.
                    print(f"[WARNING] SQLite save issue: {db_error}")

        except Exception as source_error:
            message = f"{source_name}: {type(source_error).__name__}: {source_error}"
            source_errors.append(message)
            print(f"[ERROR] {message}")

    # Always write JSON, even when zero results occur.
    # This proves when the last scan happened and prevents stale fake data.
    save_json(valid_tenders)

    completed_at = datetime.now(timezone.utc)
    duration = int((completed_at - start_time).total_seconds())

    if source_errors and not valid_tenders:
        status_message = (
            f"Completed with warnings. Found 0 matching tenders. "
            f"Source errors: {' | '.join(source_errors[:3])}"
        )
        log_system_status("WARNING", status_message)
    else:
        status_message = (
            f"Pipeline completed. Found {len(valid_tenders)} valid real tenders "
            f"in {duration}s."
        )
        log_system_status("RUNNING", status_message)

    print("\n" + "=" * 65)
    print(status_message)
    print("=" * 65)

    return len(valid_tenders)
