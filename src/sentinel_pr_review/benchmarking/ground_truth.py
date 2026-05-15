from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sentinel_pr_review.benchmarking.corpus import BenchmarkCase


def load_ground_truth_overlay(path: str | Path) -> dict[str, dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return {str(item["id"]): dict(item) for item in raw if "id" in item}
    return {str(k): (v if isinstance(v, dict) else {}) for k, v in raw.items()}


def merge_case_with_overlay(case: BenchmarkCase, overlay: dict[str, Any]) -> BenchmarkCase:
    base = asdict(case)
    clean = {k: v for k, v in overlay.items() if k != "id"}
    for key, value in clean.items():
        if key in base and value is not None:
            base[key] = value
    return BenchmarkCase(**base)


def apply_ground_truth(cases: list[BenchmarkCase], overlay_path: str | Path) -> list[BenchmarkCase]:
    overlay_map = load_ground_truth_overlay(overlay_path)
    merged: list[BenchmarkCase] = []
    for case in cases:
        if case.id in overlay_map:
            merged.append(merge_case_with_overlay(case, overlay_map[case.id]))
        else:
            merged.append(case)
    return merged


def annotate_manifest(manifest_path: str | Path, ground_truth_path: str | Path, output_path: str | Path) -> int:
    rows: list[dict[str, Any]] = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    overlay_map = load_ground_truth_overlay(ground_truth_path)
    for row in rows:
        oid = str(row.get("id", ""))
        if oid in overlay_map:
            extra = {k: v for k, v in overlay_map[oid].items() if k != "id"}
            row.update(extra)
    Path(output_path).write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return len(rows)
