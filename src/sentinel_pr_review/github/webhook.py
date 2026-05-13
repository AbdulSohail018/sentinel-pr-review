from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from sentinel_pr_review.config import ReviewSettings
from sentinel_pr_review.github.client import build_review_payload
from sentinel_pr_review.models import ReviewRequest
from sentinel_pr_review.orchestration.graph import run_review_graph

router = APIRouter(prefix="/api/github", tags=["github"])


def _verify_signature(secret: str, body: bytes, signature: str | None) -> None:
    if not secret:
        return
    if not signature or not signature.startswith("sha256="):
        raise HTTPException(status_code=401, detail="missing webhook signature")
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(f"sha256={digest}", signature):
        raise HTTPException(status_code=401, detail="invalid webhook signature")


@router.post("/webhook")
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
) -> dict[str, Any]:
    settings = ReviewSettings.from_env()
    body = await request.body()
    _verify_signature(settings.github_webhook_secret or "", body, x_hub_signature_256)
    payload = json.loads(body.decode("utf-8"))

    if x_github_event not in {"pull_request", "ping"}:
        return {"status": "ignored", "event": x_github_event}

    if x_github_event == "ping":
        return {"status": "ok", "event": "ping"}

    action = payload.get("action")
    if action not in {"opened", "synchronize", "reopened"}:
        return {"status": "ignored", "action": action}

    pull_request = payload.get("pull_request", {})
    diff = pull_request.get("diff") or pull_request.get("body", "")
    review = run_review_graph(
        ReviewRequest(
            title=pull_request.get("title", "Untitled pull request"),
            description=pull_request.get("body", ""),
            diff=diff or "diff --git a/README.md b/README.md\n+++ b/README.md\n@@\n+placeholder",
            confidence_threshold=settings.confidence_threshold,
            seed=settings.seed,
        ),
        settings=settings,
    )
    return build_review_payload(review)
