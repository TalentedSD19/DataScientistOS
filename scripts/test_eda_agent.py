import asyncio

from backend.agents.eda_agent import run_eda_agent


async def main() -> None:

    profile = {
        "tables": [
            {
                "name": "customers",
                "columns": [
                    {"name": "age", "type": "INTEGER"},
                    {"name": "segment", "type": "TEXT"},
                    {"name": "monthly_charges", "type": "REAL"},
                    {"name": "tenure_months", "type": "INTEGER"},
                    {"name": "churn", "type": "INTEGER"},
                ],
            }
        ]
    }

    result = await run_eda_agent(
        question="Compare churn across customer segments.",
        dataset="demo",
        profile=profile,
    )

    print(
        result.model_dump_json(
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())