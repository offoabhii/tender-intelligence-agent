"""
Strict Tender Auditor.

Uses Groq dynamically:
- asks Groq for currently available models;
- tests available models;
- avoids deprecated hardcoded model IDs.

OpenAI is optional fallback.

The auditor does NOT create data.
It only extracts facts present in the source content.
"""

import json
import os
import re
from datetime import date
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from config import (
    BUS_OPERATIONS_CATEGORY,
    CATEGORIES_ALLOWED,
    COMPANY_PROFILE,
    TODAY,
)


class IntelligentAuditor:
    def __init__(self):
        self.client = None
        self.provider = None
        self.model = None

        self._configure_client()

    def _configure_client(self) -> None:
        """Configure Groq first, OpenAI second."""

        groq_key = os.getenv("GROQ_API_KEY", "").strip()

        if groq_key:
            try:
                from groq import Groq

                groq_client = Groq(api_key=groq_key)
                groq_model = self._find_working_groq_model(groq_client)

                if groq_model:
                    self.client = groq_client
                    self.provider = "GROQ"
                    self.model = groq_model
                    print(f"[AUDITOR] Provider: GROQ | Model: {self.model}")
                    return

            except Exception as error:
                print(f"[AUDITOR] Groq setup failed: {error}")

        openai_key = os.getenv("OPENAI_API_KEY", "").strip()

        if openai_key:
            try:
                from openai import OpenAI

                self.client = OpenAI(api_key=openai_key)
                self.provider = "OPENAI"
                self.model = "gpt-4o-mini"
                print(f"[AUDITOR] Provider: OPENAI | Model: {self.model}")
                return

            except Exception as error:
                print(f"[AUDITOR] OpenAI setup failed: {error}")

        raise RuntimeError(
            "No working AI provider found. Add GROQ_API_KEY or OPENAI_API_KEY."
        )

    def _find_working_groq_model(self, client) -> str | None:
        """
        Dynamically discover a working Groq text model.

        This prevents issues such as:
        - model_not_found
        - model_decommissioned
        """

        try:
            models_response = client.models.list()
            model_ids = [model.id for model in models_response.data]
        except Exception as error:
            print(f"[AUDITOR] Could not list Groq models: {error}")
            return None

        excluded_words = [
            "whisper",
            "guard",
            "tts",
            "speech",
            "audio",
            "transcribe",
            "playai",
        ]

        candidates = [
            model_id
            for model_id in model_ids
            if not any(word in model_id.lower() for word in excluded_words)
        ]

        # Prefer generally capable chat models if available.
        candidates.sort(
            key=lambda model_id: (
                "gpt-oss" not in model_id.lower(),
                "qwen" not in model_id.lower(),
                "llama" not in model_id.lower(),
                "deepseek" not in model_id.lower(),
                model_id.lower(),
            )
        )

        print(f"[AUDITOR] Testing {len(candidates)} currently listed Groq models...")

        for model_id in candidates[:20]:
            try:
                client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {
                            "role": "user",
                            "content": "Reply exactly with OK.",
                        }
                    ],
                    temperature=0,
                    max_tokens=5,
                )

                print(f"[AUDITOR] Working Groq model found: {model_id}")
                return model_id

            except Exception:
                continue

        return None

    def analyze_document(
        self,
        document_content: str,
        document_url: str,
        target_category: str,
    ) -> list[dict]:
        """
        Extract candidate tenders from one real URL/document.

        Returns an empty list if:
        - no valid tender exists;
        - details are insufficient;
        - the LLM call fails.
        """

        if target_category not in CATEGORIES_ALLOWED:
            return []

        if not document_content or len(document_content.strip()) < 100:
            return []

        system_prompt = f"""
You are a strict government tender verification auditor.

TODAY'S DATE: {TODAY.isoformat()}

ALLOWED CATEGORY:
{target_category}

BUS OPERATIONS CRITICAL RULE:
- Only Gross Cost contracts are allowed.
- If Bus Operations uses Net Cost, Net Rate, Net Model, revenue-risk model,
  L1 net model, or the cost model cannot be proven as Gross Cost:
  reject it. Do not output it.

CURRENT/OPEN CRITICAL RULE:
- Only output a tender when its closing date is explicitly present
  AND can be verified as today or a future date.
- If closing date is missing, unclear, expired, or appears historical:
  reject it.
- Do not output tender archives, award notices, corrigenda alone,
  old tender lists, or completed tenders.

FACTUAL INTEGRITY:
- Use only information visible in the supplied source content.
- Never invent issuer, closing date, qualification, tender number,
  eligibility, or cost model.
- For unknown issuer/qualification/eligibility write exactly "NOT SURE".
- Eligibility must be "NOT SURE" unless it is provable from the company
  profile and the source content.

COMPANY PROFILE:
{COMPANY_PROFILE}

Return ONLY valid JSON in exactly this structure:
{{
  "tenders": [
    {{
      "title": "Exact tender title",
      "category": "{target_category}",
      "closing_date": "YYYY-MM-DD",
      "issued_by": "Issuer name or NOT SURE",
      "qualification_criteria": "Requirement summary or NOT SURE",
      "eligibility_status": "ELIGIBLE, NOT ELIGIBLE, or NOT SURE",
      "is_net_cost": false,
      "is_open_now": true,
      "confidence": "HIGH, MEDIUM, or LOW",
      "evidence": "Short exact evidence quote from source"
    }}
  ]
}}

If there are no proven current valid tenders, return:
{{"tenders":[]}}
"""

        user_prompt = f"""
SOURCE URL:
{document_url}

SOURCE CONTENT:
{document_content[:12000]}
"""

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                max_tokens=2200,
            )

            response_text = completion.choices[0].message.content or ""
            parsed = self._parse_json(response_text)

            if isinstance(parsed, list):
                items = parsed
            elif isinstance(parsed, dict):
                items = parsed.get("tenders", [])
            else:
                items = []

            if not isinstance(items, list):
                return []

            verified = []

            for item in items:
                if not isinstance(item, dict):
                    continue

                item["source_url"] = document_url
                item["category"] = target_category

                if self._passes_hard_rules(item):
                    verified.append(item)

            return verified

        except Exception as error:
            print(f"[AUDITOR] Failed to analyze {document_url}: {error}")
            return []

    def _parse_json(self, text: str) -> Any:
        """Parse plain JSON or JSON wrapped in Markdown code fences."""

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Remove ```json / ``` fences if model uses them.
        cleaned = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try extracting first JSON object.
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)

        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}

        return {}

    def _passes_hard_rules(self, item: dict) -> bool:
        """Second non-LLM validation layer."""

        category = str(item.get("category", "")).strip()

        if category not in CATEGORIES_ALLOWED:
            return False

        title = str(item.get("title", "")).strip()

        if not title or title.upper() in {"NOT SURE", "N/A", "NONE"}:
            return False

        # Must explicitly be marked open.
        if item.get("is_open_now") is not True:
            return False

        # Hard-reject Net Cost bus tenders.
        if (
            category == BUS_OPERATIONS_CATEGORY
            and bool(item.get("is_net_cost", False))
        ):
            return False

        # Gross Cost must be proven for Bus Operations.
        if category == BUS_OPERATIONS_CATEGORY:
            evidence = str(item.get("evidence", "")).lower()
            title_lower = title.lower()

            gross_cost_proven = (
                "gross cost" in evidence
                or "gross cost" in title_lower
                or "gross cost model" in evidence
            )

            if not gross_cost_proven:
                return False

        closing_date = str(item.get("closing_date", "")).strip()

        try:
            verified_date = date.fromisoformat(closing_date)
        except ValueError:
            return False

        # Closing date must be today or later.
        if verified_date < TODAY:
            return False

        item["closing_date"] = verified_date.isoformat()

        for field in [
            "issued_by",
            "qualification_criteria",
            "eligibility_status",
            "confidence",
            "evidence",
        ]:
            value = item.get(field)

            if value is None or not str(value).strip():
                item[field] = "NOT SURE"

        allowed_eligibility = {"ELIGIBLE", "NOT ELIGIBLE", "NOT SURE"}

        if str(item["eligibility_status"]).upper() not in allowed_eligibility:
            item["eligibility_status"] = "NOT SURE"

        item["confidence"] = str(item["confidence"]).upper()

        if item["confidence"] not in {"HIGH", "MEDIUM", "LOW"}:
            item["confidence"] = "LOW"

        return True
