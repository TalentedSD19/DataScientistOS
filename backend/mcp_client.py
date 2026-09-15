from langchain_mcp_adapters.client import MultiServerMCPClient

from backend.config import MCP_SERVER_URL

# Every agent tool -- write_file, execute_file -- lives on this one MCP server.
_client = MultiServerMCPClient({
    "tools": {"url": MCP_SERVER_URL, "transport": "streamable_http"},
})

_tools_cache: list | None = None


async def _get_tools() -> list:
    """Fetch the server's tool list once, then reuse it."""
    global _tools_cache
    if _tools_cache is None:
        _tools_cache = await _client.get_tools(server_name="tools")
    return _tools_cache


def _as_text(result) -> str:
    """langchain-mcp-adapters returns tool output as either a plain string
    or a list of content blocks (e.g. [{"type": "text", "text": "..."}])
    depending on version. Our MCP tools always return a single JSON string,
    so flatten either shape back down to that string."""
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in result
        )
    return str(result)


async def call(tool_name: str, **kwargs) -> str:
    """Call one tool by name, e.g. call('write_file', task_id=..., path=..., content=...)."""
    tools = await _get_tools()
    tool = next(t for t in tools if t.name == tool_name)
    result = await tool.ainvoke(kwargs)
    return _as_text(result)
