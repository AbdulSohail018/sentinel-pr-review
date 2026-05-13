from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from sentinel_pr_review.config import ReviewSettings
from sentinel_pr_review.diff import DiffContext, parse_diff, review_fingerprint
from sentinel_pr_review.models import ReviewRequest, ReviewResponse
from sentinel_pr_review.orchestration import nodes
from sentinel_pr_review.orchestration.state import ReviewState
from sentinel_pr_review.synthesis import labels, markdown_summary, recommendation, risk_level


def _build_graph():
    graph = StateGraph(ReviewState)
    graph.add_node("plan", nodes.plan_agents)
    graph.add_node("security", nodes.run_security)
    graph.add_node("performance", nodes.run_performance)
    graph.add_node("correctness", nodes.run_correctness)
    graph.add_node("clarify", nodes.route_clarifications)
    graph.add_node("style", nodes.run_style)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "security")
    graph.add_edge("security", "performance")
    graph.add_edge("performance", "correctness")
    graph.add_edge("correctness", "clarify")
    graph.add_edge("clarify", "style")
    graph.add_edge("style", END)
    return graph.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    return _GRAPH


def run_review_graph(
    request: ReviewRequest,
    settings: ReviewSettings | None = None,
) -> ReviewResponse:
    settings = settings or ReviewSettings.from_env()
    settings = ReviewSettings(
        confidence_threshold=request.confidence_threshold,
        seed=request.seed,
        token_budgets=settings.token_budgets,
        cost_per_token_usd=settings.cost_per_token_usd,
        anthropic_api_key=settings.anthropic_api_key,
        coordinator_model=settings.coordinator_model,
        specialist_model=settings.specialist_model,
        fallback_model=settings.fallback_model,
        semgrep_config=settings.semgrep_config,
        github_app_id=settings.github_app_id,
        github_private_key=settings.github_private_key,
        github_private_key_path=settings.github_private_key_path,
        github_webhook_secret=settings.github_webhook_secret,
    )
    context: DiffContext = parse_diff(request.diff)
    state: ReviewState = {
        "request": request,
        "settings": settings,
        "context": context,
        "planned_agents": [],
        "agent_runs": [],
        "clarifications": [],
        "errors": [],
        "token_usage": 0,
    }
    final_state = get_graph().invoke(state)
    findings = [finding for run in final_state["agent_runs"] for finding in run.findings]
    threshold = request.confidence_threshold
    recommendation_value = recommendation(findings)
    inline_comments = [
        item
        for item in findings
        if item.severity in {"Critical", "High"}
        and item.confidence >= threshold
        and not item.needs_human_review
    ]
    human_queue = [item for item in findings if item.needs_human_review]
    cost_usd = round(final_state["token_usage"] * settings.cost_per_token_usd, 4)
    fingerprint = review_fingerprint(request.title, request.description, request.diff, request.seed)

    return ReviewResponse(
        pr_summary=f"{request.title} modifies {len(context.files)} file(s).",
        risk_assessment=risk_level(findings),
        agents=final_state["agent_runs"],
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
