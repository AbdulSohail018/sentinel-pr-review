# Sentinel PR Review

Multi-agent pull request review system that coordinates specialized reviewers for security, performance, correctness, and style.

## Status

Early scaffold. Agent prompt specifications and architecture notes are in `docs/` and `prompts/`. LangGraph orchestration and GitHub App integration are planned next.

## Stack

- Python 3.11
- LangGraph
- tree-sitter
- semgrep
- PyGithub

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## License

MIT
