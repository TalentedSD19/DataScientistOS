from typing import Literal, Optional
from pydantic import BaseModel, Field


class Requirement(BaseModel):
    """One thing the prompt demands, written so a checker can test it."""
    kind: Literal["file", "csv", "image", "model", "text"]
    name: str = Field(description="exact output file name, e.g. accuracy_results.csv")
    expected_columns: Optional[list[str]] = None
    expected_rows: Optional[int] = None
    required_keywords: Optional[list[str]] = None
    numeric_only: bool = False
    note: str = Field(default="", description="plain English rule, e.g. '10-fold CV'")


class SubTask(BaseModel):
    id: str
    operation: str        # load_data / clean / train_model / cross_validate / plot / report
    description: str
    output: Optional[str] = None


class TaskSpec(BaseModel):
    """The prompt, turned into something a program can work with."""
    problem_type: str = "unknown"            # classification / regression / clustering / eda
    input_files: list[str] = []
    target_column: Optional[str] = None
    subtasks: list[SubTask] = []
    required_outputs: list[str] = []         # the most important field
    requirements: list[Requirement] = []
    constraints: list[str] = []              # "10-fold CV", "epochs = 60"

class Issue(BaseModel):
    """One problem the validator found."""
    severity: Literal["high", "medium", "low"]
    type: str        # runtime_error / missing_output / bad_artifact / missing_requirement
    message: str


class ValidationReport(BaseModel):
    """The verdict on one attempt."""
    status: Literal["PASS", "FAIL"]
    execution_score: float = 0.0     # did it run
    artifact_score: float = 0.0      # were the files made
    requirement_score: float = 0.0   # are the files right
    semantic_score: float = 0.0      # did it follow the rules
    final_score: float = 0.0
    issues: list[Issue] = []
    repair_instruction: str = ""     # what to tell the coder