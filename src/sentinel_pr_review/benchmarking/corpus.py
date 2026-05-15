from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    title: str
    diff: str
    known_issues: list[str]
    expected_agents: list[str]
    expected_labels: list[str]
    github_pr: str | None = None
    cve_ids: list[str] = field(default_factory=list)
    bug_references: list[str] = field(default_factory=list)


def build_default_corpus() -> list[BenchmarkCase]:
    templates = [
        (
            "auth-secret",
            "Hard-coded API key",
            'diff --git a/app/auth.py b/app/auth.py\n--- a/app/auth.py\n+++ b/app/auth.py\n@@\n+api_key = "sk-live-{index}"',
            ["api_key"],
            ["security"],
            ["needs-security-review"],
        ),
        (
            "sql-injection",
            "String-built SQL query",
            'diff --git a/app/db.py b/app/db.py\n--- a/app/db.py\n+++ b/app/db.py\n@@\n+db.execute(f"SELECT * FROM users WHERE name=\'{name}\'")',
            ["sql"],
            ["security"],
            ["needs-security-review"],
        ),
        (
            "pickle-load",
            "Unsafe pickle load",
            "diff --git a/app/io.py b/app/io.py\n--- a/app/io.py\n+++ b/app/io.py\n@@\n+pickle.loads(payload)",
            ["pickle"],
            ["security"],
            ["needs-security-review"],
        ),
        (
            "shell-true",
            "Shell invocation",
            "diff --git a/app/run.py b/app/run.py\n--- a/app/run.py\n+++ b/app/run.py\n@@\n+subprocess.run(cmd, shell=True)",
            ["shell"],
            ["security"],
            ["needs-security-review"],
        ),
        (
            "loop-hotpath",
            "Unbounded loop",
            "diff --git a/app/worker.py b/app/worker.py\n--- a/app/worker.py\n+++ b/app/worker.py\n@@\n+while True:\n+    process_queue()",
            ["loop"],
            ["performance"],
            ["performance-concern"],
        ),
        (
            "n-plus-one",
            "Loop with select",
            "diff --git a/app/report.py b/app/report.py\n--- a/app/report.py\n+++ b/app/report.py\n@@\n+for row in rows:\n+    db.execute('select * from orders where user_id = ?', row.id)",
            ["loop", "select"],
            ["performance"],
            ["performance-concern"],
        ),
        (
            "missing-tests",
            "Logic change without tests",
            "diff --git a/app/service.py b/app/service.py\n--- a/app/service.py\n+++ b/app/service.py\n@@\n+def calculate_total(items):\n+    return sum(items)",
            ["tests"],
            ["correctness"],
            ["needs-test-review"],
        ),
        (
            "swallowed-exception",
            "Swallowed exception",
            "diff --git a/app/handler.py b/app/handler.py\n--- a/app/handler.py\n+++ b/app/handler.py\n@@\n+except:\n+    pass",
            ["except"],
            ["correctness"],
            ["needs-test-review"],
        ),
        (
            "style-naming",
            "CamelCase function",
            "diff --git a/app/ui.py b/app/ui.py\n--- a/app/ui.py\n+++ b/app/ui.py\n@@\n+def renderCard():\n+    return True",
            ["style"],
            ["style"],
            [],
        ),
        (
            "password-leak",
            "Hard-coded password",
            'diff --git a/app/config.py b/app/config.py\n--- a/app/config.py\n+++ b/app/config.py\n@@\n+password = "admin123"',
            ["password"],
            ["security"],
            ["needs-security-review"],
        ),
    ]

    cases: list[BenchmarkCase] = []
    for index in range(50):
        template = templates[index % len(templates)]
        case_id, title, diff, known_issues, expected_agents, expected_labels = template
        cases.append(
            BenchmarkCase(
                id=f"{case_id}-{index + 1:02d}",
                title=f"{title} #{index + 1}",
                diff=diff.replace("{index}", str(index)),
                known_issues=known_issues,
                expected_agents=expected_agents,
                expected_labels=expected_labels,
            )
        )
    return cases
