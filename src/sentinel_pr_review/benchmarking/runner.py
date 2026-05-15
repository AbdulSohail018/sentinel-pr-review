from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sentinel_pr_review.benchmarking.baselines import BASELINES, run_baseline
from sentinel_pr_review.benchmarking.corpus import BenchmarkCase, build_default_corpus
from sentinel_pr_review.benchmarking.metrics import case_detected, summarize_cases


def load_cases(manifest_path: str | None, use_full_corpus: bool) -> list[BenchmarkCase]:
    if use_full_corpus or manifest_path is None:
        return build_default_corpus()
    path = Path(manifest_path)
    if not path.exists():
        return build_default_corpus()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        BenchmarkCase(
            id=item["id"],
            title=item["title"],
            diff=item["diff"],
            known_issues=item.get("known_issues", []),
            expected_agents=item.get("expected_agents", []),
            expected_labels=item.get("expected_labels", []),
            github_pr=item.get("github_pr"),
            cve_ids=item.get("cve_ids", []),
            bug_references=item.get("bug_references", []),
        )
        for item in payload
    ]


def run_benchmark(
    manifest_path: str | None = None,
    use_full_corpus: bool = False,
    output_path: str | None = None,
    ground_truth_path: str | None = None,
) -> dict[str, Any]:
    cases = load_cases(manifest_path, use_full_corpus)
    if ground_truth_path:
        from sentinel_pr_review.benchmarking.ground_truth import apply_ground_truth

        cases = apply_ground_truth(cases, ground_truth_path)
    report: dict[str, Any] = {"case_count": len(cases), "baselines": {}}

    for baseline_name in BASELINES:
        started = time.perf_counter()
        responses = []
        per_case = []
        total_cost = 0.0
        for case in cases:
            response = run_baseline(baseline_name, case)
            responses.append(response)
            total_cost += response.cost_report_usd
            per_case.append(
                {
                    "id": case.id,
                    "detected": case_detected(case, response),
                    "labels": response.labels,
                    "recommendation": response.recommendation,
                    "cost_report_usd": response.cost_report_usd,
                }
            )
        elapsed = time.perf_counter() - started
        report["baselines"][baseline_name] = {
            "metrics": summarize_cases(cases, responses),
            "time_to_review_seconds": round(elapsed, 3),
            "cost_per_pr_usd": round(total_cost / len(cases), 4) if cases else 0.0,
            "cases": per_case,
        }

    if output_path:
        Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
