from __future__ import annotations

import asyncio
import base64
import time
from pathlib import Path
from queue import Empty
from typing import Any

from app.models.task import CellOutput, ExecutionResult


class CodeExecutor:
    """Execute generated Python code in a per-task Jupyter kernel."""

    def __init__(self, workdir: Path) -> None:
        self.workdir = workdir
        self.kernel_manager: Any | None = None
        self.kernel_client: Any | None = None

    async def start_kernel(self) -> None:
        """Start an IPython kernel for this executor."""

        await asyncio.to_thread(self._start_kernel_sync)

    async def execute(self, code: str, timeout: int = 60) -> ExecutionResult:
        """Execute code and collect stdout, stderr, errors, and images."""

        if self.kernel_client is None:
            await self.start_kernel()
        return await asyncio.to_thread(self._execute_sync, code, timeout)

    async def shutdown(self) -> None:
        """Stop the Jupyter kernel."""

        await asyncio.to_thread(self._shutdown_sync)

    async def restart_kernel(self) -> None:
        """Restart the kernel after a serious execution failure."""

        await self.shutdown()
        await self.start_kernel()

    def _start_kernel_sync(self) -> None:
        self.workdir.mkdir(parents=True, exist_ok=True)
        try:
            from jupyter_client import KernelManager
        except Exception as exc:  # pragma: no cover - install-time concern
            raise RuntimeError("jupyter_client is required for code execution.") from exc

        self.kernel_manager = KernelManager(kernel_name="python3")
        self.kernel_manager.start_kernel(cwd=str(self.workdir))
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        self.kernel_client.wait_for_ready(timeout=15)

    def _execute_sync(self, code: str, timeout: int) -> ExecutionResult:
        if self.kernel_client is None:
            raise RuntimeError("Kernel has not been started.")

        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        outputs: list[CellOutput] = []
        error: str | None = None

        msg_id = self.kernel_client.execute(code)
        deadline = time.monotonic() + timeout

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                error = f"Execution timed out after {timeout} seconds."
                break

            try:
                msg = self.kernel_client.get_iopub_msg(timeout=max(0.1, remaining))
            except Empty:
                error = f"Execution timed out after {timeout} seconds."
                break

            if msg.get("parent_header", {}).get("msg_id") != msg_id:
                continue

            msg_type = msg.get("header", {}).get("msg_type")
            content = msg.get("content", {})

            if msg_type == "status" and content.get("execution_state") == "idle":
                break
            if msg_type == "stream":
                text = content.get("text", "")
                if content.get("name") == "stderr":
                    stderr_parts.append(text)
                else:
                    stdout_parts.append(text)
            elif msg_type in {"execute_result", "display_data"}:
                outputs.extend(self._extract_display_outputs(content.get("data", {})))
            elif msg_type == "error":
                traceback = "\n".join(content.get("traceback", []))
                error = traceback or content.get("ename") or "Execution error."
                outputs.append(
                    CellOutput(
                        type="error",
                        content=error,
                        mime_type="text/plain",
                    )
                )

        outputs.extend(self._collect_saved_images())
        return ExecutionResult(
            success=error is None,
            stdout="".join(stdout_parts),
            stderr="".join(stderr_parts),
            error=error,
            outputs=outputs,
        )

    def _extract_display_outputs(self, data: dict[str, Any]) -> list[CellOutput]:
        outputs: list[CellOutput] = []
        if "image/png" in data:
            outputs.append(
                CellOutput(
                    type="image",
                    content=data["image/png"],
                    mime_type="image/png",
                )
            )
        if "text/plain" in data:
            text = data["text/plain"]
            if isinstance(text, list):
                text = "\n".join(text)
            outputs.append(
                CellOutput(type="text", content=str(text), mime_type="text/plain")
            )
        return outputs

    def _collect_saved_images(self) -> list[CellOutput]:
        outputs: list[CellOutput] = []
        for image_path in sorted(self.workdir.glob("output_*.png")):
            try:
                encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            except OSError:
                continue
            outputs.append(
                CellOutput(
                    type="image",
                    content=encoded,
                    mime_type="image/png",
                )
            )
        return outputs

    def _shutdown_sync(self) -> None:
        if self.kernel_client is not None:
            self.kernel_client.stop_channels()
            self.kernel_client = None
        if self.kernel_manager is not None:
            self.kernel_manager.shutdown_kernel(now=True)
            self.kernel_manager = None

