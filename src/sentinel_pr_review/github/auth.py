from __future__ import annotations

from pathlib import Path

from github import Auth, Github, GithubIntegration

from sentinel_pr_review.config import ReviewSettings


def load_private_key(settings: ReviewSettings) -> str | None:
    if settings.github_private_key:
        return settings.github_private_key
    if settings.github_private_key_path:
        return Path(settings.github_private_key_path).read_text(encoding="utf-8")
    return None


def build_installation_client(settings: ReviewSettings, installation_id: int) -> Github | None:
    if not settings.github_app_id:
        return None
    private_key = load_private_key(settings)
    if not private_key:
        return None
    auth = Auth.AppAuth(settings.github_app_id, private_key)
    integration = GithubIntegration(auth=auth)
    token = integration.get_access_token(installation_id).token
    return Github(auth=Auth.Token(token))
