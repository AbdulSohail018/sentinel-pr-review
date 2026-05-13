from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from sentinel_pr_review.diff import DiffContext
from sentinel_pr_review.heuristics import confidence
from sentinel_pr_review.models import Finding


def run_semgrep(ctx: DiffContext, config: str, threshold: float) -> list[Finding]:
    if not shutil.which("semgrep"):
        return []

    findings: list[Finding] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        for file_name in ctx.files:
            target = root / file_name
            target.parent.mkdir(parents=True, exist_ok=True)
            lines = [content for path, _, content in ctx.added_lines if path == file_name]
            target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

        result = subprocess.run(
            [
                "semgrep",
                "--config",
                config,
                "--json",
                "--quiet",
                "--no-git-ignore",
                str(root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode not in {0, 1} or not result.stdout.strip():
            return findings

        payload = json.loads(result.stdout)
        for index, item in enumerate(payload.get("results", []), start=1):
            extra = item.get("extra", {})
            severity = extra.get("severity", "WARNING").upper()
            mapped = "High" if severity in {"ERROR", "CRITICAL"} else "Medium"
            score = 0.84 if mapped == "High" else 0.7
            conf, needs_human = confidence(score, threshold)
            findings.append(
                Finding(
                    id=f"SEC-SG-{index:03d}",
                    agent="security",
                    severity=mapped,
                    title=item.get("check_id", "semgrep finding"),
                    file=item.get("path"),
                    line_start=item.get("start", {}).get("line"),
                    line_end=item.get("end", {}).get("line"),
                    evidence=item.get("extra", {}).get("message", "semgrep match"),
                    confidence=conf,
                    needs_human_review=needs_human,
                )
            )
    return findings
