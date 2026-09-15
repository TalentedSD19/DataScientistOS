import os
from langchain_openai import ChatOpenAI


def get_llm(role: str, temperature: float = 0.0, max_tokens: int | None = None):
    """One place to choose which model each agent uses."""
    model = {
        "analyzer":  os.getenv("ANALYZER_MODEL", "gpt-4o-mini"),
        "planner":   os.getenv("PLANNER_MODEL", "gpt-4o"),
        "coder":     os.getenv("CODER_MODEL", "gpt-4o-mini"),
        "verifier":  os.getenv("VERIFIER_MODEL", "gpt-4o"),
        "router":    os.getenv("ROUTER_MODEL", "gpt-4o"),
        "debugger":  os.getenv("DEBUGGER_MODEL", "gpt-4o-mini"),
    }.get(role, "gpt-4o")
    kwargs = {"model": model, "temperature": temperature}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return ChatOpenAI(**kwargs)
