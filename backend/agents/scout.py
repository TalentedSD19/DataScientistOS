from __future__ import annotations

import time
from typing import Any

from backend.agents.common import create_step
from backend.mcp.client import MCPToolClient
from backend.db.models import AgentOutput


async def run_scout(
    dataset: str | None = None,
    mcp: MCPToolClient | None = None,
) -> AgentOutput:
    start = int(time.time() * 1000)

    errors: list[dict[str, Any]] = []

    try:
        if mcp is None:
            async with MCPToolClient() as client:
                return await _run_scout(
                    client,
                    dataset,
                    start,
                )

        return await _run_scout(
            mcp,
            dataset,
            start,
        )

    except Exception as exc:
        step = create_step(
            agent="scout",
            action="inspect_dataset",
            status="failed",
            duration=int(time.time() * 1000) - start,
            message=str(exc),
        )

        errors.append(
            {
                "type": "runtime",
                "message": str(exc),
            }
        )

        return AgentOutput(
            errors=errors,
            steps=[step],
        )


async def _run_scout(
    mcp: MCPToolClient,
    dataset: str | None,
    start: int,
) -> AgentOutput:
    datasets = await mcp.call(
        "list_datasets",
        {},
    )

    selected_dataset = dataset

    if selected_dataset is None:
        available = datasets.get("datasets", [])

        if not available:
            raise RuntimeError(
                "No datasets were returned by MCP."
            )

        selected_dataset = available[0].get("id")

    profile = await mcp.call(
        "inspect_dataset",
        {
            "dataset": selected_dataset,
        },
    )

    step = create_step(
        agent="scout",
        action="inspect_dataset",
        status="success",
        duration=int(time.time() * 1000) - start,
        message=f"Inspected dataset {selected_dataset}",
    )

    return AgentOutput(
        tool_results=[
            {
                "tool": "list_datasets",
                "result": datasets,
            },
            {
                "tool": "inspect_dataset",
                "dataset": selected_dataset,
                "result": profile,
            },
        ],
        steps=[step],
    )