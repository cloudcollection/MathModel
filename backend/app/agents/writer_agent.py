from __future__ import annotations

import json
from pathlib import Path

from app.agents.base_agent import BaseAgent
from app.config.prompts import WRITER_SYSTEM_PROMPT
from app.models.task import PlannerOutput, SubTaskResult


class WriterAgent(BaseAgent):
    """Write the final modeling paper section by section."""

    agent_name = "writer"

    SECTION_ORDER = [
        ("abstract", "Abstract"),
        ("problem_restatement", "Problem Restatement"),
        ("assumptions", "Assumptions and Justifications"),
        ("model", "Mathematical Model"),
        ("solution", "Solution Process"),
        ("results", "Results and Analysis"),
        ("conclusion", "Conclusion and Discussion"),
    ]

    async def run(
        self,
        *,
        planner_output: PlannerOutput,
        subtask_results: list[SubTaskResult],
        template_sections: dict[str, str],
        output_dir: Path,
    ) -> str:
        """Generate a Markdown paper."""

        await self.publish("agent_start", "Writing the final paper.")
        context = self._build_context(planner_output, subtask_results)
        sections: list[str] = []

        for key, title in self.SECTION_ORDER:
            instruction = template_sections.get(key, "")
            user_prompt = (
                f"Write the '{title}' section of the paper.\n"
                f"Additional section instruction: {instruction}\n\n"
                f"Context:\n{context}"
            )
            content = await self.stream_llm(
                [
                    {"role": "system", "content": WRITER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                metadata={"section": key},
            )
            sections.append(f"## {title}\n\n{content.strip()}\n")

        paper = "# Math Modeling Solution Paper\n\n" + "\n".join(sections)
        output_dir.mkdir(parents=True, exist_ok=True)
        await self.publish(
            "agent_end",
            "Final paper written.",
            section_count=len(sections),
        )
        return paper

    @staticmethod
    def _build_context(
        planner_output: PlannerOutput,
        subtask_results: list[SubTaskResult],
    ) -> str:
        payload = {
            "planner_output": planner_output.model_dump(),
            "subtask_results": [
                {
                    "subtask": item.subtask.model_dump(),
                    "stdout": item.execution.stdout,
                    "stderr": item.execution.stderr,
                    "error": item.execution.error,
                    "key_results": item.key_results,
                    "analysis": item.analysis,
                }
                for item in subtask_results
            ],
        }
        return json.dumps(payload, ensure_ascii=True, indent=2)

