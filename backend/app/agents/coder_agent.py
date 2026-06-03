from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.config.prompts import CODER_FIX_PROMPT, CODER_SYSTEM_PROMPT
from app.core.code_executor import CodeExecutor
from app.models.task import ExecutionResult, SubTask, SubTaskResult
from app.utils.json_utils import parse_json_object, strip_code_fence


class CoderAgent(BaseAgent):
    """Generate, repair, and execute Python code for a subtask."""

    agent_name = "coder"

    def __init__(
        self,
        *,
        task_id: str,
        llm_client,
        model: str,
        executor: CodeExecutor,
        max_retry: int,
        timeout: int,
    ) -> None:
        super().__init__(task_id=task_id, llm_client=llm_client, model=model)
        self.executor = executor
        self.max_retry = max_retry
        self.timeout = timeout

    async def run(self, subtask: SubTask, context: str) -> SubTaskResult:
        """Generate and execute code for a subtask."""

        await self.publish(
            "agent_start",
            f"Generating code for subtask {subtask.index}: {subtask.title}",
            subtask_index=subtask.index,
        )
        code = await self._generate_code(subtask, context)

        execution = ExecutionResult(success=False)
        for attempt in range(1, self.max_retry + 1):
            execution = await self.executor.execute(code, timeout=self.timeout)
            await self.publish(
                "code_exec",
                "Code executed." if execution.success else "Code execution failed.",
                subtask_index=subtask.index,
                code=code,
                output=execution.stdout,
                stderr=execution.stderr,
                error=execution.error,
                outputs=[item.model_dump() for item in execution.outputs],
                attempt=attempt,
            )
            if execution.success:
                key_results = self._extract_key_results(execution.stdout)
                await self.publish(
                    "agent_end",
                    f"Subtask {subtask.index} code completed.",
                    subtask_index=subtask.index,
                    key_results=key_results,
                )
                return SubTaskResult(
                    subtask=subtask,
                    code=code,
                    execution=execution,
                    key_results=key_results,
                )

            if attempt < self.max_retry:
                code = await self._fix_code(code, execution.error or execution.stderr)

        await self.publish(
            "error",
            f"Subtask {subtask.index} failed after {self.max_retry} attempts.",
            subtask_index=subtask.index,
            error=execution.error,
        )
        return SubTaskResult(subtask=subtask, code=code, execution=execution)

    async def _generate_code(self, subtask: SubTask, context: str) -> str:
        user_prompt = (
            f"Subtask title: {subtask.title}\n"
            f"Subtask description: {subtask.description}\n"
            f"Expected output: {subtask.expected_output}\n"
            f"Available data files: {subtask.data_files}\n\n"
            f"Previous context:\n{context}\n"
        )
        raw = await self.stream_llm(
            [
                {"role": "system", "content": CODER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            metadata={"subtask_index": subtask.index},
        )
        return strip_code_fence(raw)

    async def _fix_code(self, code: str, error: str) -> str:
        raw = await self.stream_llm(
            [
                {"role": "system", "content": CODER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": CODER_FIX_PROMPT.format(error=error, code=code),
                },
            ],
            metadata={"repair": True},
        )
        return strip_code_fence(raw)

    @staticmethod
    def _extract_key_results(stdout: str) -> dict[str, Any]:
        for line in reversed([item.strip() for item in stdout.splitlines()]):
            if not line.startswith("{"):
                continue
            try:
                parsed = parse_json_object(line)
            except Exception:
                continue
            value = parsed.get("key_results")
            if isinstance(value, dict):
                return value
        return {}

