from __future__ import annotations

from sentinel_pr_review.diff import DiffContext
from sentinel_pr_review.heuristics import confidence
from sentinel_pr_review.models import Finding


def _load_python_parser():
    try:
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser
    except ImportError:
        return None

    parser = Parser(Language(tspython.language()))
    return parser


def ast_findings(ctx: DiffContext, threshold: float) -> list[Finding]:
    parser = _load_python_parser()
    if parser is None:
        return []

    findings: list[Finding] = []
    by_file: dict[str, list[str]] = {}
    for file_name, _, content in ctx.added_lines:
        if file_name.endswith(".py"):
            by_file.setdefault(file_name, []).append(content)

    for file_name, lines in by_file.items():
        source = "\n".join(lines).encode("utf-8")
        tree = parser.parse(source)
        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            if node.type == "for_statement" and "for " in source.decode("utf-8", errors="ignore"):
                conf, needs_human = confidence(0.66, threshold)
                findings.append(
                    Finding(
                        id=f"PERF-AST-{len(findings) + 1:03d}",
                        agent="performance",
                        severity="Low",
                        title="Loop introduced in changed Python code",
                        file=file_name,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        evidence="tree-sitter detected a for loop in the changed region.",
                        confidence=conf,
                        needs_human_review=needs_human,
                    )
                )
            stack.extend(reversed(node.children))
    return findings
