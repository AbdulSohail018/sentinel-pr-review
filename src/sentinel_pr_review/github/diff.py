from __future__ import annotations

from github.PullRequest import PullRequest


def build_pr_diff(pull: PullRequest) -> str:
    parts: list[str] = []
    for file in pull.get_files():
        if not file.patch:
            continue
        parts.append(f"diff --git a/{file.filename} b/{file.filename}\n{file.patch}")
    return "\n".join(parts)
