from __future__ import annotations

import json
import re
from typing import Any


def strip_code_fence(text: str) -> str:
    """Remove a markdown code fence if the model added one."""

    stripped = text.strip()
    fence_match = re.fullmatch(r"```(?:\w+)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return stripped


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse the first JSON object found in text."""

    stripped = strip_code_fence(text)
    try:
        value = json.loads(stripped)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM output.")

    value = json.loads(stripped[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Parsed JSON value is not an object.")
    return value

