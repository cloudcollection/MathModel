from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from app.config.settings import Settings, get_settings


Message = dict[str, str]


class LLMClient:
    """Small async wrapper around LiteLLM with a deterministic mock mode."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def stream_chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Yield text chunks from an LLM chat completion."""

        if self.settings.mock_llm:
            async for chunk in self._stream_mock(messages):
                yield chunk
            return

        try:
            from litellm import acompletion
            from litellm.exceptions import RateLimitError
        except Exception as exc:  # pragma: no cover - install-time concern
            raise RuntimeError("litellm is required unless MOCK_LLM=true.") from exc

        last_error: Exception | None = None
        retry_count = max(1, self.settings.max_retry)
        for attempt in range(retry_count):
            try:
                stream = await acompletion(
                    model=model or self.settings.default_model,
                    messages=messages,
                    temperature=(
                        self.settings.llm_temperature
                        if temperature is None
                        else temperature
                    ),
                    stream=True,
                )
                async for chunk in stream:
                    content = self._extract_delta(chunk)
                    if content:
                        yield content
                return
            except RateLimitError as exc:  # pragma: no cover - provider-specific
                last_error = exc
                if attempt + 1 >= retry_count:
                    break
                await asyncio.sleep(10)
            except Exception as exc:
                last_error = exc
                if attempt + 1 >= retry_count:
                    break
                await asyncio.sleep(2**attempt)

        raise RuntimeError(f"LLM call failed after {retry_count} attempts: {last_error}")

    async def complete_chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """Return a complete response by accumulating streamed chunks."""

        parts: list[str] = []
        async for chunk in self.stream_chat(
            messages, model=model, temperature=temperature
        ):
            parts.append(chunk)
        return "".join(parts)

    @staticmethod
    def _extract_delta(chunk: Any) -> str:
        choice = chunk.choices[0]
        delta = getattr(choice, "delta", None)
        if isinstance(delta, dict):
            return delta.get("content") or ""
        return getattr(delta, "content", "") or ""

    async def _stream_mock(self, messages: list[Message]) -> AsyncIterator[str]:
        text = self._mock_response(messages)
        for index in range(0, len(text), 32):
            await asyncio.sleep(0.01)
            yield text[index : index + 32]

    def _mock_response(self, messages: list[Message]) -> str:
        system = "\n".join(item["content"] for item in messages if item["role"] == "system")
        user = "\n".join(item["content"] for item in messages if item["role"] == "user")

        if "Output ONLY valid JSON" in system:
            return json.dumps(
                {
                    "problem_summary": "A contest problem is decomposed into data preparation, model construction, computation, and interpretation.",
                    "assumptions": [
                        "Input data are representative of the studied system.",
                        "The objective can be approximated with measurable indicators.",
                        "Unobserved noise is bounded and does not change the main trend.",
                    ],
                    "subtasks": [
                        {
                            "index": 1,
                            "title": "Baseline analysis",
                            "description": "Build a baseline quantitative description and compute summary indicators.",
                            "expected_output": "A reproducible Python calculation with key summary values.",
                            "data_files": [],
                        },
                        {
                            "index": 2,
                            "title": "Sensitivity analysis",
                            "description": "Evaluate how the main conclusion changes under perturbed parameters.",
                            "expected_output": "Sensitivity indicators and a short interpretation.",
                            "data_files": [],
                        },
                    ],
                    "suggested_models": [
                        "Descriptive statistics",
                        "Scenario simulation",
                        "Sensitivity analysis",
                    ],
                }
            )

        if "Python data scientist" in system or "corrected code" in user:
            return """import json
import math
import statistics

# === Baseline Data ===
values = [12.5, 14.2, 13.9, 15.1, 14.8, 16.0, 15.4]

# === Indicator Calculation ===
mean_value = statistics.mean(values)
stdev_value = statistics.pstdev(values)
coefficient_of_variation = stdev_value / mean_value

print(f"mean_value: {mean_value:.4f}")
print(f"stdev_value: {stdev_value:.4f}")
print(f"coefficient_of_variation: {coefficient_of_variation:.4f}")
print(json.dumps({"key_results": {
    "mean_value": round(mean_value, 4),
    "stdev_value": round(stdev_value, 4),
    "coefficient_of_variation": round(coefficient_of_variation, 4)
}}))
"""

        if "mathematical modeling analyst" in system:
            return (
                "The computation gives a stable baseline indicator. "
                "The coefficient of variation is small enough to support the use "
                "of an aggregate trend model, while remaining uncertainty should be "
                "addressed through sensitivity analysis."
            )

        if "academic writer" in system:
            section = "Paper Section"
            marker = "Write the '"
            if marker in user:
                section = user.split(marker, 1)[1].split("'", 1)[0]
            return (
                f"This {section} section summarizes the modeling logic and computed "
                "evidence. The problem is represented through measurable indicators, "
                "then evaluated with a reproducible computational workflow. The "
                "numerical results show a consistent central tendency and limited "
                "dispersion, which supports the proposed baseline model. Remaining "
                "uncertainty is discussed through sensitivity considerations, and the "
                "final conclusions are tied directly to the assumptions and outputs."
            )

        return "Mock response."

