# DataScientistOS

A multi-agent system that turns a natural-language data question plus a folder
of data files into working code and an answer. Point it at a `.csv`, a pile of
mixed CSV/JSON/text files, or anything in between, describe what you want
("clean this and plot revenue by month", "train a model to predict churn"),
and it plans, writes, runs, and debugs its own code in a sandboxed container
until an LLM judge is satisfied — then writes up what it found.

## Architecture

```mermaid
flowchart TD
    START(["Input files + query"]) --> Analyzer

    Analyzer["Analyzer<br/>describes every file"] --> Retriever
    Retriever["Retriever<br/>keeps top-K relevant files<br/>(only above 100 files)"] --> Planner
    Planner["Planner<br/>proposes one concrete next step"] --> Coder
    Coder["Coder<br/>writes the step into main.py"] --> Executor
    Executor["Executor<br/>runs main.py in the sandbox"] --> ExecOK{"exit code?"}

    ExecOK -- "0" --> Verifier
    ExecOK -- "crashed, retries left" --> Debugger["Debugger<br/>pip installs, or fixes the traceback"]
    ExecOK -- "crashed, retries exhausted" --> Reporter
    Debugger --> Executor

    Verifier["Verifier<br/>LLM judge: is this enough?"] --> VerOK{"sufficient?"}
    VerOK -- "yes" --> Reporter
    VerOK -- "no, steps left" --> Router["Router<br/>add a step, or backtrack"]
    VerOK -- "no, out of steps" --> Reporter
    Router --> Planner

    Reporter["Reporter<br/>writes report.md"] --> Done(["Done"])

    classDef agent fill:#e0ecff,stroke:#3b6fd6,color:#111
    classDef decision fill:#fff3cd,stroke:#c9962c,color:#111
    classDef term fill:#dff5e1,stroke:#3bb35a,color:#111
    class Analyzer,Retriever,Planner,Coder,Executor,Debugger,Verifier,Router,Reporter agent
    class ExecOK,VerOK decision
    class START,Done term
```

Solid arrows are the fixed pipeline; the two loops are the interesting part —
**Coder → Executor → Debugger → Executor** retries a crashing script (up to
`MAX_DEBUG_ATTEMPTS`), and **Verifier → Router → Planner** is the
plan-refinement loop, which either adds a step or backtracks to redo one that
turned out wrong (up to `MAX_STEPS` rounds total). However the run ends, the
Reporter always runs once at the end.

Each agent is a small, single-purpose LLM call under `backend/agents/`, wired
together as a LangGraph state machine in `backend/graph/graph.py`.

## Inspired by DS-STAR

The agent loop is based on **DS-STAR** (Nam et al., 2025 — Google Cloud &
KAIST, [arXiv:2509.21825](https://arxiv.org/abs/2509.21825)): analyze every
file up front, then loop through *plan → code → execute → verify*, letting an
LLM judge decide when the answer is actually done rather than just checking
whether the code ran, and letting a router either add the next step or
backtrack and redo one that turned out wrong. That loop is the heart of this
project too, but getting it from a paper to something you can actually run
against your own data meant building out a few things the paper doesn't
cover.

The biggest of those is where the code actually runs. The paper reasons about
scripts and execution results in the abstract; here, every script an agent
writes runs inside its own Docker container, spun up fresh per task with no
network access and CPU/memory limits by default, and torn down the moment the
task ends. The agents never touch the host, and the host never runs
LLM-generated code directly. The only way an agent reaches that sandbox is
through a small MCP tool server — `write_file`, `execute_file`, and
`execute_shell` are the entire surface area, and it's the same server every
agent talks to, which keeps the sandboxing logic in one place instead of
scattered across nine agents.

The other addition is the **Reporter**. The paper's loop is happy to stop at
working code and a short answer; this project always finishes with a
Reporter agent that writes a plain-language `report.md` — the answer, the
steps it took to get there, and the files it produced — or, if it ran out of
retries or steps, an honest explanation of what went wrong instead of just
failing silently.

All of that is wrapped in a FastAPI backend and a React frontend, so you can
run a task from a browser instead of a terminal: upload files, type a prompt,
and watch the pipeline above light up node by node as the agents work,
finishing with a downloadable report and any files the run produced.

## Running it

Requires Python 3.12, [uv](https://docs.astral.sh/uv/), and Docker Desktop.

```bash
uv sync
cp .env.example .env      # fill in OPENAI_API_KEY

docker build -t datasci-runtime:latest -f docker/Dockerfile.runtime docker

uv run python -m mcp_servers.server    # keep running in its own terminal
```

Then, from the command line:

```bash
uv run python scripts/run_task.py "train a model to predict Outcome" samples/data.csv
```

Or over HTTP, with the React UI:

```bash
uv run uvicorn backend.api.main:app --reload   # in one terminal

cd frontend && npm install && npm run dev      # in another
```

Each task gets its own folder under `storage/tasks/<task_id>/workspace/` and
its own Docker container, torn down as soon as the task finishes.

## Layout

```
backend/
  agents/        one file per DS-STAR agent
  graph/         the LangGraph state machine wiring the agents together
  api/           FastAPI wrapper
  config.py      every tunable in one place
  llm.py         picks which model backs each agent role
  docker_runner.py  starts/runs commands in each task's sandbox container
mcp_servers/
  server.py      the single MCP server: write_file, execute_file, execute_shell
docker/          the sandbox image code executes in
scripts/         CLI entry point + sample data generator
frontend/        the React UI: upload form, pipeline diagram, logs, report
```
