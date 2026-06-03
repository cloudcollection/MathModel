from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.responses import FileResponse, PlainTextResponse
from starlette.websockets import WebSocketDisconnect

from app.config.settings import get_settings
from app.core.event_bus import event_bus, publish_event
from app.core.task_manager import task_manager
from app.models.message import WSMessage
from app.models.task import TaskCreateResponse
from app.utils.file_handler import save_uploads

api_router = APIRouter()
ws_router = APIRouter()


@api_router.post("/task", response_model=TaskCreateResponse)
async def create_task(
    problem_text: Annotated[str, Form()],
    model: Annotated[str | None, Form()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> TaskCreateResponse:
    """Create a task and start the agent pipeline."""

    if not problem_text.strip():
        raise HTTPException(status_code=400, detail="problem_text is required")

    settings = get_settings()
    record = await task_manager.create_task(
        problem_text=problem_text.strip(),
        attachments=[],
        model=model,
    )
    attachments = await save_uploads(
        task_id=record.id,
        files=files,
        upload_root=settings.upload_path,
    )
    await task_manager._update_record(record.id, attachments=attachments)
    asyncio.create_task(task_manager.run_task(record.id))
    return TaskCreateResponse(task_id=record.id, status=record.status)


@api_router.get("/task/{task_id}")
async def get_task(task_id: str):
    """Return task status and accumulated messages."""

    snapshot = await task_manager.snapshot(task_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="task not found")
    return snapshot


@api_router.get("/task/{task_id}/paper", response_class=PlainTextResponse)
async def get_paper(task_id: str) -> str:
    """Return the generated Markdown paper."""

    record = await task_manager.get_record(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="task not found")
    if not record.paper_markdown:
        raise HTTPException(status_code=404, detail="paper not ready")
    return record.paper_markdown


@api_router.get("/task/{task_id}/download")
async def download_paper(task_id: str) -> FileResponse:
    """Download result.docx when available, otherwise result.md."""

    record = await task_manager.get_record(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="task not found")

    candidates = [record.result_docx_path, record.result_md_path]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return FileResponse(
                candidate,
                filename=Path(candidate).name,
                media_type="application/octet-stream",
            )
    raise HTTPException(status_code=404, detail="paper not ready")


@ws_router.websocket("/ws/task/{task_id}")
async def websocket_task_events(websocket: WebSocket, task_id: str) -> None:
    """Stream live task events, including catch-up history."""

    await websocket.accept()
    snapshot = await task_manager.snapshot(task_id)
    if snapshot is None:
        await websocket.send_json(
            WSMessage(
                type="error",
                agent="system",
                content="task not found",
            ).model_dump(mode="json")
        )
        await websocket.close(code=1008)
        return

    for message in snapshot.messages:
        await websocket.send_json(message.model_dump(mode="json"))

    async def forward_events() -> None:
        async for message in event_bus.subscribe(task_id):
            await websocket.send_json(message.model_dump(mode="json"))

    async def heartbeat() -> None:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json(
                WSMessage(
                    type="heartbeat",
                    agent="system",
                    content="ping",
                ).model_dump(mode="json")
            )

    tasks = [
        asyncio.create_task(forward_events()),
        asyncio.create_task(heartbeat()),
    ]
    try:
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_EXCEPTION,
        )
        for task in done:
            task.result()
    except WebSocketDisconnect:
        pass
    finally:
        for task in tasks:
            task.cancel()

