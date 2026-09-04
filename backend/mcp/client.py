from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from mcp import Client
from mcp.types import TextContent

load_dotenv()


class MCPToolError(RuntimeError):
    pass


class MCPToolClient:
    """
    Small wrapper around the official MCP Python client.

    The URL is expected to point to the Streamable HTTP endpoint,
    for example:
        http://127.0.0.1:8000/mcp
    """

    def __init__(self, url: str | None = None) -> None:
        self.url = url or os.getenv(
            "MCP_SERVER_URL",
            "http://127.0.0.1:8000/mcp",
        )
        self._cm = None
        self._client = None

    async def __aenter__(self) -> "MCPToolClient":
        self._cm = Client(self.url)
        self._client = await self._cm.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self._cm is not None:
            await self._cm.__aexit__(
                exc_type,
                exc_value,
                traceback,
            )

        self._cm = None
        self._client = None

    async def list_tools(self) -> list[str]:
        self._require_connection()

        result = await self._client.list_tools()

        return [tool.name for tool in result.tools]

    async def call(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        self._require_connection()

        result = await self._client.call_tool(
            name,
            arguments,
        )

        if result.is_error:
            message = self._extract_text(result.content)
            raise MCPToolError(
                f"MCP tool '{name}' failed: {message}"
            )

        if result.structured_content is not None:
            return result.structured_content

        text = self._extract_text(result.content)

        if not text:
            return {}

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "text": text,
            }

    def _require_connection(self) -> None:
        if self._client is None:
            raise RuntimeError(
                "MCPToolClient is not connected. "
                "Use 'async with MCPToolClient()'."
            )

    @staticmethod
    def _extract_text(content: list[Any]) -> str:
        pieces: list[str] = []

        for block in content:
            if isinstance(block, TextContent):
                pieces.append(block.text)

        return "\n".join(pieces)