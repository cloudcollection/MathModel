from __future__ import annotations

from pydantic import ValidationError

from app.agents.base_agent import BaseAgent
from app.config.prompts import PLANNER_SYSTEM_PROMPT
from app.models.task import PlannerOutput
from app.utils.json_utils import parse_json_object


class PlannerAgent(BaseAgent):
    """Analyze the problem and produce a structured modeling plan."""

    agent_name = "planner"

    async def run(self, problem_text: str, attachments: list[str]) -> PlannerOutput:
        """Run the planner and parse its JSON output."""

        await self.publish("agent_start", "Planning the modeling workflow.")
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Problem:\n"
                    f"{problem_text}\n\n"
                    f"Available attachments: {attachments}\n"
                    "Return valid JSON only."
                ),
            },
        ]

        last_error: Exception | None = None
        for attempt in range(2):
            raw = await self.stream_llm(messages, metadata={"attempt": attempt + 1})
            try:
                output = PlannerOutput.model_validate(parse_json_object(raw))
                if not output.subtasks:
                    raise ValueError("Planner returned no subtasks.")
                await self.publish(
                    "agent_end",
                    "Plan created.",
                    subtask_count=len(output.subtasks),
                )
                return output
            except (ValidationError, ValueError) as exc:
                last_error = exc
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The previous response was not valid for the schema. "
                            "Return only one valid JSON object with non-empty subtasks."
                        ),
                    }
                )

        await self.publish("error", f"Planner failed: {last_error}")
        raise RuntimeError(f"Planner failed to produce valid JSON: {last_error}")

