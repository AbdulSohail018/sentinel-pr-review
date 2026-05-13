from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from sentinel_pr_review.models import AgentRun, Finding, ReviewRequest, ReviewResponse

DIFF_FILE_RE = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", re.MULTILINE)


@dataclass(frozen=True)
class DiffContext:
    files: list[str]
    added_lines: list[tuple[str, int, str]]
    text: str


def _parse_diff(diff: str) -> DiffContext:
    files = DIFF_FILE_RE.findall(diff)
    added_lines: list[tuple[str, int, str]] = []
    current_file = ""
    current_line = 0

    for line in diff.splitlines():
        hunk = HUNK_RE.match(line)
        if hunk:
            current_line = int(hunk.group(1))
            continue
        if line.startswith("+++ b/"):
            current_file = line.removeprefix("+++ b/")
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append((current_file, current_line, line[1:]))
            current_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            continue
        elif line.startswith(" "):
            current_line += 1

    return DiffContext(files=files, added_lines=added_lines, text=diff)


def _fingerprint(request: ReviewRequest) -> str:
    payload = f"{request.seed}|{request.title}|{request.description}|{request.diff}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _confidence(score: float, threshold: float) -> tuple[float, bool]:
    confidence = round(min(max(score, 0.0), 1.0), 2)
    return confidence, confidence < threshold


def _security_findings(ctx: DiffContext, threshold: float) -> list[Finding]:
    findings: list[Finding] = []
    patterns = [
        (r"password\s*=\s*['\"][^'\"]+['\"]", "Possible hard-coded credential", "CWE-798", 0.82),
        (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "Possible API key in source", "CWE-798", 0.8),
        (r"eval\s*\(", "Use of eval on dynamic input", "CWE-95", 0.74),
        (r"pickle\.loads\s*\(", "Unsafe deserialization via pickle", "CWE-502", 0.86),
        (r"execute\s*\(\s*f?['\"]", "Possible SQL injection via string-built query", "CWE-89", 0.79),
        (r"subprocess\.[a-z_]+\([^)]*shell\s*=\s*True", "Shell invocation with shell=True", "CWE-78", 0.77),
    ]

    for file_name, line_no, content in ctx.added_lines:
        for pattern, title, _cwe, score in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                confidence, needs_human = _confidence(score, threshold)
                findings.append(
                    Finding(
                        id=f"SEC-{len(findings) + 1:03d}",
                        agent="security",
                        severity="High" if score >= 0.8 else "Medium",
                        title=title,
                        file=file_name or None,
                        line_start=line_no,
                        line_end=line_no,
                        evidence=content.strip(),
                        confidence=confidence,
                        needs_human_review=needs_human,
                    )
                )
    return findings


def _performance_findings(ctx: DiffContext, threshold: float) -> list[Finding]:
    findings: list[Finding] = []
    for file_name, line_no, content in ctx.added_lines:
        if re.search(r"for\s+.+\s+in\s+.+:\s*$", content) and "select" in ctx.text.lower():
            confidence, needs_human = _confidence(0.7, threshold)
            findings.append(
                Finding(
                    id=f"PERF-{len(findings) + 1:03d}",
                    agent="performance",
                    severity="Medium",
                    title="Potential N+1 query inside loop",
                    file=file_name or None,
                    line_start=line_no,
                    line_end=line_no,
                    evidence=content.strip(),
                    confidence=confidence,
                    needs_human_review=needs_human,
                )
            )
        if re.search(r"while\s+True\s*:", content):
            confidence, needs_human = _confidence(0.68, threshold)
            findings.append(
                Finding(
                    id=f"PERF-{len(findings) + 1:03d}",
                    agent="performance",
                    severity="Low",
                    title="Unbounded loop requires explicit exit criteria",
                    file=file_name or None,
                    line_start=line_no,
                    line_end=line_no,
                    evidence=content.strip(),
                    confidence=confidence,
                    needs_human_review=needs_human,
                )
            )
    return findings


def _correctness_findings(ctx: DiffContext, threshold: float) -> list[Finding]:
    findings: list[Finding] = []
    for file_name, line_no, content in ctx.added_lines:
        if "def " in content and '"""' not in content and "->" not in content:
            confidence, needs_human = _confidence(0.62, threshold)
            findings.append(
                Finding(
                    id=f"CORR-{len(findings) + 1:03d}",
                    agent="correctness",
                    severity="Low",
                    title="New function lacks docstring or return annotation",
                    file=file_name or None,
                    line_start=line_no,
                    line_end=line_no,
                    evidence=content.strip(),
                    confidence=confidence,
                    needs_human_review=needs_human,
                )
            )
        if re.search(r"except\s*:\s*pass", content):
            confidence, needs_human = _confidence(0.76, threshold)
            findings.append(
                Finding(
                    id=f"CORR-{len(findings) + 1:03d}",
                    agent="correctness",
                    severity="Medium",
                    title="Swallowed exception hides failure modes",
                    file=file_name or None,
                    line_start=line_no,
                    line_end=line_no,
                    evidence=content.strip(),
                    confidence=confidence,
                    needs_human_review=needs_human,
                )
            )
    if ctx.files and not any(path.startswith(("test", "tests")) for path in ctx.files):
        confidence, needs_human = _confidence(0.6, threshold)
        findings.append(
            Finding(
                id="CORR-999",
                agent="correctness",
                severity="Medium",
                title="No test file changes detected in diff",
                evidence="Changed files do not include test paths.",
                confidence=confidence,
                needs_human_review=needs_human,
            )
        )
    return findings


def _style_findings(ctx: DiffContext, threshold: float, blocked: bool) -> list[Finding]:
    if blocked:
        return []
    findings: list[Finding] = []
    for file_name, line_no, content in ctx.added_lines:
        if re.search(r"def [a-z]+[A-Z]", content):
            confidence, needs_human = _confidence(0.58, threshold)
            findings.append(
                Finding(
                    id=f"STYLE-{len(findings) + 1:03d}",
                    agent="style",
                    severity="Low",
                    title="Function naming may not match snake_case convention",
                    file=file_name or None,
                    line_start=line_no,
                    line_end=line_no,
                    evidence=content.strip(),
                    confidence=confidence,
                    needs_human_review=needs_human,
                )
            )
    return findings


def _risk_level(findings: list[Finding]) -> str:
    if any(item.severity == "Critical" for item in findings):
        return "high"
    if any(item.severity == "High" for item in findings):
        return "medium"
    if findings:
        return "low"
    return "low"


def _recommendation(findings: list[Finding]) -> str:
    if any(item.severity in {"Critical", "High"} and not item.needs_human_review for item in findings):
        return "request_changes"
    if findings:
        return "comment"
    return "approve"


def _labels(findings: list[Finding]) -> list[str]:
    labels: list[str] = []
    if any(item.agent == "security" for item in findings):
        labels.append("needs-security-review")
    if any(item.agent == "performance" for item in findings):
        labels.append("performance-concern")
    if any(item.agent == "correctness" for item in findings):
        labels.append("needs-test-review")
    return labels


def _markdown_summary(
    request: ReviewRequest,
    ctx: DiffContext,
    recommendation: str,
    findings: list[Finding],
    cost_usd: float,
    fingerprint: str,
) -> str:
    sections = [
        "## Sentinel PR Review",
        f"**Recommendation:** `{recommendation}`",
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


def run_review(request: ReviewRequest) -> ReviewResponse:
    ctx = _parse_diff(request.diff)
    threshold = request.confidence_threshold

    security = _security_findings(ctx, threshold)
    performance = _performance_findings(ctx, threshold)
    correctness = _correctness_findings(ctx, threshold)
    blocking = any(item.severity in {"Critical", "High"} for item in security + performance + correctness)
    style = _style_findings(ctx, threshold, blocked=blocking)

    agent_runs = [
        AgentRun(
            agent="security",
            invoked=True,
            reason="Diff touches executable code paths.",
            token_budget=4000,
            token_usage=min(1200 + len(security) * 120, 4000),
            findings=security,
        ),
        AgentRun(
            agent="performance",
            invoked=True,
            reason="Loop or query-related changes detected.",
            token_budget=3500,
            token_usage=min(900 + len(performance) * 100, 3500),
            findings=performance,
        ),
        AgentRun(
            agent="correctness",
            invoked=True,
            reason="Logic and contract checks required for changed files.",
            token_budget=3500,
            token_usage=min(1000 + len(correctness) * 110, 3500),
            findings=correctness,
        ),
        AgentRun(
            agent="style",
            invoked=not blocking,
            reason="Skipped because higher-priority findings are open."
            if blocking
            else "No blocking findings from other agents.",
            token_budget=1500,
            token_usage=0 if blocking else min(500 + len(style) * 60, 1500),
            findings=style,
        ),
    ]

    findings = security + performance + correctness + style
    recommendation = _recommendation(findings)
    inline_comments = [
        item
        for item in findings
        if item.severity in {"Critical", "High"}
        and item.confidence >= threshold
        and not item.needs_human_review
    ]
    human_queue = [item for item in findings if item.needs_human_review]
    token_total = sum(run.token_usage for run in agent_runs)
    cost_usd = round(token_total * 0.000004, 4)
    fingerprint = _fingerprint(request)

    return ReviewResponse(
        pr_summary=f"{request.title} modifies {len(ctx.files)} file(s).",
        risk_assessment=_risk_level(findings),
        agents=agent_runs,
        recommendation=recommendation,
        consolidated_comment_markdown=_markdown_summary(
            request,
            ctx,
            recommendation,
            findings,
            cost_usd,
            fingerprint,
        ),
        labels=_labels(findings),
        inline_comments=inline_comments,
        human_review_queue=human_queue,
        cost_report_usd=cost_usd,
        review_fingerprint=fingerprint,
        seed=request.seed,
    )
