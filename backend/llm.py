import os
from langchain_openai import ChatOpenAI


def get_llm(role: str, temperature: float = 0.0):
    """One place to choose which model each agent uses."""
    model = {
        "planner":   os.getenv("PLANNER_MODEL", "gpt-4o"),
        "coder":     os.getenv("CODER_MODEL", "gpt-4o"),
        "validator": os.getenv("VALIDATOR_MODEL", "gpt-4o"),
        "reporter":  os.getenv("REPORTER_MODEL", "gpt-4o-mini"),
    }.get(role, "gpt-4o")
    return ChatOpenAI(model=model, temperature=temperature)