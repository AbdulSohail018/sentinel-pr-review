from __future__ import annotations

from sentinel_pr_review.benchmarking.corpus import BenchmarkCase
from sentinel_pr_review.models import ReviewResponse


def _finding_text(response: ReviewResponse) -> str:
    chunks: list[str] = []
    for run in response.agents:
        for finding in run.findings:
            chunks.append(finding.title.lower())
            chunks.append(finding.evidence.lower())
    return " ".join(chunks)


def case_detected(case: BenchmarkCase, response: ReviewResponse) -> bool:
    haystack = _finding_text(response)
    return any(issue in haystack for issue in case.known_issues)


def summarize_cases(cases: list[BenchmarkCase], responses: list[ReviewResponse]) -> dict[str, float]:
    true_positive = 0
    false_negative = 0
    false_positive = 0

    for case, response in zip(cases, responses, strict=True):
        detected = case_detected(case, response)
        if case.known_issues:
            if detected:
                true_positive += 1
            else:
                false_negative += 1
        elif detected:
            false_positive += 1

    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 1.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 1.0
    false_positive_rate = false_positive / len(cases) if cases else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "false_positive_rate": round(false_positive_rate, 4),
    }
