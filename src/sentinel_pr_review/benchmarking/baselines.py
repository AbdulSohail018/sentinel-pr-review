from __future__ import annotations

from collections.abc import Callable

from sentinel_pr_review import heuristics
from sentinel_pr_review.benchmarking.corpus import BenchmarkCase
from sentinel_pr_review.benchmarking.github_copilot import fetch_copilot_review_findings
from sentinel_pr_review.diff import parse_diff
from sentinel_pr_review.models import AgentRun, Finding, ReviewRequest, ReviewResponse
from sentinel_pr_review.orchestration.graph import run_review_graph
from sentinel_pr_review.synthesis import labels, markdown_summary, recommendation, risk_level
from sentinel_pr_review.diff import review_fingerprint


def _response_from_findings(request: ReviewRequest, findings: list[Finding]) -> ReviewResponse:
    context = parse_diff(request.diff)
    recommendation_value = recommendation(findings)
    threshold = request.confidence_threshold
    inline_comments = [
        item
        for item in findings
        if item.severity in {"Critical", "High"}
        and item.confidence >= threshold
        and not item.needs_human_review
    ]
    human_queue = [item for item in findings if item.needs_human_review]
    fingerprint = review_fingerprint(request.title, request.description, request.diff, request.seed)
    cost_usd = 0.0
    return ReviewResponse(
        pr_summary=f"{request.title} modifies {len(context.files)} file(s).",
        risk_assessment=risk_level(findings),
        agents=[
            AgentRun(
                agent="single",
                invoked=True,
                reason="Single-agent baseline over merged heuristics.",
                token_budget=5000,
                token_usage=0,
                findings=findings,
            )
        ],
        recommendation=recommendation_value,
        consolidated_comment_markdown=markdown_summary(
            request,
            context,
            recommendation_value,
            findings,
            cost_usd,
            fingerprint,
        ),
        labels=labels(findings),
        inline_comments=inline_comments,
        human_review_queue=human_queue,
        cost_report_usd=cost_usd,
        review_fingerprint=fingerprint,
        seed=request.seed,
    )


def run_sentinel(request: ReviewRequest, case: BenchmarkCase | None = None) -> ReviewResponse:
    return run_review_graph(request)


def run_single_agent(request: ReviewRequest, case: BenchmarkCase | None = None) -> ReviewResponse:
    context = parse_diff(request.diff)
    threshold = request.confidence_threshold
    findings = (
        heuristics.security_findings(context, threshold)
        + heuristics.performance_findings(context, threshold)
        + heuristics.correctness_findings(context, threshold)
    )
    return _response_from_findings(request, findings)


def run_plain_claude(request: ReviewRequest, case: BenchmarkCase | None = None) -> ReviewResponse:
    context = parse_diff(request.diff)
    findings = heuristics.security_findings(context, request.confidence_threshold)
    return _response_from_findings(request, findings)


def run_copilot(request: ReviewRequest, case: BenchmarkCase | None = None) -> ReviewResponse:
    if case and case.github_pr:
        findings = fetch_copilot_review_findings(case.github_pr)
        if findings:
            return _response_from_findings(request, findings)
    return _response_from_findings(request, [])


BaselineFn = Callable[[ReviewRequest, BenchmarkCase | None], ReviewResponse]

BASELINES: dict[str, BaselineFn] = {
    "sentinel": run_sentinel,
    "single_agent": run_single_agent,
    "plain_claude": run_plain_claude,
    "copilot": run_copilot,
}


def run_baseline(name: str, case: BenchmarkCase) -> ReviewResponse:
    request = ReviewRequest(title=case.title, diff=case.diff, seed=42)
    return BASELINES[name](request, case)
