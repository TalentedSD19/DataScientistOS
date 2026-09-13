import json

from backend.llm import get_llm
from backend.mcp_client import call

SYSTEM = """You write complete, self-contained Python data science scripts.

Rules you must follow:
- Write ONE file that runs from top to bottom. `python src/main.py` must work.
- The working folder is /workspace. Input files are in input/.
- Save every requested output with the EXACT file name asked for. If the name has a
  folder in it, create the folder first with
  `os.makedirs(os.path.dirname(path) or ".", exist_ok=True)` — the `or "."` matters:
  a bare file name with no folder makes os.path.dirname(path) return '', and
  os.makedirs('', exist_ok=True) raises FileNotFoundError.
- For charts use matplotlib, never call plt.show(), always plt.savefig(...) then plt.close().
- Only use column names from the data profile you are given.
- Set random_state so results repeat.
- Print every metric you calculate, with a label.
- You may use: pandas, numpy, scipy, scikit-learn, statsmodels, matplotlib,
  seaborn, openpyxl, pillow, joblib, xgboost, lightgbm.
- There is no internet.
- Reply with Python code only. No explanation, no markdown fences.
"""

FIRST_DRAFT = """TASK SPECIFICATION:
{spec}

DATA PROFILE:
{profiles}

ORIGINAL REQUEST:
{prompt}

Write src/main.py."""

PATCH = """Your previous script did not pass the checks.

CURRENT CODE:
{code}

WHAT HAPPENED WHEN IT RAN:
exit code: {exit_code}
error output: {stderr}

PROBLEMS FOUND:
{issues}

WHAT TO DO:
{instruction}

Fix only what is broken. Keep everything that already worked.
Reply with the complete corrected src/main.py."""


def _strip_fences(text: str) -> str:
    """Remove ```python ... ``` if the model adds it anyway."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("python"):
            text = text[len("python"):]
    return text.strip()


async def code_node(state: dict) -> dict:
    task_id = state["task_id"]
    llm = get_llm("coder")

    # If there is already code AND a failed check, we patch instead of rewriting
    if state.get("code") and state.get("validation"):
        run = state.get("execution_result", {})
        message = PATCH.format(
            code=state["code"],
            exit_code=run.get("exit_code"),
            stderr=(run.get("stderr") or "")[-2000:],
            issues=json.dumps(state["validation"].get("issues", []), indent=2),
            instruction=state["validation"].get("repair_instruction", ""),
        )
        mode = "patch"
    else:
        message = FIRST_DRAFT.format(
            spec=json.dumps(state["spec"], indent=2),
            profiles=json.dumps(state.get("dataset_profiles", {}), indent=2)[:8000],
            prompt=state["user_prompt"],
        )
        mode = "first draft"

    response = await llm.ainvoke([("system", SYSTEM), ("user", message)])
    code = _strip_fences(response.content)

    # Save it into the workspace so the sandbox can run it
    await call("workspace", "write_file",
               task_id=task_id, path="src/main.py", content=code)

    return {"code": code, "status": "executing",
            "logs": [f"coder: {mode}, {len(code)} characters"]}