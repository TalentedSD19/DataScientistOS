from __future__ import annotations

import asyncio
import json
import os

from dotenv import load_dotenv

from backend.graph.workflow import graph


load_dotenv()


QUESTION = (
    "Build a model to predict customer churn "
    "using the available customer attributes."
)


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


async def main() -> None:
    print_section("DAY 4 — LANGGRAPH END-TO-END SMOKE TEST")

    initial_state = {
        "question": QUESTION,
        "dataset": os.getenv(
            "DEFAULT_DATASET",
            "demo",
        ),
        "profile": {},
        "plan": None,
        "findings": [],
        "tool_results": [],
        "critique": None,
        "evidence": [],
        "report": None,
        "errors": [],
        "steps": 0,
        "critic_rounds": 0,
    }

    result = await graph.ainvoke(
        initial_state
    )

    print_section("PLAN")

    print(
        json.dumps(
            result.get("plan"),
            indent=2,
            default=str,
        )
    )

    print_section("CRITIQUE")

    print(
        json.dumps(
            result.get("critique"),
            indent=2,
            default=str,
        )
    )

    print_section("FINDINGS")

    print(
        json.dumps(
            result.get("findings"),
            indent=2,
            default=str,
        )
    )

    print_section("EVIDENCE")

    print(
        json.dumps(
            result.get("evidence"),
            indent=2,
            default=str,
        )
    )

    print_section("REPORT")

    print(
        json.dumps(
            result.get("report"),
            indent=2,
            default=str,
        )
    )

    print_section("ERRORS")

    print(
        json.dumps(
            result.get("errors"),
            indent=2,
            default=str,
        )
    )

    print_section("GRAPH SUMMARY")

    print(
        json.dumps(
            {
                "steps": result.get("steps"),
                "critic_rounds": result.get(
                    "critic_rounds"
                ),
                "dataset": result.get(
                    "dataset"
                ),
            },
            indent=2,
        )
    )

    print_section(
        "DAY 4 SMOKE TEST COMPLETE"
    )


if __name__ == "__main__":
    asyncio.run(main())