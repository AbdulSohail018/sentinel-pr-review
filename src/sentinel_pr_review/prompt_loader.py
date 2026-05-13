from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


def load_prompt(agent: str) -> str:
    prompt_path = PROMPTS_DIR / f"{agent}.md"
    return prompt_path.read_text(encoding="utf-8")
