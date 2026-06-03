from __future__ import annotations

import re
from pathlib import Path

from fastapi import UploadFile

from app.models.task import UploadedFileInfo


def safe_filename(filename: str) -> str:
    """Return a filesystem-safe upload name."""

    name = Path(filename).name.strip() or "upload.dat"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


async def save_uploads(
    *,
    task_id: str,
    files: list[UploadFile] | None,
    upload_root: Path,
) -> list[UploadedFileInfo]:
    """Persist uploaded files and return metadata."""

    if not files:
        return []

    task_dir = upload_root / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    saved: list[UploadedFileInfo] = []
    for upload in files:
        if not upload.filename:
            continue
        filename = safe_filename(upload.filename)
        path = task_dir / filename
        content = await upload.read()
        path.write_bytes(content)
        saved.append(
            UploadedFileInfo(
                filename=filename,
                path=str(path),
                size=len(content),
            )
        )
    return saved

