from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sentinel_pr_review.github.webhook import router as github_router
from sentinel_pr_review.models import ReviewRequest, ReviewResponse
from sentinel_pr_review.review_service import run_review

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Sentinel PR Review", version="0.3.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(github_router)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/review", response_model=ReviewResponse)
def review(request: ReviewRequest) -> ReviewResponse:
    return run_review(request)
