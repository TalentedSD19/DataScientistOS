import asyncio

from backend.mcp.client import MCPToolClient


async def main() -> None:
    async with MCPToolClient() as client:
        tools = await client.list_tools()

        for tool in tools:
            print(tool)


if __name__ == "__main__":
    asyncio.run(main())