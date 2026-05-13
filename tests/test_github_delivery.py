from unittest.mock import MagicMock

from sentinel_pr_review.github.delivery import publish_pull_request_review
from sentinel_pr_review.models import AgentRun, Finding, ReviewResponse


def _review() -> ReviewResponse:
    return ReviewResponse(
        pr_summary="summary",
        risk_assessment="medium",
        agents=[
            AgentRun(
                agent="security",
                invoked=True,
                reason="test",
                token_budget=100,
                token_usage=10,
                findings=[],
            )
        ],
        recommendation="comment",
        consolidated_comment_markdown="## Sentinel PR Review\nReview fingerprint: `abc123`",
        labels=["needs-security-review"],
        inline_comments=[
            Finding(
                id="SEC-001",
                agent="security",
                severity="High",
                title="Secret leak",
                file="app/auth.py",
                line_start=10,
                line_end=10,
                evidence="api_key = 'x'",
                confidence=0.9,
            )
        ],
        human_review_queue=[],
        cost_report_usd=0.01,
        review_fingerprint="abc123",
        seed=42,
    )


def test_publish_skips_duplicate_fingerprint() -> None:
    pull = MagicMock()
    issue = MagicMock()
    existing = MagicMock()
    existing.body = "Review fingerprint: `abc123`"
    issue.get_comments.return_value = [existing]
    pull.as_issue.return_value = issue

    result = publish_pull_request_review(pull, _review())
    assert result["status"] == "skipped"
    issue.create_comment.assert_not_called()


def test_publish_creates_comment_and_labels() -> None:
    pull = MagicMock()
    issue = MagicMock()
    issue.get_comments.return_value = []
    pull.as_issue.return_value = issue
    pull.head.sha = "sha123"

    result = publish_pull_request_review(pull, _review())
    assert result["status"] == "published"
    issue.create_comment.assert_called_once()
    issue.add_to_labels.assert_called_once_with("needs-security-review")
    pull.create_review.assert_called_once()
