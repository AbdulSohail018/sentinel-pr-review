from fastapi.testclient import TestClient

from sentinel_pr_review.api import app
from sentinel_pr_review.models import ReviewRequest
from sentinel_pr_review.review_service import run_review

SAMPLE_DIFF = """diff --git a/app/auth.py b/app/auth.py
index 1111111..2222222 100644
--- a/app/auth.py
+++ b/app/auth.py
@@ -10,3 +10,5 @@ def login(username, password):
     user = db.execute(f"SELECT * FROM users WHERE name='{username}'")
+    api_key = "sk-live-1234567890"
     return None
"""


def test_run_review_flags_security_issue() -> None:
    response = run_review(ReviewRequest(title="Auth change", diff=SAMPLE_DIFF))
    assert response.recommendation in {"comment", "request_changes"}
    assert any(finding.agent == "security" for finding in response.agents[0].findings)


def test_review_endpoint_returns_payload() -> None:
    client = TestClient(app)
    result = client.post(
        "/api/review",
        json={"title": "Auth change", "diff": SAMPLE_DIFF},
    )
    assert result.status_code == 200
    payload = result.json()
    assert payload["consolidated_comment_markdown"].startswith("## Sentinel PR Review")
