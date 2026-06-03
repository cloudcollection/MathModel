from __future__ import annotations

import json

from app.agents.base_agent import BaseAgent
from app.config.prompts import ANALYST_SYSTEM_PROMPT
from app.models.task import SubTaskResult


class AnalystAgent(BaseAgent):
    """Interpret code outputs for the final paper."""

    agent_name = "analyst"

    async def run(self, result: SubTaskResult, context: str) -> str:
        """Produce a concise interpretation for one subtask result."""

        subtask = result.subtask
        await self.publish(
            "agent_start",
            f"Analyzing results for subtask {subtask.index}: {subtask.title}",
            subtask_index=subtask.index,
        )
        payload = {
            "subtask": subtask.model_dump(),
            "stdout": result.execution.stdout,
            "stderr": result.execution.stderr,
            "error": result.execution.error,
            "key_results": result.key_results,
            "context": context,
        }
        analysis = await self.stream_llm(
            [
                {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
            ],
            metadata={"subtask_index": subtask.index},
        )
        await self.publish(
            "agent_end",
            f"Analysis completed for subtask {subtask.index}.",
            subtask_index=subtask.index,
        )
        return analysis.strip()

