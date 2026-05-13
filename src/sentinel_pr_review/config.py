from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewSettings:
    confidence_threshold: float = 0.65
    seed: int = 42
    token_budgets: dict[str, int] | None = None
    cost_per_token_usd: float = 0.000004
    anthropic_api_key: str | None = None
    coordinator_model: str = "claude-opus-4-20250514"
    specialist_model: str = "claude-sonnet-4-20250514"
    fallback_model: str = "claude-3-5-haiku-20241022"
    semgrep_config: str = "p/owasp-top-ten"
    github_app_id: str | None = None
    github_private_key: str | None = None
    github_private_key_path: str | None = None
    github_webhook_secret: str | None = None

    @classmethod
    def from_env(cls) -> ReviewSettings:
        budgets = {
            "coordinator": int(os.getenv("SENTINEL_BUDGET_COORDINATOR", "6000")),
            "security": int(os.getenv("SENTINEL_BUDGET_SECURITY", "4000")),
            "performance": int(os.getenv("SENTINEL_BUDGET_PERFORMANCE", "3500")),
            "correctness": int(os.getenv("SENTINEL_BUDGET_CORRECTNESS", "3500")),
            "style": int(os.getenv("SENTINEL_BUDGET_STYLE", "1500")),
        }
        return cls(
            confidence_threshold=float(os.getenv("SENTINEL_CONFIDENCE_THRESHOLD", "0.65")),
            seed=int(os.getenv("SENTINEL_SEED", "42")),
            token_budgets=budgets,
            cost_per_token_usd=float(os.getenv("SENTINEL_COST_PER_TOKEN_USD", "0.000004")),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            coordinator_model=os.getenv("SENTINEL_COORDINATOR_MODEL", "claude-opus-4-20250514"),
            specialist_model=os.getenv("SENTINEL_SPECIALIST_MODEL", "claude-sonnet-4-20250514"),
            fallback_model=os.getenv("SENTINEL_FALLBACK_MODEL", "claude-3-5-haiku-20241022"),
            semgrep_config=os.getenv("SENTINEL_SEMGREP_CONFIG", "p/owasp-top-ten"),
            github_app_id=os.getenv("GITHUB_APP_ID"),
            github_private_key=os.getenv("GITHUB_PRIVATE_KEY"),
            github_private_key_path=os.getenv("GITHUB_PRIVATE_KEY_PATH"),
            github_webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET"),
        )

    def budget_for(self, agent: str) -> int:
        budgets = self.token_budgets or {}
        return budgets.get(agent, 2000)
