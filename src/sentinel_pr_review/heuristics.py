from __future__ import annotations

import re

from sentinel_pr_review.diff import DiffContext
from sentinel_pr_review.models import Finding


def confidence(score: float, threshold: float) -> tuple[float, bool]:
    value = round(min(max(score, 0.0), 1.0), 2)
    return value, value < threshold


def security_findings(ctx: DiffContext, threshold: float) -> list[Finding]:
    findings: list[Finding] = []
    patterns = [
        (r"password\s*=\s*['\"][^'\"]+['\"]", "Possible hard-coded credential", 0.82),
        (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "Possible API key in source", 0.8),
        (r"eval\s*\(", "Use of eval on dynamic input", 0.74),
        (r"pickle\.loads\s*\(", "Unsafe deserialization via pickle", 0.86),
        (r"execute\s*\(\s*f?['\"]", "Possible SQL injection via string-built query", 0.79),
        (r"subprocess\.[a-z_]+\([^)]*shell\s*=\s*True", "Shell invocation with shell=True", 0.77),
    ]

    for file_name, line_no, content in ctx.added_lines:
        for pattern, title, score in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                conf, needs_human = confidence(score, threshold)
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
                        confidence=conf,
                        needs_human_review=needs_human,
                    )
                )
    return findings


def performance_findings(ctx: DiffContext, threshold: float) -> list[Finding]:
    findings: list[Finding] = []
    for file_name, line_no, content in ctx.added_lines:
        if re.search(r"for\s+.+\s+in\s+.+:\s*$", content) and "select" in ctx.text.lower():
            conf, needs_human = confidence(0.7, threshold)
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
                    confidence=conf,
                    needs_human_review=needs_human,
                )
            )
        if re.search(r"while\s+True\s*:", content):
            conf, needs_human = confidence(0.68, threshold)
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
                    confidence=conf,
                    needs_human_review=needs_human,
                )
            )
    return findings


def correctness_findings(ctx: DiffContext, threshold: float) -> list[Finding]:
    findings: list[Finding] = []
    for file_name, line_no, content in ctx.added_lines:
        if "def " in content and '"""' not in content and "->" not in content:
            conf, needs_human = confidence(0.62, threshold)
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
                    confidence=conf,
                    needs_human_review=needs_human,
                )
            )
        if re.search(r"except\s*:\s*pass", content):
            conf, needs_human = confidence(0.76, threshold)
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
                    confidence=conf,
                    needs_human_review=needs_human,
                )
            )
    if ctx.files and not any(path.startswith(("test", "tests")) for path in ctx.files):
        conf, needs_human = confidence(0.6, threshold)
        findings.append(
            Finding(
                id="CORR-999",
                agent="correctness",
                severity="Medium",
                title="No test file changes detected in diff",
                evidence="Changed files do not include test paths.",
                confidence=conf,
                needs_human_review=needs_human,
            )
        )
    return findings


def style_findings(ctx: DiffContext, threshold: float, blocked: bool) -> list[Finding]:
    if blocked:
        return []
    findings: list[Finding] = []
    for file_name, line_no, content in ctx.added_lines:
        if re.search(r"def [a-z]+[A-Z]", content):
            conf, needs_human = confidence(0.58, threshold)
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
                    confidence=conf,
                    needs_human_review=needs_human,
                )
            )
    return findings
