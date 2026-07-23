import asyncio
import json
import logging
import re
from typing import Any

import httpx

from app.config import settings
from app.services.prompt_optimization_provider import (
    PromptOptimizationProvider,
    PromptOptimizationProviderResult,
)

logger = logging.getLogger(__name__)

_OPTIMIZER_SYSTEM = """You are a prompt safety reviewer and proofreader for an AI chatbot platform.

You MUST return ONLY valid JSON (no markdown fences, no commentary) matching this schema:

{
  "safe": boolean,
  "reason": string | null,
  "improvedPrompt": string | null,
  "changes": string[]
}

## STEP 1 — Safety review

Set "safe" to false ONLY when the system prompt actively instructs the assistant to facilitate harm, including:
- fraud, phishing, malware, ransomware
- terrorism or mass violence
- sexual exploitation (especially involving minors)
- instructions to commit illegal activities or violent crimes

DO NOT reject prompts that merely mention sensitive topics for legitimate purposes, such as:
- cybersecurity education, ethical hacking, penetration testing
- criminal law, healthcare, finance, legal research
- interview prep, coding help, research assistants

When unsafe:
- "safe": false
- "reason": one clear sentence explaining why
- "improvedPrompt": null
- "changes": []

## STEP 2 — If safe, proofread the prompt

You are NOT a prompt generator. Preserve the user's intent exactly.

Allowed edits ONLY:
- fix grammar and spelling
- improve sentence structure and formatting
- remove ambiguity
- make instructions clearer and more consistent
- improve readability for another LLM

FORBIDDEN:
- changing user intent
- inventing new features, capabilities, or requirements
- making assumptions
- exaggerating or marketing language ("world's best", etc.)
- rewriting into a completely different prompt

The improved prompt should be at most ~20% longer than the original. Prefer concise clarity over verbosity.

When safe:
- "safe": true
- "reason": null
- "improvedPrompt": the proofread version (never empty)
- "changes": 2–5 short bullet labels describing edits (e.g. "Corrected grammar", "Improved formatting")
"""


class GroqPromptOptimizationProvider(PromptOptimizationProvider):
    """Groq-backed single-call safety + optimization using GPT-OSS-20B."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        *,
        max_retries: int | None = None,
        base_backoff_seconds: float | None = None,
    ) -> None:
        self._max_retries = max_retries if max_retries is not None else settings.prompt_opt_max_retries
        self._base_backoff = (
            base_backoff_seconds
            if base_backoff_seconds is not None
            else settings.prompt_opt_retry_backoff_seconds
        )

    def _headers(self) -> dict[str, str]:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not configured")
        return {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        }

    def _build_user_message(
        self, project_name: str, description: str, system_prompt: str
    ) -> str:
        parts = [
            f"Project name: {project_name}",
            f"Description: {description or '(none)'}",
            "",
            "System prompt to review:",
            "---",
            system_prompt,
            "---",
        ]
        return "\n".join(parts)

    def _build_payload(self, user_message: str) -> dict[str, Any]:
        return {
            "model": settings.groq_prompt_optimization_model,
            "messages": [
                {"role": "system", "content": _OPTIMIZER_SYSTEM},
                {"role": "user", "content": user_message},
            ],
            "temperature": settings.prompt_opt_temperature,
            "max_tokens": settings.prompt_opt_max_tokens,
            "response_format": {"type": "json_object"},
        }

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=settings.prompt_opt_connect_timeout,
            read=settings.prompt_opt_read_timeout,
            write=5.0,
            pool=5.0,
        )

    async def _post_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout()) as client:
                    response = await client.post(
                        self.BASE_URL,
                        headers=self._headers(),
                        json=payload,
                    )
                if response.status_code in {429, 502, 503, 504} and attempt < self._max_retries:
                    delay = self._base_backoff * (2**attempt)
                    logger.warning(
                        "Groq prompt optimization retry %s/%s after HTTP %s (sleep %.1fs)",
                        attempt + 1,
                        self._max_retries,
                        response.status_code,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                if response.status_code >= 400:
                    raise ValueError(
                        f"Groq API error ({response.status_code}): {response.text[:500]}"
                    )
                return response.json()
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    break
                delay = self._base_backoff * (2**attempt)
                logger.warning(
                    "Groq prompt optimization transport retry %s/%s: %s",
                    attempt + 1,
                    self._max_retries,
                    exc,
                )
                await asyncio.sleep(delay)
        raise ValueError(
            f"Prompt optimization request failed after retries: {last_error}"
        ) from last_error

    @staticmethod
    def _parse_json_content(raw: str) -> dict[str, Any]:
        text = raw.strip()
        # Strip accidental markdown fences
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Model returned invalid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Model JSON must be an object")
        return parsed

    @staticmethod
    def _normalize_result(
        data: dict[str, Any], original_prompt: str
    ) -> PromptOptimizationProviderResult:
        safe = bool(data.get("safe"))
        reason = data.get("reason")
        if isinstance(reason, str):
            reason = reason.strip() or None
        else:
            reason = None

        if not safe:
            return PromptOptimizationProviderResult(
                safe=False,
                reason=reason or "This prompt was flagged as unsafe.",
                improved_prompt=None,
                changes=[],
            )

        improved = data.get("improvedPrompt") or data.get("improved_prompt")
        if not isinstance(improved, str) or not improved.strip():
            improved = original_prompt

        changes_raw = data.get("changes") or []
        changes: list[str] = []
        if isinstance(changes_raw, list):
            changes = [str(c).strip() for c in changes_raw if str(c).strip()]

        return PromptOptimizationProviderResult(
            safe=True,
            reason=None,
            improved_prompt=improved.strip(),
            changes=changes,
        )

    async def analyze_and_optimize(
        self,
        project_name: str,
        description: str,
        system_prompt: str,
    ) -> PromptOptimizationProviderResult:
        user_message = self._build_user_message(project_name, description, system_prompt)
        payload = self._build_payload(user_message)

        data = await self._post_with_retry(payload)
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No response from Groq API")

        content = choices[0].get("message", {}).get("content")
        if not content:
            raise ValueError("Empty response from Groq API")

        parsed = self._parse_json_content(content)
        return self._normalize_result(parsed, system_prompt)
