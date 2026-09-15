import asyncio
import json
import uuid

from backend.llm import get_llm
from backend.mcp_client import call
from backend.config import MAX_DEBUG_ATTEMPTS
from backend.agents.debugger import fix_code

PROMPT = """You are an expert data analyst.
Generate a Python code that loads and describes the content of {filename}.

# Requirement
- The file can be either unstructured or structured data.
- If there is too much structured data, print out just a few examples.
- Print out essential information. For example, print out all the column names.
- The Python code should print out the content of {filename}.
- The code should be a single-file Python program that is self-contained and can be
  executed as-is.
- Reply with a single Python code block only.
- Do not include dummy contents since we will debug if an error occurs.
- Do not use try: and except: to hide errors. Debugging happens separately."""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("python"):
            text = text[len("python"):]
    return text.strip()


async def _describe_one_file(task_id: str, file_name: str) -> str:
    """d_i = exec(s_desc), s_desc = A_analyzer(D_i) -- with the Eq. 8 debug loop
    for when the generated description script itself fails to run."""
    llm = get_llm("analyzer")
    script_path = f"src/_describe_{uuid.uuid4().hex[:6]}.py"

    response = await llm.ainvoke(PROMPT.format(filename=f"input/{file_name}"))
    code = _strip_fences(response.content)

    for attempt in range(MAX_DEBUG_ATTEMPTS + 1):
        await call("workspace", "write_file", task_id=task_id, path=script_path, content=code)
        raw = await call("execution", "execute_file", task_id=task_id, path=script_path)
        result = json.loads(raw) if isinstance(raw, str) else raw

        if result.get("exit_code") == 0:
            return result.get("stdout", "")
        if attempt == MAX_DEBUG_ATTEMPTS:
            return f"(could not describe this file: {(result.get('stderr') or '')[-500:]})"

        code = await fix_code(code, result.get("stderr") or "")


async def analyzer_node(state: dict) -> dict:
    task_id = state["task_id"]
    files = state.get("input_files", [])

    descriptions_list = await asyncio.gather(
        *(_describe_one_file(task_id, f) for f in files)
    )
    descriptions = dict(zip(files, descriptions_list))

    return {
        "data_descriptions": descriptions,
        "logs": [f"analyzer: described {len(descriptions)} file(s)"],
    }
