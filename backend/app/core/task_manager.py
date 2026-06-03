from __future__ import annotations

import asyncio
import traceback
import uuid
from pathlib import Path

from app.agents.analyst_agent import AnalystAgent
from app.agents.coder_agent import CoderAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.writer_agent import WriterAgent
from app.config.settings import BACKEND_DIR, Settings, get_settings
from app.core.code_executor import CodeExecutor
from app.core.event_bus import event_bus, publish_event
from app.core.llm_client import LLMClient
from app.models.message import WSMessage
from app.models.task import (
    PlannerOutput,
    SubTaskResult,
    TaskRecord,
    TaskSnapshot,
    TaskStatus,
    UploadedFileInfo,
)
from app.utils.paper_builder import write_paper_files


class TaskManager:
    """Create, store, and run modeling tasks."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = asyncio.Lock()

    async def create_task(
        self,
        *,
        problem_text: str,
        attachments: list[UploadedFileInfo],
        model: str | None,
    ) -> TaskRecord:
        """Create a task record."""

        task_id = uuid.uuid4().hex
        record = TaskRecord(
            id=task_id,
            problem_text=problem_text,
            model=model,
            attachments=attachments,
        )
        async with self._lock:
            self._tasks[task_id] = record
        return record

    async def get_record(self, task_id: str) -> TaskRecord | None:
        """Return a task record if it exists."""

        async with self._lock:
            return self._tasks.get(task_id)

    async def snapshot(self, task_id: str) -> TaskSnapshot | None:
        """Return task state plus event history."""

        record = await self.get_record(task_id)
        if record is None:
            return None
        return TaskSnapshot(task=record, messages=await event_bus.get_history(task_id))

    async def run_task(self, task_id: str) -> None:
        """Run the complete agent pipeline for one task."""

        record = await self.get_record(task_id)
        if record is None:
            return

        output_dir = self.settings.output_path / task_id
        executor = CodeExecutor(workdir=output_dir)
        llm_client = LLMClient(self.settings)

        try:
            await self._set_status(task_id, TaskStatus.running)
            await publish_event(
                task_id,
                WSMessage(
                    type="agent_start",
                    agent="system",
                    content="Task started.",
                    metadata={"task_id": task_id},
                ),
            )

            await executor.start_kernel()
            planner_output = await self._run_planner(record, llm_client)
            await self._update_record(task_id, planner_output=planner_output)

            context = self._build_context(record.problem_text, planner_output, [])
            subtask_results: list[SubTaskResult] = []
            for subtask in planner_output.subtasks:
                coder = CoderAgent(
                    task_id=task_id,
                    llm_client=llm_client,
                    model=self._model_for(record, "coder"),
                    executor=executor,
                    max_retry=self.settings.max_retry,
                    timeout=self.settings.jupyter_timeout,
                )
                result = await coder.run(subtask, context)

                analyst = AnalystAgent(
                    task_id=task_id,
                    llm_client=llm_client,
                    model=self._model_for(record, "analyst"),
                )
                result.analysis = await analyst.run(result, context)
                subtask_results.append(result)
                await self._update_record(task_id, subtask_results=subtask_results)
                context = self._build_context(
                    record.problem_text, planner_output, subtask_results
                )

            writer = WriterAgent(
                task_id=task_id,
                llm_client=llm_client,
                model=self._model_for(record, "writer"),
            )
            paper = await writer.run(
                planner_output=planner_output,
                subtask_results=subtask_results,
                template_sections=self._load_template_sections(),
                output_dir=output_dir,
            )
            md_path, docx_path = write_paper_files(paper, output_dir)
            await self._update_record(
                task_id,
                paper_markdown=paper,
                result_md_path=str(md_path),
                result_docx_path=str(docx_path) if docx_path else None,
                status=TaskStatus.complete,
            )
            await publish_event(
                task_id,
                WSMessage(
                    type="task_complete",
                    agent="system",
                    content="Task complete.",
                    metadata={
                        "paper_markdown": paper,
                        "download_url": f"/api/task/{task_id}/download",
                    },
                ),
            )
        except Exception as exc:
            error_text = "".join(
                traceback.format_exception_only(type(exc), exc)
            ).strip()
            await self._update_record(
                task_id,
                status=TaskStatus.error,
                error=error_text,
            )
            await publish_event(
                task_id,
                WSMessage(
                    type="error",
                    agent="system",
                    content=error_text,
                    metadata={"traceback": traceback.format_exc()},
                ),
            )
        finally:
            await executor.shutdown()

    async def _run_planner(
        self,
        record: TaskRecord,
        llm_client: LLMClient,
    ) -> PlannerOutput:
        planner = PlannerAgent(
            task_id=record.id,
            llm_client=llm_client,
            model=self._model_for(record, "planner"),
        )
        return await planner.run(
            record.problem_text,
            [item.filename for item in record.attachments],
        )

    async def _set_status(self, task_id: str, status: TaskStatus) -> None:
        await self._update_record(task_id, status=status)

    async def _update_record(self, task_id: str, **updates: object) -> None:
        async with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                return
            for key, value in updates.items():
                setattr(record, key, value)
            record.touch()

    def _model_for(self, record: TaskRecord, agent: str) -> str:
        return record.model or self.settings.model_for(agent)

    @staticmethod
    def _build_context(
        problem_text: str,
        planner_output: PlannerOutput,
        subtask_results: list[SubTaskResult],
    ) -> str:
        result_summaries = [
            {
                "index": item.subtask.index,
                "title": item.subtask.title,
                "key_results": item.key_results,
                "analysis": item.analysis,
            }
            for item in subtask_results
        ]
        return (
            f"Problem:\n{problem_text}\n\n"
            f"Problem summary:\n{planner_output.problem_summary}\n\n"
            f"Assumptions:\n{planner_output.assumptions}\n\n"
            f"Completed subtask results:\n{result_summaries}"
        )

    @staticmethod
    def _load_template_sections() -> dict[str, str]:
        try:
            import tomllib
        except ModuleNotFoundError:  # pragma: no cover - py310 fallback
            return {}

        template_path = BACKEND_DIR / "app" / "config" / "md_template.toml"
        if not template_path.exists():
            return {}
        data = tomllib.loads(template_path.read_text(encoding="utf-8"))
        sections = data.get("sections", {})
        return {str(key): str(value) for key, value in sections.items()}


task_manager = TaskManager()

