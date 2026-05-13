from __future__ import annotations

from typing import Any

from sentinel_pr_review.models import ReviewResponse


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
