from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    title: str = Field(default="Untitled pull request", max_length=200)
    description: str = ""
    diff: str = Field(min_length=1)
    confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    seed: int = Field(default=42, ge=0)


class Finding(BaseModel):
    id: str
    agent: str
    severity: Literal["Critical", "High", "Medium", "Low"]
    title: str
    file: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    evidence: str
    confidence: float
    needs_human_review: bool = False


class AgentRun(BaseModel):
    agent: str
    invoked: bool
    reason: str
    token_budget: int
    token_usage: int
    findings: list[Finding] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    pr_summary: str
    risk_assessment: Literal["low", "medium", "high"]
    agents: list[AgentRun]
    recommendation: Literal["approve", "comment", "request_changes"]
    consolidated_comment_markdown: str
    labels: list[str]
    inline_comments: list[Finding]
    human_review_queue: list[Finding]
    cost_report_usd: float
    review_fingerprint: str
    seed: int
