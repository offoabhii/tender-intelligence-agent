"""
Gemini-powered strict tender auditor.

The auditor extracts information only from actual text returned by Tavily.

Hard rules:
- Four categories only.
- Current/future closing date required.
- Bus Operations must explicitly prove Gross Cost.
- Net Cost Bus Operations are rejected.
- Unknown data becomes NOT SURE.
"""

import json
import os
import re
from datetime import date
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.config import (
    BUS_OPERATIONS_CATEGORY,
    CATEGORIES_ALLOWED,
    COMPANY_PROFILE,
    TODAY,
)

load_dotenv()


class IntelligentAuditor:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY", "").strip()

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. Add it in .env and GitHub Secrets."
            )

        self.client = genai.Client(api_key=api_key)

        # You can change this through GitHub secret/variable if needed.
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

        print(f"[AUDITOR] Gemini model: {self.model}")

    def analyze_document(
        self,
        document_content: str,
        document_url: str,
        target_category: str,
    ) -> list[dict]:
        """
        Extract valid tenders from one real source page.

        Returns an empty list when:
        - no valid tender is found;
        - closing date cannot be proven;
        - tender is expired;
        - Bus Operations contract is Net Cost or unclear.
        """

        if target_category not in CATEGORIES_ALLOWED:
            return []

        if not document_content or len(document_content.strip()) < 100:
            return []

        system_prompt = f"""
You are a strict government tender verification auditor.

TODAY: {TODAY.isoformat()}

TARGET CATEGORY:
{target_category}

MANDATORY RULES:

1. Extract only current tender opportunities related to TARGET CATEGORY.

2. A tender must have a clearly stated closing/bid-submission date.
   Convert it to YYYY-MM-DD.
   If the date is unclear, missing, historical, or before today: reject it.

3. BUS OPERATIONS RULE:
   - Only Gross Cost contracts are acceptable.
   - If the tender says Net Cost, Net Rate, Net Model, L1 Net,
     revenue-risk model, or a cost model is unclear: reject it.
   - A valid Bus Operations tender must contain direct evidence
     that it is Gross Cost.

4. Do not extract tender archives, tender results, awards, corrigenda,
   historical notices, or expired tenders.

5. Never invent facts.
   If issuer, qualifications, or company eligibility cannot be verified,
   use exactly: NOT SURE.

6. Company eligibility policy:
{COMPANY_PROFILE}

Return only valid JSON. Required structure:

{{
  "tenders": [
    {{
      "title": "Exact title from source",
      "category": "{target_category}",
      "closing_date": "YYYY-MM-DD",
      "issued_by": "Issuer or NOT SURE",
      "qualification_criteria": "Requirements summary or NOT SURE",
      "eligibility_status": "ELIGIBLE or NOT ELIGIBLE or NOT SURE",
      "is_net_cost": false,
      "is_open_now": true,
      "confidence": "HIGH or MEDIUM or LOW",
      "evidence": "Exact short source quote proving tender and date"
    }}
  ]
}}

If no tender fully meets the rules, return:
{{"tenders":[]}}
"""

        user_prompt = f"""
REAL SOURCE URL:
{document_url}

REAL SOURCE CONTENT:
{document_content[:12000]}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": system_prompt},
                            {"text": user_prompt},
                        ],
                    }
                ],
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                    max_output_tokens=2500,
                ),
            )

            raw_text = response.text or ""
            parsed = self._parse_json(raw_text)

            if isinstance(parsed, dict):
                tenders = parsed.get("tenders", [])
            elif isinstance(parsed, list):
                tenders = parsed
            else:
                tenders = []

            if not isinstance(tenders, list):
                return []

            verified_tenders = []

            for tender in tenders:
                if not isinstance(tender, dict):
                    continue

                tender["source_url"] = document_url
                tender["category"] = target_category

                if self._passes_hard_rules(tender):
                    verified_tenders.append(tender)

            return verified_tenders

        except Exception as error:
            print(f"[AUDITOR] Gemini extraction failed for {document_url}: {error}")
            return []

    @staticmethod
    def _parse_json(text: str) -> Any:
        """Safely parse Gemini JSON output."""

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        cleaned = re.sub(
            r"^```(?:json)?",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        cleaned = re.sub(r"```$", "", cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _passes_hard_rules(tender: dict) -> bool:
        """
        Python validation layer.
        The LLM cannot bypass these checks.
        """

        category = str(tender.get("category", "")).strip()

        if category not in CATEGORIES_ALLOWED:
            return False

        title = str(tender.get("title", "")).strip()

        if not title or title.upper() in {"NOT SURE", "N/A", "NONE"}:
            return False

        # Must be explicitly open.
        if tender.get("is_open_now") is not True:
            return False

        closing_date_text = str(tender.get("closing_date", "")).strip()

        try:
            closing_date = date.fromisoformat(closing_date_text)
        except ValueError:
            return False

        # Reject closed/old tenders.
        if closing_date < TODAY:
            return False

        tender["closing_date"] = closing_date.isoformat()

        # Net Cost Bus Operations = absolute rejection.
        if (
            category == BUS_OPERATIONS_CATEGORY
            and bool(tender.get("is_net_cost", False))
        ):
            return False

        # Gross Cost must be visibly proven for Bus Operations.
        if category == BUS_OPERATIONS_CATEGORY:
            evidence = str(tender.get("evidence", "")).lower()
            title_lower = title.lower()

            gross_cost_proven = (
                "gross cost" in evidence
                or "gross cost" in title_lower
                or "gross cost model" in evidence
                or "gross cost contract" in evidence
            )

            if not gross_cost_proven:
                return False

        # Honest defaults for unknown values.
        for field in [
            "issued_by",
            "qualification_criteria",
            "eligibility_status",
            "confidence",
            "evidence",
        ]:
            value = tender.get(field)

            if value is None or not str(value).strip():
                tender[field] = "NOT SURE"

        eligibility = str(
            tender.get("eligibility_status", "NOT SURE")
        ).upper()

        if eligibility not in {"ELIGIBLE", "NOT ELIGIBLE", "NOT SURE"}:
            tender["eligibility_status"] = "NOT SURE"
        else:
            tender["eligibility_status"] = eligibility

        confidence = str(tender.get("confidence", "LOW")).upper()

        if confidence not in {"HIGH", "MEDIUM", "LOW"}:
            tender["confidence"] = "LOW"
        else:
            tender["confidence"] = confidence

        return True
