import asyncio
import json
import uuid

from backend.llm import get_llm
from backend.mcp_client import call
from backend.config import MAX_DEBUG_ATTEMPTS
from backend.agents.debugger import fix_code, install_missing_package

PROMPT = """You are an expert data analyst and Python programmer.

Generate a **single, self-contained Python program** that loads and analyzes the file `{filename}` and prints a concise but comprehensive description of its contents.

### Requirements

1. **File handling**

   * `{filename}` may contain either **structured data** (CSV, Excel, JSON, Parquet, etc.) or **unstructured data** (TXT, Markdown, PDF, logs, etc.).
   * Detect the file type from its extension and use an appropriate Python library to read it.
   * The program must work directly with the provided `{filename}` without requiring any manual modification.
   * Do not create dummy data, placeholder content, or mock files.

2. **For structured data**
   Print the essential information needed to understand the dataset, including:

   * File name and file type
   * Number of rows and columns
   * **All column names**
   * Data types of all columns
   * A small sample of records (e.g., first 5 rows)
   * Basic dataset statistics where appropriate
   * Missing-value counts for each column
   * Number of unique values for each column
   * Any other important structural information that can be obtained efficiently

   If the dataset is very large, **do not print the entire dataset**. Print only representative examples and summaries.

3. **For unstructured data**
   Print the essential information needed to understand the file, including:

   * File name and file type
   * File size where available
   * Number of characters/words/lines where applicable
   * A representative excerpt from the content
   * For multi-page documents such as PDFs, include page count and a short excerpt from the beginning rather than dumping the entire document.
   * Preserve enough information from the excerpt to understand the nature and structure of the content.

4. **Output**

   * Print all important findings clearly using labeled sections.
   * The program must **print the contents or representative sample of `{filename}`**, not merely metadata about the file.
   * Avoid excessive output for large files.
   * Do not truncate important metadata such as column names.

5. **Code requirements**

   * Return **only one Python code block** containing the complete program.
   * The code must be **self-contained and executable as-is**.
   * Do not use `try`/`except` blocks to suppress, catch, or hide errors. If something fails, allow the error to be raised normally so it can be debugged.
   * Do not use dummy data or assume a particular dataset schema.
   * Keep the implementation robust and general-purpose.
   * Use standard Python libraries and commonly available data-processing libraries where appropriate.
   * Do not require command-line arguments unless necessary; use `{filename}` directly in the program.
"""


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
        await call("write_file", task_id=task_id, path=script_path, content=code)
        raw = await call("execute_file", task_id=task_id, path=script_path)
        result = json.loads(raw) if isinstance(raw, str) else raw

        if result.get("exit_code") == 0:
            return result.get("stdout", "")
        if attempt == MAX_DEBUG_ATTEMPTS:
            return f"(could not describe this file: {(result.get('stderr') or '')[-500:]})"

        traceback = result.get("stderr") or ""
        if not await install_missing_package(task_id, traceback):
            code = await fix_code(code, traceback)


async def analyzer_node(state: dict) -> dict:
    task_id = state["task_id"]
    files = state.get("input_files", [])

    descriptions_list = await asyncio.gather(
        *(_describe_one_file(task_id, f) for f in files)
    )
    descriptions = dict(zip(files, descriptions_list))

    return {
        "data_descriptions": descriptions,
        "logs": [f"analyzer: described {len(descriptions)} file(s) - {', '.join(files)}"],
    }
