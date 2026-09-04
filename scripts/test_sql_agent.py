import asyncio

from backend.agents.sql_agent import run_sql_agent


async def main() -> None:

    profile = {
        "tables": [
            {
                "name": "customers",
                "columns": [
                    {
                        "name": "customer_id",
                        "type": "INTEGER",
                    },
                    {
                        "name": "age",
                        "type": "INTEGER",
                    },
                    {
                        "name": "segment",
                        "type": "TEXT",
                    },
                    {
                        "name": "monthly_charges",
                        "type": "REAL",
                    },
                    {
                        "name": "tenure_months",
                        "type": "INTEGER",
                    },
                    {
                        "name": "churn",
                        "type": "INTEGER",
                    },
                ],
            }
        ]
    }

    result = await run_sql_agent(
        question=(
            "Which customer segment has "
            "the highest churn?"
        ),
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