from __future__ import annotations

from sentinel_pr_review import heuristics
from sentinel_pr_review.llm_client import with_retry
from sentinel_pr_review.models import AgentRun, Finding
from sentinel_pr_review.orchestration.llm_specialists import augment_with_llm
from sentinel_pr_review.orchestration.state import ReviewState
from sentinel_pr_review.tools.ast_analysis import ast_findings
from sentinel_pr_review.tools.semgrep import run_semgrep


def _estimate_usage(base: int, findings: list[Finding], budget: int, llm_usage: int) -> int:
    return min(base + len(findings) * 100 + llm_usage, budget)


def plan_agents(state: ReviewState) -> ReviewState:
    ctx = state["context"]
    planned = ["security", "performance", "correctness"]
    if ctx.files:
        planned.append("style")
    state["planned_agents"] = planned
    return state


def run_security(state: ReviewState) -> ReviewState:
    settings = state["settings"]
    threshold = state["request"].confidence_threshold
    budget = settings.budget_for("security")

    findings, error = with_retry(
        lambda: heuristics.security_findings(state["context"], threshold)
        + run_semgrep(state["context"], settings.semgrep_config, threshold)
    )
    if error:
        state["errors"].append(f"security: {error}")
    findings, llm_usage = augment_with_llm("security", state, findings)
    state["agent_runs"].append(
        AgentRun(
            agent="security",
            invoked=True,
            reason="Auth, secret, and injection checks on changed code.",
            token_budget=budget,
            token_usage=_estimate_usage(900, findings, budget, llm_usage),
            findings=findings,
        )
    )
    state["token_usage"] += state["agent_runs"][-1].token_usage
    return state


def run_performance(state: ReviewState) -> ReviewState:
    settings = state["settings"]
    threshold = state["request"].confidence_threshold
    budget = settings.budget_for("performance")
    findings, error = with_retry(
        lambda: heuristics.performance_findings(state["context"], threshold)
        + ast_findings(state["context"], threshold)
    )
    if error:
        state["errors"].append(f"performance: {error}")
    findings, llm_usage = augment_with_llm("performance", state, findings)
    state["agent_runs"].append(
        AgentRun(
            agent="performance",
            invoked=True,
            reason="Loop and query-related changes detected.",
            token_budget=budget,
            token_usage=_estimate_usage(800, findings, budget, llm_usage),
            findings=findings,
        )
    )
    state["token_usage"] += state["agent_runs"][-1].token_usage
    return state


def run_correctness(state: ReviewState) -> ReviewState:
    settings = state["settings"]
    threshold = state["request"].confidence_threshold
    budget = settings.budget_for("correctness")
    findings, error = with_retry(lambda: heuristics.correctness_findings(state["context"], threshold))
    if error:
        state["errors"].append(f"correctness: {error}")
    findings, llm_usage = augment_with_llm("correctness", state, findings)
    state["agent_runs"].append(
        AgentRun(
            agent="correctness",
            invoked=True,
            reason="Contract and test coverage checks on changed files.",
            token_budget=budget,
            token_usage=_estimate_usage(850, findings, budget, llm_usage),
            findings=findings,
        )
    )
    state["token_usage"] += state["agent_runs"][-1].token_usage
    return state


def route_clarifications(state: ReviewState) -> ReviewState:
    for run in state["agent_runs"]:
        for finding in run.findings:
            if finding.confidence < state["request"].confidence_threshold:
                state["clarifications"].append(
                    f"{run.agent} flagged {finding.title} for human review."
                )
    return state


def run_style(state: ReviewState) -> ReviewState:
    settings = state["settings"]
    threshold = state["request"].confidence_threshold
    budget = settings.budget_for("style")
    blocking = any(
        finding.severity in {"Critical", "High"}
        for run in state["agent_runs"]
        for finding in run.findings
    )
    findings: list[Finding] = []
    llm_usage = 0
    if not blocking:
        findings = heuristics.style_findings(state["context"], threshold, blocked=False)
        findings, llm_usage = augment_with_llm("style", state, findings)
    state["agent_runs"].append(
        AgentRun(
            agent="style",
            invoked=not blocking,
            reason="Skipped because higher-priority findings are open."
            if blocking
            else "No blocking findings from other agents.",
            token_budget=budget,
            token_usage=0 if blocking else _estimate_usage(400, findings, budget, llm_usage),
            findings=findings,
        )
    )
    state["token_usage"] += state["agent_runs"][-1].token_usage
    return state
