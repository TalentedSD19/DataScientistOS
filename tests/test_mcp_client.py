import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend import mcp_client


def test_as_text_passes_through_plain_string():
    assert mcp_client._as_text("hello") == "hello"


def test_as_text_joins_content_blocks():
    blocks = [{"type": "text", "text": "foo"}, {"type": "text", "text": "bar"}]
    assert mcp_client._as_text(blocks) == "foobar"


def test_as_text_falls_back_to_str_for_other_types():
    assert mcp_client._as_text(123) == "123"


@pytest.fixture
def fake_tools(monkeypatch):
    write_file = MagicMock(name="write_file")
    write_file.name = "write_file"
    write_file.ainvoke = AsyncMock(return_value='{"ok": true}')
    monkeypatch.setattr(mcp_client, "_get_tools", AsyncMock(return_value=[write_file]))
    return write_file


def test_call_finds_tool_by_name_and_invokes_it(fake_tools):
    result = asyncio.run(mcp_client.call("write_file", task_id="t1", content="x"))

    assert result == '{"ok": true}'
    fake_tools.ainvoke.assert_called_once_with({"task_id": "t1", "content": "x"})


def test_call_raises_for_unknown_tool(fake_tools):
    with pytest.raises(RuntimeError):
        asyncio.run(mcp_client.call("no_such_tool"))
