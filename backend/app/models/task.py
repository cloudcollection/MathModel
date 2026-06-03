from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.message import WSMessage


class TaskStatus(str, Enum):
    """Lifecycle states for a modeling task."""

    pending = "pending"
    running = "running"
    complete = "complete"
    error = "error"


class UploadedFileInfo(BaseModel):
    """Saved upload metadata."""

    filename: str
    path: str
    size: int


class SubTask(BaseModel):
    """A modeling subtask produced by the planner."""

    index: int
    title: str
    description: str
    expected_output: str
    data_files: list[str] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    """Structured output from the planner agent."""

    problem_summary: str
    assumptions: list[str] = Field(default_factory=list)
    subtasks: list[SubTask] = Field(default_factory=list)
    suggested_models: list[str] = Field(default_factory=list)


class CellOutput(BaseModel):
    """A single Jupyter cell output item."""

    type: Literal["text", "image", "error"]
    content: str
    mime_type: str


class ExecutionResult(BaseModel):
    """Structured result from executing generated code."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    outputs: list[CellOutput] = Field(default_factory=list)


class SubTaskResult(BaseModel):
    """Final result for one planned subtask."""

    subtask: SubTask
    code: str
    execution: ExecutionResult
    key_results: dict[str, Any] = Field(default_factory=dict)
    analysis: str = ""


class TaskRecord(BaseModel):
    """Stored state for a task."""

    id: str
    status: TaskStatus = TaskStatus.pending
    problem_text: str
    model: str | None = None
    attachments: list[UploadedFileInfo] = Field(default_factory=list)
    planner_output: PlannerOutput | None = None
    subtask_results: list[SubTaskResult] = Field(default_factory=list)
    paper_markdown: str = ""
    result_md_path: str | None = None
    result_docx_path: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)


class TaskCreateResponse(BaseModel):
    """Response returned after creating a task."""

    task_id: str
    status: TaskStatus


class TaskSnapshot(BaseModel):
    """Task state returned by the status endpoint."""

    task: TaskRecord
    messages: list[WSMessage] = Field(default_factory=list)

