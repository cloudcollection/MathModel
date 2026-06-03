# Project Overview

## Summary

`MathModel` is a full-stack agent system for math modeling contests.

## Core Flow

1. Submit a problem statement and optional files.
2. Planner splits the problem into subtasks and assumptions.
3. Coder writes and executes Python for each subtask.
4. Analyst explains the computed results.
5. Writer assembles the final paper in Markdown.

## Included Stack

- `FastAPI`
- `WebSocket`
- `Redis` fallback event history
- `LiteLLM`
- `Jupyter kernel` execution
- `Vue 3 + TypeScript + Tailwind`

## Generated Artifacts

- `backend/outputs/<task_id>/result.md`
- `backend/outputs/<task_id>/result.docx`

## Development Notes

- Set `MOCK_LLM=true` for a local demo without provider keys.
- All prompts live in `backend/app/config/prompts.py`.
- Paper section templates live in `backend/app/config/md_template.toml`.
