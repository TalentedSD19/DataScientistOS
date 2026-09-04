from __future__ import annotations

import asyncio
import json
import os

from dotenv import load_dotenv

from backend.agents.critic import run_critic
from backend.agents.eda_agent import run_eda_agent
from backend.agents.manager import run_manager
from backend.agents.reporter import run_reporter
from backend.agents.scout import run_scout
from backend.agents.sql_agent import run_sql_agent
from backend.agents.stats_ml_agent import run_stats_ml_agent
from backend.mcp.client import MCPToolClient


load_dotenv()


QUESTION = (
    "Which customer segment has the highest churn, "
    "and is the difference statistically significant?"
)


async def main() -> None:

    dataset = os.getenv(
        "DEFAULT_DATASET",
        "demo",
    )

    print("=" * 70)
    print("DAY 3 — DataScientistOS agent smoke test")
    print("=" * 70)

    async with MCPToolClient() as mcp:

        # --------------------------------------------------
        # 1. Check MCP tools
        # --------------------------------------------------

        tools = await mcp.list_tools()

        print("\n[MCP TOOLS]")
        print(tools)

        # --------------------------------------------------
        # 2. Manager
        # --------------------------------------------------

        print("\n[1/7] MANAGER")

        datasets = await mcp.call(
            "list_datasets",
            {},
        )

        available_datasets = datasets.get(
            "datasets",
            [],
        )

        plan, manager_step = await run_manager(
            QUESTION,
            available_datasets,
        )

        print(
            json.dumps(
                plan.model_dump(),
                indent=2,
            )
        )

        # --------------------------------------------------
        # 3. Scout
        # --------------------------------------------------

        print("\n[2/7] SCOUT")

        scout_output = await run_scout(
            dataset=dataset,
            mcp=mcp,
        )

        print(
            json.dumps(
                scout_output.model_dump(),
                indent=2,
                default=str,
            )[:10000]
        )

        profile = {}

        for item in scout_output.tool_results:
            if item["tool"] == "inspect_dataset":
                profile = item["result"]

        # --------------------------------------------------
        # 4. SQL Analyst
        # --------------------------------------------------

        print("\n[3/7] SQL ANALYST")

        sql_output = await run_sql_agent(
            question=QUESTION,
            dataset=dataset,
            profile=profile,
            mcp=mcp,
        )

        print(
            json.dumps(
                sql_output.model_dump(),
                indent=2,
                default=str,
            )[:10000]
        )

        # --------------------------------------------------
        # 5. EDA Analyst
        # --------------------------------------------------

        print("\n[4/7] EDA ANALYST")

        eda_output = await run_eda_agent(
            question=QUESTION,
            dataset=dataset,
            profile=profile,
            mcp=mcp,
        )

        print(
            json.dumps(
                eda_output.model_dump(),
                indent=2,
                default=str,
            )[:10000]
        )

        # --------------------------------------------------
        # 6. Statistics / ML
        # --------------------------------------------------

        print("\n[5/7] STATS / ML")

        stats_output = await run_stats_ml_agent(
            question=QUESTION,
            dataset=dataset,
            profile=profile,
            analysis_type="diagnostic",
            target=plan.target or "churn",
            mcp=mcp,
        )

        print(
            json.dumps(
                stats_output.model_dump(),
                indent=2,
                default=str,
            )[:10000]
        )

        # --------------------------------------------------
        # Combine evidence
        # --------------------------------------------------

        all_findings = (
            sql_output.findings
            + eda_output.findings
            + stats_output.findings
        )

        all_evidence = (
            sql_output.evidence
            + eda_output.evidence
            + stats_output.evidence
        )

        all_errors = (
            sql_output.errors
            + eda_output.errors
            + stats_output.errors
        )

        # --------------------------------------------------
        # 7. Critic
        # --------------------------------------------------

        print("\n[6/7] CRITIC")

        critique, critic_step = await run_critic(
            question=QUESTION,
            plan=plan.model_dump(),
            findings=[
                item.model_dump()
                for item in all_findings
            ],
            evidence=[
                item.model_dump()
                for item in all_evidence
            ],
            errors=all_errors,
        )

        print(
            json.dumps(
                critique.model_dump(),
                indent=2,
            )
        )

        # --------------------------------------------------
        # 8. Reporter
        # --------------------------------------------------

        print("\n[7/7] REPORTER")

        report, reporter_step = await run_reporter(
            question=QUESTION,
            plan=plan.model_dump(),
            findings=[
                item.model_dump()
                for item in all_findings
            ],
            evidence=[
                item.model_dump()
                for item in all_evidence
            ],
        )

        print(
            json.dumps(
                report.model_dump(),
                indent=2,
            )
        )

        # --------------------------------------------------
        # Step log
        # --------------------------------------------------

        all_steps = [
            manager_step,
            *scout_output.steps,
            *sql_output.steps,
            *eda_output.steps,
            *stats_output.steps,
            critic_step,
            reporter_step,
        ]

        print("\n[STEP TRACE]")

        for step in all_steps:
            print(
                json.dumps(
                    step.model_dump(),
                    indent=2,
                )
            )

    print("\n" + "=" * 70)
    print("DAY 3 SMOKE TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())