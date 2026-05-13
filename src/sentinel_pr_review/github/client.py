from __future__ import annotations

from typing import Any

from sentinel_pr_review.config import ReviewSettings
from sentinel_pr_review.github.auth import build_installation_client
from sentinel_pr_review.github.delivery import publish_pull_request_review
from sentinel_pr_review.github.diff import build_pr_diff
from sentinel_pr_review.models import ReviewRequest, ReviewResponse
from sentinel_pr_review.orchestration.graph import run_review_graph


def build_review_payload(review: ReviewResponse) -> dict[str, Any]:
    return {
        "status": "ok",
        "recommendation": review.recommendation,
        "labels": review.labels,
        "comment": review.consolidated_comment_markdown,
        "inline_comments": [item.model_dump() for item in review.inline_comments],
        "cost_report_usd": review.cost_report_usd,
        "review_fingerprint": review.review_fingerprint,
    }


def process_pull_request_webhook(payload: dict[str, Any], settings: ReviewSettings) -> dict[str, Any]:
    pull_request = payload.get("pull_request", {})
    installation = payload.get("installation") or {}
    installation_id = installation.get("id")
    repository = payload.get("repository") or {}
    owner = repository.get("owner", {}).get("login")
    repo_name = repository.get("name")
    pr_number = pull_request.get("number")

    client = None
    pull = None
    if installation_id and owner and repo_name and pr_number:
        client = build_installation_client(settings, int(installation_id))
        if client is not None:
            repo = client.get_repo(f"{owner}/{repo_name}")
            pull = repo.get_pull(int(pr_number))

    if pull is not None:
        diff = build_pr_diff(pull)
        review = run_review_graph(
            ReviewRequest(
                title=pull.title,
                description=pull.body or "",
                diff=diff or "diff --git a/README.md b/README.md\n+++ b/README.md\n@@\n+placeholder",
                confidence_threshold=settings.confidence_threshold,
                seed=settings.seed,
            ),
            settings=settings,
        )
        delivery = publish_pull_request_review(pull, review)
        return {**build_review_payload(review), "delivery": delivery}

    review = run_review_graph(
        ReviewRequest(
            title=pull_request.get("title", "Untitled pull request"),
            description=pull_request.get("body", ""),
            diff=pull_request.get("diff")
            or "diff --git a/README.md b/README.md\n+++ b/README.md\n@@\n+placeholder",
            confidence_threshold=settings.confidence_threshold,
            seed=settings.seed,
        ),
        settings=settings,
    )
    return {**build_review_payload(review), "delivery": "skipped", "reason": "missing_github_app_config"}
