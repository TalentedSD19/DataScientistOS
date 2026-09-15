from langchain_mcp_adapters.client import MultiServerMCPClient

from backend.config import MCP_WORKSPACE_URL, MCP_EXEC_URL

_client = MultiServerMCPClient({
    "workspace": {"url": MCP_WORKSPACE_URL, "transport": "streamable_http"},
    "execution": {"url": MCP_EXEC_URL,      "transport": "streamable_http"},
})

# Remember the tool lists so we don't fetch them over and over
_cache: dict[str, list] = {}


async def get_tools(*servers: str) -> list:
    """Get the tools from one or more servers."""
    names = servers or ("workspace", "execution")
    tools = []
    for name in names:
        if name not in _cache:
            _cache[name] = await _client.get_tools(server_name=name)
        tools.extend(_cache[name])
    return tools


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


async def call(server: str, tool_name: str, **kwargs) -> str:
    """Call one tool directly, e.g. call('workspace', 'write_file', ...)."""
    tools = await get_tools(server)
    tool = next(t for t in tools if t.name == tool_name)
    result = await tool.ainvoke(kwargs)
    return _as_text(result)