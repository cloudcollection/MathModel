from __future__ import annotations

from app.core.event_bus import publish_event
from app.core.llm_client import LLMClient, Message
from app.models.message import AgentName, WSMessage


class BaseAgent:
    """Common streaming and event helpers for all agents."""

    agent_name: AgentName

    def __init__(
        self,
        *,
        task_id: str,
        llm_client: LLMClient,
        model: str,
    ) -> None:
        self.task_id = task_id
        self.llm_client = llm_client
        self.model = model

    async def publish(self, type_: str, content: str, **metadata: object) -> None:
        await publish_event(
            self.task_id,
            WSMessage(
                type=type_,  # type: ignore[arg-type]
                agent=self.agent_name,
                content=content,
                metadata=metadata,
            ),
        )

    async def stream_llm(
        self,
        messages: list[Message],
        *,
        metadata: dict[str, object] | None = None,
        temperature: float | None = None,
    ) -> str:
        """Stream a model response to WebSocket and return the full text."""

        metadata = metadata or {}
        parts: list[str] = []
        async for chunk in self.llm_client.stream_chat(
            messages,
            model=self.model,
            temperature=temperature,
        ):
            parts.append(chunk)
            await publish_event(
                self.task_id,
                WSMessage(
                    type="agent_stream",
                    agent=self.agent_name,
                    content=chunk,
                    metadata=metadata,
                ),
            )
        return "".join(parts)

