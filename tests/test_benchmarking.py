from sentinel_pr_review.benchmarking.baselines import run_sentinel
from sentinel_pr_review.benchmarking.corpus import build_default_corpus
from sentinel_pr_review.benchmarking.metrics import summarize_cases
from sentinel_pr_review.benchmarking.runner import run_benchmark
from sentinel_pr_review.models import ReviewRequest


def test_default_corpus_has_fifty_cases() -> None:
    assert len(build_default_corpus()) == 50


def test_benchmark_report_includes_baselines() -> None:
    report = run_benchmark(use_full_corpus=True)
    assert report["case_count"] == 50
    assert "sentinel" in report["baselines"]
    assert "single_agent" in report["baselines"]
    assert "plain_claude" in report["baselines"]
    assert "copilot" in report["baselines"]
    assert "precision" in report["baselines"]["sentinel"]["metrics"]


def test_metrics_handles_detected_cases() -> None:
    case = build_default_corpus()[0]
    response = run_sentinel(ReviewRequest(title=case.title, diff=case.diff, seed=42))
    metrics = summarize_cases([case], [response])
    assert metrics["recall"] >= 0.0
