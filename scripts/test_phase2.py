import asyncio, json

from backend.workspace import create_workspace, add_input_file
from backend.docker_runner import get_or_create, destroy
from backend.mcp_client import call


async def main():
    create_workspace("t2")
    add_input_file("t2", "samples/data.csv")
    get_or_create("t2")

    # 1. profile the data
    profile = await call("workspace", "inspect_dataset", task_id="t2", path="input/data.csv")
    print("PROFILE:", json.loads(profile)["column_names"])

    # 2. run some code in the sandbox that makes a file
    code = (
        "import pandas as pd\n"
        "df = pd.read_csv('input/data.csv')\n"
        "df.describe().to_csv('outputs/summary.csv')\n"
        "print('rows:', len(df))\n"
    )
    result = await call("execution", "execute_python", task_id="t2", code=code)
    print("RUN:", json.loads(result)["stdout"], json.loads(result)["files_created"])

    # 3. check the file that was produced
    check = await call("validation", "validate_manifest",
                       task_id="t2", required_outputs=["summary.csv"])
    print("CHECK:", check)

    destroy("t2")


asyncio.run(main())