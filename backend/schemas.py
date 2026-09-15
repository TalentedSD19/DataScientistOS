from typing import Literal, Optional
from pydantic import BaseModel, Field


class NextStep(BaseModel):
    """The single next step the planner wants taken."""
    goal: str = Field(description="one clear, small, executable step")


class VerifierResult(BaseModel):
    """Whether the current plan and code are sufficient to answer the query."""
    status: Literal["SUFFICIENT", "INSUFFICIENT"]


class RouterDecision(BaseModel):
    """What to do about an insufficient plan: add a step, or redo a bad one."""
    action: Literal["ADD_STEP", "BACKTRACK"]
    backtrack_to: Optional[int] = Field(
        default=None,
        description="step_id to redo from; only set when action is BACKTRACK",
    )
