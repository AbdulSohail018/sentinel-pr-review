from __future__ import annotations

import argparse
import json
import sys

import uvicorn

from sentinel_pr_review.models import ReviewRequest
from sentinel_pr_review.review_service import run_review


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sentinel PR Review")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ui_parser = subparsers.add_parser("ui", help="Launch the review console")
    ui_parser.add_argument("--host", default="127.0.0.1")
    ui_parser.add_argument("--port", type=int, default=8080)

    review_parser = subparsers.add_parser("review", help="Run a local review from a diff file")
    review_parser.add_argument("--diff", required=True)
    review_parser.add_argument("--title", default="Untitled pull request")
    review_parser.add_argument("--description", default="")
    review_parser.add_argument("--confidence-threshold", type=float, default=0.65)
    review_parser.add_argument("--seed", type=int, default=42)

    benchmark_parser = subparsers.add_parser("benchmark", help="Run benchmark manifest")
    benchmark_parser.add_argument("--manifest", default="benchmarks/manifest.json")
    benchmark_parser.add_argument("--full-corpus", action="store_true")
    benchmark_parser.add_argument("--output", default=None)

    harvest_parser = subparsers.add_parser("harvest", help="Harvest merged PRs into benchmark manifest")
    harvest_parser.add_argument("--repo", required=True)
    harvest_parser.add_argument("--limit", type=int, default=50)
    harvest_parser.add_argument("--output", default="benchmarks/real_manifest.json")
    harvest_parser.add_argument("--token", default=None)

    args = parser.parse_args(argv)

    if args.command == "ui":
        uvicorn.run("sentinel_pr_review.api:app", host=args.host, port=args.port, reload=False)
        return 0

    if args.command == "benchmark":
        from sentinel_pr_review.benchmarking.runner import run_benchmark

        report = run_benchmark(
            manifest_path=None if args.full_corpus else args.manifest,
            use_full_corpus=args.full_corpus,
            output_path=args.output,
        )
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if args.command == "harvest":
        import os
        from dataclasses import asdict
        from pathlib import Path

        from sentinel_pr_review.github.harvest import harvest_pull_requests

        token = args.token or os.getenv("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN is required for harvest")
        cases = harvest_pull_requests(args.repo, args.limit, token)
        payload = [asdict(case) for case in cases]
        Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        json.dump({"harvested": len(payload), "output": args.output}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    diff_text = open(args.diff, encoding="utf-8").read()
    response = run_review(
        ReviewRequest(
            title=args.title,
            description=args.description,
            diff=diff_text,
            confidence_threshold=args.confidence_threshold,
            seed=args.seed,
        )
    )
    json.dump(response.model_dump(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
