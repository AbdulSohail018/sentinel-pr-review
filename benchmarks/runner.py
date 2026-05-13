from __future__ import annotations

import argparse
import json
from pathlib import Path

from sentinel_pr_review.models import ReviewRequest
from sentinel_pr_review.review_service import run_review


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Sentinel benchmark manifest")
    parser.add_argument("--manifest", default="benchmarks/manifest.json")
    args = parser.parse_args()

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
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
