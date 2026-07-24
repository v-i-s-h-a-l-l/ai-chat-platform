"""Context-aware document classification using GPT-OSS-20B (Groq)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx

from app.config import settings
from app.services.upload_validation.types import (
    DocumentSample,
    PiiInventory,
    UploadPolicyDecision,
)

logger = logging.getLogger(__name__)

_CLASSIFIER_SYSTEM = """You classify uploaded documents for a RAG knowledge base.

Return ONLY valid JSON (no markdown fences):
{
  "document_type": string,
  "confidence": number,
  "decision": "allow" | "warn" | "restrict",
  "reason": string
}

Policy:
- ALLOW expected personal/business contact info in: Research Paper, Academic Paper, IEEE Paper, arXiv Paper, Resume/CV, Business Card, Invoice, Technical Documentation, User Manual, Book, Presentation, Meeting Notes.
- WARN for: Medical Record, Bank Statement, Credit Card Statement, Passport, Aadhaar, PAN Card, Driving Licence.
- RESTRICT only when the document clearly contains live payment credentials (card numbers with CVV/OTP/PIN) unrelated to a legitimate business document context.

Author names and institutional emails in research papers are EXPECTED — allow them.
Resume contact details are EXPECTED — allow them.
Invoice business contact info is EXPECTED — allow them.

Be concise. Keep reason under one sentence."""


class DocumentUploadClassifier:
    """Groq GPT-OSS-20B classifier for ambiguous upload decisions."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    async def classify(
        self,
        sample: DocumentSample,
        inventory: PiiInventory,
        *,
        existing_pii_violation: str | None = None,
    ) -> tuple[UploadPolicyDecision, str, float, str]:
        payload = self._build_payload(sample, inventory, existing_pii_violation)
        data = await self._post_with_retry(payload)
        return self._parse_response(data)

    def _build_payload(
        self,
        sample: DocumentSample,
        inventory: PiiInventory,
        existing_pii_violation: str | None,
    ) -> dict[str, Any]:
        summary = {
            "title": sample.title,
            "filename": sample.filename,
            "first_page_text": sample.first_page_text[:1800],
            "document_statistics": {"pages": sample.page_count},
            "detected_pii": inventory.as_dict(),
        }
        if existing_pii_violation:
            summary["existing_guardrail_signal"] = existing_pii_violation

        user_message = json.dumps(summary, ensure_ascii=False)

        return {
            "model": settings.groq_prompt_optimization_model,
            "messages": [
                {"role": "system", "content": _CLASSIFIER_SYSTEM},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.0,
            "max_tokens": 256,
            "response_format": {"type": "json_object"},
        }

    def _headers(self) -> dict[str, str]:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not configured")
        return {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        }

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=settings.prompt_opt_connect_timeout,
            read=settings.prompt_opt_read_timeout,
            write=5.0,
            pool=5.0,
        )

    async def _post_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        max_retries = settings.prompt_opt_max_retries
        base_backoff = settings.prompt_opt_retry_backoff_seconds
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout()) as client:
                    response = await client.post(
                        self.BASE_URL,
                        headers=self._headers(),
                        json=payload,
                    )
                if response.status_code in {429, 502, 503, 504} and attempt < max_retries:
                    await asyncio.sleep(base_backoff * (2**attempt))
                    continue
                if response.status_code >= 400:
                    raise ValueError(f"Groq API error ({response.status_code})")
                return response.json()
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt >= max_retries:
                    break
                await asyncio.sleep(base_backoff * (2**attempt))

        raise ValueError(f"Upload classification failed: {last_error}") from last_error

    def _parse_response(self, data: dict[str, Any]) -> tuple[UploadPolicyDecision, str, float, str]:
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("Empty Groq response")

        content = choices[0].get("message", {}).get("content", "")
        parsed = self._parse_json(content)

        decision_raw = str(parsed.get("decision", "warn")).lower()
        if decision_raw == "allow":
            decision = UploadPolicyDecision.ALLOW
        elif decision_raw == "restrict":
            decision = UploadPolicyDecision.RESTRICT
        else:
            decision = UploadPolicyDecision.WARN

        document_type = str(parsed.get("document_type") or "Unknown Document").strip()
        confidence = float(parsed.get("confidence") or 0.7)
        reason = str(parsed.get("reason") or "Classification completed").strip()
        return decision, document_type, confidence, reason

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Classifier JSON must be an object")
        return parsed
