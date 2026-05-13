from __future__ import annotations

import json
from dataclasses import asdict

from sentinel_pr_review.benchmarking.corpus import build_default_corpus


def main() -> int:
    payload = [asdict(case) for case in build_default_corpus()]
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
