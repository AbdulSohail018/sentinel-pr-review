from __future__ import annotations

from github import Auth, Github

from sentinel_pr_review.benchmarking.corpus import BenchmarkCase
from sentinel_pr_review.github.diff import build_pr_diff


def harvest_pull_requests(repo_full_name: str, limit: int, token: str) -> list[BenchmarkCase]:
    client = Github(auth=Auth.Token(token))
    repo = client.get_repo(repo_full_name)
    cases: list[BenchmarkCase] = []

    for pull in repo.get_pulls(state="closed", sort="updated", direction="desc"):
        if len(cases) >= limit:
            break
        if not pull.merged:
            continue
        diff = build_pr_diff(pull)
        if not diff.strip():
            continue
        cases.append(
            BenchmarkCase(
                id=f"github-{repo_full_name.replace('/', '-')}-{pull.number}",
                title=pull.title,
                diff=diff,
                known_issues=[],
                expected_agents=[],
                expected_labels=[],
                github_pr=f"{repo_full_name}#{pull.number}",
            )
        )
    return cases
