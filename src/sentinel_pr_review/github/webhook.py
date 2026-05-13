from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from sentinel_pr_review.config import ReviewSettings
from sentinel_pr_review.github.client import process_pull_request_webhook

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

    return process_pull_request_webhook(payload, settings)
