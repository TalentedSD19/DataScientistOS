import asyncio

from backend.agents.manager import run_manager


async def main() -> None:

    datasets = [
        {
            "id": "demo",
            "name": "demo",
            "type": "sqlite",
        }
    ]

    plan, step = await run_manager(
        "Which customer segment has the highest churn?",
        datasets,
    )

    print(plan.model_dump_json(indent=2))
    print(step.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())