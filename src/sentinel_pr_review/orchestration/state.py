from __future__ import annotations

from typing import TypedDict

from sentinel_pr_review.config import ReviewSettings
from sentinel_pr_review.diff import DiffContext
from sentinel_pr_review.models import AgentRun, Finding, ReviewRequest


class ReviewState(TypedDict):
    request: ReviewRequest
    settings: ReviewSettings
    context: DiffContext
    planned_agents: list[str]
    agent_runs: list[AgentRun]
    clarifications: list[str]
    errors: list[str]
    token_usage: int
