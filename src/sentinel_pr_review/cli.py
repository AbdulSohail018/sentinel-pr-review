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

    args = parser.parse_args(argv)

    if args.command == "ui":
        uvicorn.run("sentinel_pr_review.api:app", host=args.host, port=args.port, reload=False)
        return 0

    if args.command == "benchmark":
        import json
        from pathlib import Path

        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        results = []
        for case in manifest:
            response = run_review(
                ReviewRequest(title=case["title"], diff=case["diff"], seed=42),
            )
            labels_ok = all(label in response.labels for label in case.get("expected_labels", []))
            agents_ok = all(
                any(run.agent == agent and run.invoked for run in response.agents)
                for agent in case.get("expected_agents", [])
            )
            results.append(
                {
                    "id": case["id"],
                    "labels_ok": labels_ok,
                    "agents_ok": agents_ok,
                    "recommendation": response.recommendation,
                    "cost_report_usd": response.cost_report_usd,
                }
            )
        json.dump(results, sys.stdout, indent=2)
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
