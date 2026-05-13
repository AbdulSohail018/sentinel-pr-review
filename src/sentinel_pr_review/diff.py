from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


DIFF_FILE_RE = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", re.MULTILINE)


@dataclass(frozen=True)
class DiffContext:
    files: list[str]
    added_lines: list[tuple[str, int, str]]
    text: str


def parse_diff(diff: str) -> DiffContext:
    files = DIFF_FILE_RE.findall(diff)
    added_lines: list[tuple[str, int, str]] = []
    current_file = ""
    current_line = 0

    for line in diff.splitlines():
        hunk = HUNK_RE.match(line)
        if hunk:
            current_line = int(hunk.group(1))
            continue
        if line.startswith("+++ b/"):
            current_file = line.removeprefix("+++ b/")
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append((current_file, current_line, line[1:]))
            current_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            continue
        elif line.startswith(" "):
            current_line += 1

    return DiffContext(files=files, added_lines=added_lines, text=diff)


def review_fingerprint(title: str, description: str, diff: str, seed: int) -> str:
    payload = f"{seed}|{title}|{description}|{diff}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
