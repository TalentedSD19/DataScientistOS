from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


AnalysisType = Literal[
    "descriptive",
    "diagnostic",
    "predictive",
    "insufficient_data",
]


AgentName = Literal[
    "manager",
    "scout",
    "sql_analyst",
    "eda_analyst",
    "stats_ml",
    "critic",
    "reporter",
]


EvidenceKind = Literal[
    "sql",
    "python",
    "stat_test",
    "model",
    "chart",
]


CritiqueVerdict = Literal[
    "accept",
    "revise",
    "reject",
]


class Plan(BaseModel):
    analysis_type: AnalysisType
    target: str | None = None
    dataset: str | None = None
    steps: list[str] = Field(default_factory=list)
    specialists: list[str] = Field(default_factory=list)
    rationale: str = ""


class Evidence(BaseModel):
    evidence_id: str
    kind: EvidenceKind
    step_id: str
    summary: str
    artifact_path: str | None = None


class Finding(BaseModel):
    claim: str
    evidence_ids: list[str] = Field(default_factory=list)
    numbers: dict[str, float] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class CritiqueIssue(BaseModel):
    severity: Literal["low", "medium", "high"]
    description: str
    suggested_fix: str


class Critique(BaseModel):
    verdict: CritiqueVerdict
    issues: list[CritiqueIssue] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class RunStep(BaseModel):
    step_id: str
    agent: AgentName
    action: str
    status: Literal["running", "success", "failed"]
    duration_ms: int
    message: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class AgentOutput(BaseModel):
    """
    Common envelope returned by analysis agents.
    """

    findings: list[Finding] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    steps: list[RunStep] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class SQLAction(BaseModel):
    query: str
    purpose: str


class EDAAction(BaseModel):
    code: str
    purpose: str


class StatisticsAction(BaseModel):
    operation: Literal[
        "chi_square",
        "t_test",
        "pearson",
        "spearman",
    ]
    sql_query: str
    purpose: str


class MLAction(BaseModel):
    target: str
    features: list[str]
    model_type: Literal[
        "logistic_regression",
        "random_forest",
        "xgboost",
    ]
    purpose: str


class Report(BaseModel):
    summary: str
    question_interpretation: str
    data_used: str
    key_findings: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    statistics_or_model: str | None = None
    limitations: list[str] = Field(default_factory=list)