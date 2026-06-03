from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


AgentName = Literal["system", "planner", "coder", "analyst", "writer"]
MessageType = Literal[
    "agent_start",
    "agent_stream",
    "agent_end",
    "code_exec",
    "error",
    "task_complete",
    "heartbeat",
]


class WSMessage(BaseModel):
    """Message sent through the task event stream."""

    type: MessageType
    agent: AgentName
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

