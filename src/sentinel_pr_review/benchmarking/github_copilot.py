from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any

from sentinel_pr_review.models import Finding


def fetch_copilot_review_findings(github_pr: str) -> list[Finding]:
    if not shutil.which("gh"):
        return []
    match = re.match(r"^([^/]+)/([^#]+)#(\d+)$", github_pr.strip())
    if not match:
        return []
    owner, repo, num = match.group(1), match.group(2), match.group(3)
    proc = subprocess.run(
        ["gh", "api", f"repos/{owner}/{repo}/pulls/{num}/reviews", "--paginate"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if proc.returncode != 0:
        return []
    try:
        reviews: list[dict[str, Any]] = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []
    findings: list[Finding] = []
    for index, review in enumerate(reviews):
        user = (review.get("user") or {}).get("login", "").lower()
        if "copilot" not in user:
            continue
        body = (review.get("body") or "").strip()
        if not body:
            continue
        findings.append(
            Finding(
                id=f"COPILOT-{index + 1:03d}",
                agent="copilot",
                severity="Low",
                title="GitHub Copilot pull request review",
                evidence=body[:4000],
                confidence=0.72,
            )
        )
    return findings
