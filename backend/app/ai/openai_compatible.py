"""OpenAI-compatible AI provider.

Works with OpenAI, Ollama (/v1), LM Studio, Groq, and any endpoint speaking the
OpenAI Chat Completions API. Uses the official `openai` async SDK with a
configurable base_url.
"""
from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.ai.provider_base import AIProvider, ConnectionTestResult, ProviderConfig
from app.core.exceptions import AIProviderError


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        # A dummy key is acceptable for local providers (Ollama/LM Studio) which
        # ignore auth, but the SDK requires a non-empty string.
        self._client = AsyncOpenAI(
            base_url=config.endpoint_url or "https://api.openai.com/v1",
            api_key=config.api_key or "not-needed",
        )

    async def complete_json(self, system: str, user: str) -> dict:
        try:
            resp = await self._client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                max_tokens=self.config.max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # noqa: BLE001 - surface a clean domain error
            # Fall back to a non-json-mode call for providers lacking response_format.
            try:
                resp = await self._client.chat.completions.create(
                    model=self.config.model_name,
                    messages=[
                        {"role": "system", "content": system + "\nRespond with ONLY valid JSON."},
                        {"role": "user", "content": user},
                    ],
                    temperature=0.2,
                    max_tokens=self.config.max_tokens,
                )
            except Exception as exc2:  # noqa: BLE001
                raise AIProviderError(f"AI provider request failed: {exc2}") from exc

        content = resp.choices[0].message.content or "{}"
        return _safe_json(content)

    async def stream_text(self, system: str, user: str) -> AsyncIterator[str]:
        try:
            stream = await self._client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise AIProviderError(f"AI provider streaming request failed: {exc}") from exc

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    async def test_connection(self) -> ConnectionTestResult:
        start = time.perf_counter()
        try:
            resp = await self._client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": "Reply with the single word: OK"}],
                max_tokens=8,
                temperature=0,
            )
            latency = (time.perf_counter() - start) * 1000
            text = (resp.choices[0].message.content or "").strip()
            return ConnectionTestResult(
                ok=True,
                latency_ms=round(latency, 1),
                detail=f"Connected. Model replied: {text[:60]!r}",
                model=self.config.model_name,
            )
        except Exception as exc:  # noqa: BLE001
            return ConnectionTestResult(ok=False, detail=str(exc), model=self.config.model_name)


def _safe_json(content: str) -> dict:
    content = content.strip()
    # Strip markdown code fences if present.
    if content.startswith("```"):
        content = content.split("```", 2)[1] if "```" in content else content
        if content.startswith("json"):
            content = content[4:]
        content = content.strip("`").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Attempt to extract the first {...} block.
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                pass
        return {}
