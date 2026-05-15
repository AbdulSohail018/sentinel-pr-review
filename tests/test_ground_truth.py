import json
from pathlib import Path

from sentinel_pr_review.benchmarking.corpus import BenchmarkCase
from sentinel_pr_review.benchmarking.ground_truth import annotate_manifest, apply_ground_truth, merge_case_with_overlay


def test_merge_case_with_overlay() -> None:
    case = BenchmarkCase(
        id="github-owner-repo-1",
        title="Fix",
        diff="diff",
        known_issues=[],
        expected_agents=[],
        expected_labels=[],
        github_pr="owner/repo#1",
    )
    merged = merge_case_with_overlay(
        case,
        {
            "id": "github-owner-repo-1",
            "known_issues": ["sql"],
            "cve_ids": ["CVE-2024-9999"],
            "bug_references": ["GHSA-abcd-efgh"],
        },
    )
    assert merged.known_issues == ["sql"]
    assert merged.cve_ids == ["CVE-2024-9999"]


def test_apply_ground_truth(tmp_path: Path) -> None:
    gt = tmp_path / "gt.json"
    gt.write_text(
        json.dumps(
            {
                "case-1": {
                    "known_issues": ["api_key"],
                }
            }
        ),
        encoding="utf-8",
    )
    cases = [
        BenchmarkCase(
            id="case-1",
            title="t",
            diff="d",
            known_issues=[],
            expected_agents=[],
            expected_labels=[],
        )
    ]
    out = apply_ground_truth(cases, gt)
    assert out[0].known_issues == ["api_key"]


def test_annotate_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps([{"id": "a", "title": "t", "diff": "d", "known_issues": [], "expected_agents": [], "expected_labels": []}]),
        encoding="utf-8",
    )
    gt = tmp_path / "gt.json"
    gt.write_text(json.dumps({"a": {"cve_ids": ["CVE-2024-1"]}}), encoding="utf-8")
    out = tmp_path / "o.json"
    count = annotate_manifest(manifest, gt, out)
    assert count == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload[0]["cve_ids"] == ["CVE-2024-1"]
