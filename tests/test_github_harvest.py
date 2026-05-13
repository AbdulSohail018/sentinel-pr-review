from unittest.mock import MagicMock, patch

from sentinel_pr_review.github.harvest import harvest_pull_requests


@patch("sentinel_pr_review.github.harvest.Github")
def test_harvest_pull_requests(mock_github: MagicMock) -> None:
    pull = MagicMock()
    pull.number = 42
    pull.title = "Fix auth"
    pull.merged = True
    file = MagicMock()
    file.filename = "app/auth.py"
    file.patch = "@@\n+api_key = 'x'"
    pull.get_files.return_value = [file]

    repo = MagicMock()
    repo.get_pulls.return_value = [pull]
    mock_github.return_value.get_repo.return_value = repo

    cases = harvest_pull_requests("owner/repo", 1, "token")
    assert len(cases) == 1
    assert cases[0].id.endswith("-42")
