import asyncio

from backend.agents.scout import run_scout


async def main() -> None:
    result = await run_scout("demo")

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())