import os
from langchain_openai import ChatOpenAI


def get_llm(role: str, temperature: float = 0.0, max_tokens: int | None = None):
    """One place to choose which model each agent uses."""
    model = {
        "planner":   os.getenv("PLANNER_MODEL", "gpt-4o"),
        "coder":     os.getenv("CODER_MODEL", "gpt-4o-mini"),
        "validator": os.getenv("VALIDATOR_MODEL", "gpt-4o"),
        "reporter":  os.getenv("REPORTER_MODEL", "gpt-4o-mini"),
    }.get(role, "gpt-4o")
    kwargs = {"model": model, "temperature": temperature}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return ChatOpenAI(**kwargs)