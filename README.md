# DataScientistOS

An implementation of **DS-STAR** (Nam et al., 2025) — a multi-agent system that
turns a natural-language data question plus a folder of data files into working
code and an answer. This follows DS-STAR's core architecture for well-defined
queries (not the DS-STAR+ extension for open-ended report writing).

## How it works

DS-STAR answers a query about a set of data files by looping through five
agents until an LLM judge decides the current plan and code are sufficient:

```
                 ┌─────────────┐
   input files → │  Analyzer   │  describes every file (schema, sample rows, ...)
                 └──────┬──────┘
                        ▼
                 ┌─────────────┐
                 │  Retriever  │  picks the most relevant files (only kicks in
                 └──────┬──────┘  above 100 input files; see backend/config.py)
                        │
          ┌─────────────▼─────────────┐
          │            Planner        │◄────────────┐
          │  proposes the next step   │              │
          └─────────────┬─────────────┘              │
                         ▼                            │
                 ┌─────────────┐   crash    ┌─────────────┐
                 │    Coder    │───────────►│  Debugger   │
                 │ writes code │            │  fixes it   │
                 └──────┬──────┘            └──────┬──────┘
                        ▼         ▲                 │
                 ┌─────────────┐  └─────────────────┘
                 │  Executor   │  runs the script in Docker
                 └──────┬──────┘
                        ▼ success
                 ┌─────────────┐  insufficient  ┌─────────────┐
                 │  Verifier   │───────────────►│   Router    │
                 │ judges plan │                │ add step or │
                 └──────┬──────┘                │  backtrack  │
                         │ sufficient            └──────┬──────┘
                         ▼                              │
                       done ◄────────────────────────────┘ (back to Planner)
```

Each agent is a small, single-purpose LLM call under `backend/agents/`, wired
together as a LangGraph state machine in `backend/graph/graph.py`. The full
state each agent reads and writes is defined in `backend/graph/state.py`.

- **Analyzer** — generates and runs a small Python script per file to produce
  a text description of its structure and content (works for structured and
  unstructured formats alike).
- **Retriever** — with many input files, embeds the query and each file
  description and keeps only the top-K most relevant ones.
- **Planner** — proposes one small, concrete next step toward answering the
  query, given the plan so far and the last execution output.
- **Coder** — implements the current plan as a single `src/main.py` script.
- **Executor** — runs that script inside the task's Docker sandbox.
- **Debugger** — if the script crashes, fixes it using the traceback (and the
  file descriptions, since a traceback alone often isn't enough context).
- **Verifier** — an LLM judge that decides whether the plan + code + output
  are actually sufficient to answer the query.
- **Router** — when the verifier says no, decides whether to add a new step
  or backtrack and redo a step that turned out to be wrong.

## Tools

Every tool an agent can call — writing a script into the workspace, and
running one — is served by a single MCP server: `mcp_servers/server.py`. All
agents reach it through `backend/mcp_client.py`.

All code the agents write is executed inside a per-task Docker container
(`backend/docker_runner.py`, image built from `docker/Dockerfile.runtime`),
with no network access by default and CPU/memory limits — the host never runs
LLM-generated code directly.

## Setup

Requires Python 3.12, [uv](https://docs.astral.sh/uv/), and Docker Desktop.

```bash
uv sync
cp .env.example .env   # then fill in your OPENAI_API_KEY
```

Build the sandbox image the executor runs code in:

```bash
docker build -t datasci-runtime:latest -f docker/Dockerfile.runtime docker
```

Start the MCP tool server (keep this running in its own terminal):

```bash
uv run python -m mcp_servers.server
```

## Running a task

From the command line, everything is printed live as the agent works:

```bash
uv run python scripts/run_task.py "train a model to predict Outcome" samples/data.csv
```

Or over HTTP, via the FastAPI wrapper:

```bash
uv run uvicorn backend.api.main:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -F "prompt=train a model to predict Outcome" \
  -F "files=@samples/data.csv"
# then: GET /tasks/{task_id}, /tasks/{task_id}/logs, /tasks/{task_id}/result
```

Each task gets its own folder under `storage/tasks/<task_id>/workspace/`
(`input/` for uploaded files, `src/main.py` for the current solution, plus
whatever the code itself produces) and its own long-lived Docker container.

## Layout

```
backend/
  agents/        one file per DS-STAR agent
  graph/         the LangGraph state machine wiring the agents together
  api/           FastAPI wrapper (optional HTTP interface)
  config.py      every tunable in one place (model names, limits, ports)
  llm.py         picks which model backs each agent role
  schemas.py     structured-output types for the planner/verifier/router
  mcp_client.py  talks to the MCP tool server
  docker_runner.py  starts/runs commands in each task's sandbox container
  workspace.py   creates a task's folder layout, copies input files in
  runner.py      runs the graph end to end, printing every step
mcp_servers/
  server.py      the single MCP server: write_file, execute_file
docker/
  Dockerfile.runtime        the sandbox image code executes in
  requirements-runtime.txt  its Python packages
scripts/
  run_task.py    CLI entry point
  make_sample.py regenerates samples/data.csv
```
