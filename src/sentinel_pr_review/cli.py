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
