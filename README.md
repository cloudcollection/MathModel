# Math Modeling Agent

This repository is a compact, runnable implementation of a math modeling competition agent inspired by [jihe520/MathModelAgent](https://github.com/jihe520/MathModelAgent).

The app accepts a contest problem statement and optional data files, decomposes the problem into subtasks, generates and executes Python code in a Jupyter kernel, interprets the results, and writes a Markdown/docx paper.

## Architecture

- Backend: FastAPI, WebSocket task events, optional Redis event history, LiteLLM, Jupyter kernel execution.
- Agents: Planner, Coder, Analyst, Writer. The orchestration is plain async Python, not LangChain or LangGraph.
- Frontend: Vue 3, TypeScript, Pinia, Tailwind CSS, live agent feed, code/output tabs, Markdown plus KaTeX paper preview.
- Output: `backend/outputs/<task_id>/result.md` and `result.docx` when `python-docx` is installed.

## Quick Start

1. Copy the backend environment file:

```bash
cp backend/.env.example backend/.env
```

2. For a provider-backed run, set API keys and model names in `backend/.env`. For a local smoke test, keep:

```bash
MOCK_LLM=true
```

3. Start everything:

```bash
docker compose up --build
```

4. Open:

```text
http://localhost:5173
```

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## API

- `POST /api/task`: form fields `problem_text`, optional `model`, optional repeated `files`.
- `GET /api/task/{task_id}`: task state and event history.
- `GET /api/task/{task_id}/paper`: generated Markdown.
- `GET /api/task/{task_id}/download`: generated docx or Markdown.
- `WS /ws/task/{task_id}`: real-time task events.

## Notes

- Redis is optional at runtime. If `REDIS_URL` is unset or unavailable, the server uses in-memory event history and live queues.
- Each task receives its own Jupyter kernel and output directory.
- Prompts are centralized in `backend/app/config/prompts.py`.
- Paper section instructions are editable in `backend/app/config/md_template.toml`.

