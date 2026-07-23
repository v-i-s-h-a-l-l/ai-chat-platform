import json
import logging
from collections.abc import AsyncGenerator

from app.config import settings
from app.services.llm_provider import LLMProvider
from app.utils.http_client import get_async_http_client

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    """LLMProvider implementation backed by the Groq chat-completions API."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        model: str | None,
        max_tokens: int | None,
        stream: bool,
    ) -> dict:
        payload: dict = {
            "model": model or settings.groq_model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        return payload

    def _headers(self) -> dict[str, str]:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not configured")
        return {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        }

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        payload = self._build_payload(messages, temperature, model, max_tokens, False)
        client = get_async_http_client()
        response = await client.post(self.BASE_URL, headers=self._headers(), json=payload)
        if response.status_code >= 400:
            raise ValueError(f"Groq API error ({response.status_code}): {response.text}")
        data = response.json()

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No response from Groq API")

        content = choices[0].get("message", {}).get("content")
        if not content:
            raise ValueError("Empty response from Groq API")

        return content

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        model: str | None = None,
    ) -> AsyncGenerator[str, None]:
        payload = self._build_payload(messages, temperature, model, None, True)
        client = get_async_http_client()

        async with client.stream(
            "POST",
            self.BASE_URL,
            headers=self._headers(),
            json=payload,
        ) as response:
            if response.status_code >= 400:
                body = await response.aread()
                raise ValueError(f"Groq API error ({response.status_code}): {body.decode()}")

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {}).get("content")
                if delta:
                    yield delta

    async def fast_complete(self, messages: list[dict[str, str]], *, max_tokens: int = 8) -> str:
        """Low-latency call for classification tasks (YES/NO)."""
        return await self.complete(
            messages,
            temperature=0.0,
            model=settings.groq_fast_model,
            max_tokens=max_tokens,
        )
