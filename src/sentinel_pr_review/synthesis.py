from __future__ import annotations

from sentinel_pr_review.diff import DiffContext
from sentinel_pr_review.models import Finding, ReviewRequest


def risk_level(findings: list[Finding]) -> str:
    if any(item.severity == "Critical" for item in findings):
        return "high"
    if any(item.severity == "High" for item in findings):
        return "medium"
    if findings:
        return "low"
    return "low"


def recommendation(findings: list[Finding]) -> str:
    if any(item.severity in {"Critical", "High"} and not item.needs_human_review for item in findings):
        return "request_changes"
    if findings:
        return "comment"
    return "approve"


def labels(findings: list[Finding]) -> list[str]:
    result: list[str] = []
    if any(item.agent == "security" for item in findings):
        result.append("needs-security-review")
    if any(item.agent == "performance" for item in findings):
        result.append("performance-concern")
    if any(item.agent == "correctness" for item in findings):
        result.append("needs-test-review")
    return result


def markdown_summary(
    request: ReviewRequest,
    ctx: DiffContext,
    recommendation_value: str,
    findings: list[Finding],
    cost_usd: float,
    fingerprint: str,
) -> str:
    sections = [
        "## Sentinel PR Review",
        f"**Recommendation:** `{recommendation_value}`",
        f"**Changed files:** {len(ctx.files)}",
        "",
        request.description.strip() or "_No PR description provided._",
        "",
        "### Findings",
    ]
    if findings:
        for item in findings:
            location = f"{item.file}:{item.line_start}" if item.file and item.line_start else "n/a"
            sections.append(
                f"- **{item.severity}** ({item.agent}) {item.title} — `{location}` "
                f"(confidence {item.confidence:.2f})"
            )
    else:
        sections.append("- No actionable findings in this run.")
    sections.extend(
        [
            "",
            "### Cost",
            f"- Estimated run cost: `${cost_usd:.4f}`",
            f"- Review fingerprint: `{fingerprint}`",
            f"- Seed: `{request.seed}`",
        ]
    )
    return "\n".join(sections)
