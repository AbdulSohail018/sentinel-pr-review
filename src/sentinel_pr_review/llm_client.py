from __future__ import annotations

import random
import time
from typing import Callable

from sentinel_pr_review.config import ReviewSettings


class LLMClient:
    def __init__(self, settings: ReviewSettings) -> None:
        self.settings = settings
        self._rng = random.Random(settings.seed)
        self._client = None
        if settings.anthropic_api_key:
            try:
                from anthropic import Anthropic

                self._client = Anthropic(api_key=settings.anthropic_api_key)
            except ImportError:
                self._client = None

    def complete(self, system_prompt: str, user_prompt: str, model: str, max_tokens: int) -> tuple[str, int]:
        if self._client is None:
            return "", 0

        models = [model, self.settings.fallback_model]
        delay = 1.0
        for candidate in models:
            for attempt in range(3):
                try:
                    response = self._client.messages.create(
                        model=candidate,
                        max_tokens=max_tokens,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                    )
                    text = "".join(block.text for block in response.content if block.type == "text")
                    usage = response.usage.input_tokens + response.usage.output_tokens
                    return text, usage
                except Exception:
                    if attempt == 2 and candidate == models[-1]:
                        return "", 0
                    time.sleep(delay + self._rng.random())
                    delay *= 2
        return "", 0


def with_retry(operation: Callable[[], list], retries: int = 2) -> tuple[list, str | None]:
    delay = 0.5
    for attempt in range(retries + 1):
        try:
            return operation(), None
        except Exception as exc:
            if attempt == retries:
                return [], str(exc)
            time.sleep(delay)
            delay *= 2
    return [], "unknown failure"
