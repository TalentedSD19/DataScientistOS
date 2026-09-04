from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """
    Create one shared LLM configuration for all agents.

    Use a smaller model by default because Day 3 is about
    validating the architecture, not maximizing benchmark quality.
    """
    model_name = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

    return ChatOpenAI(
        model=model_name,
        temperature=0,
    )