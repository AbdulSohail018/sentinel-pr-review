from __future__ import annotations

from typing import Any

from github.Issue import Issue
from github.PullRequest import PullRequest

from sentinel_pr_review.models import Finding, ReviewResponse


def _review_event(recommendation: str) -> str:
    if recommendation == "approve":
        return "APPROVE"
    if recommendation == "request_changes":
        return "REQUEST_CHANGES"
    return "COMMENT"


def _existing_fingerprint(issue: Issue, fingerprint: str) -> bool:
    marker = f"Review fingerprint: `{fingerprint}`"
    for comment in issue.get_comments():
        if marker in comment.body:
            return True
    return False


def _inline_comment_payload(finding: Finding, commit_sha: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "body": f"**{finding.severity}** {finding.title}\n\n{finding.evidence}",
        "commit_id": commit_sha,
        "path": finding.file,
    }
    if finding.line_start is not None:
        payload["line"] = finding.line_start
    return payload


def publish_pull_request_review(pull: PullRequest, review: ReviewResponse) -> dict[str, Any]:
    issue = pull.as_issue()
    if _existing_fingerprint(issue, review.review_fingerprint):
        return {
            "status": "skipped",
            "reason": "duplicate_fingerprint",
            "review_fingerprint": review.review_fingerprint,
        }

    issue.create_comment(review.consolidated_comment_markdown)
    for label in review.labels:
        issue.add_to_labels(label)

    commit_sha = pull.head.sha
    inline = [
        _inline_comment_payload(finding, commit_sha)
        for finding in review.inline_comments
        if finding.file
    ]
    if inline:
        pull.create_review(
            body="Sentinel inline findings for Critical/High severity issues.",
            event="COMMENT",
            comments=inline,
        )
    else:
        pull.create_review(
            body="Sentinel automated review completed.",
            event=_review_event(review.recommendation),
            commit=commit_sha,
        )

    return {
        "status": "published",
        "labels": review.labels,
        "inline_comment_count": len(inline),
        "review_fingerprint": review.review_fingerprint,
        "recommendation": review.recommendation,
    }
