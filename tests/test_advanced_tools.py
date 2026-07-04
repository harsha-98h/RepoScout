"""
Pytest suite for the Advanced Analysis tools (README, Commits, Issues).
"""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest
import requests

from tools.github_search import GitHubSearchTool


@pytest.fixture()
def tool() -> GitHubSearchTool:
    # Use a fresh instance with an isolated cache for tests
    return GitHubSearchTool()


def _mock_response(status_code: int, json_data: dict | list) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


class TestGetReadme:
    @patch("tools.github_search.requests.get")
    def test_get_readme_success(self, mock_get, tool: GitHubSearchTool) -> None:
        raw_text = "# Hello World"
        encoded = base64.b64encode(raw_text.encode("utf-8")).decode("utf-8")
        mock_get.return_value = _mock_response(200, {"content": encoded})

        res = tool.get_readme("owner/repo")
        assert res == "# Hello World"

    @patch("tools.github_search.requests.get")
    def test_get_readme_truncation(self, mock_get, tool: GitHubSearchTool) -> None:
        raw_text = "x" * 5000
        encoded = base64.b64encode(raw_text.encode("utf-8")).decode("utf-8")
        mock_get.return_value = _mock_response(200, {"content": encoded})

        res = tool.get_readme("owner/repo")
        assert len(res) < 5000
        assert "[README TRUNCATED]" in res

    @patch("tools.github_search.requests.get")
    def test_empty_readme(self, mock_get, tool: GitHubSearchTool) -> None:
        mock_get.return_value = _mock_response(200, {"content": ""})
        res = tool.get_readme("owner/repo")
        assert "empty or missing" in res

    @patch("tools.github_search.requests.get")
    def test_readme_not_found(self, mock_get, tool: GitHubSearchTool) -> None:
        mock_get.return_value = _mock_response(404, {"message": "Not Found"})
        res = tool.get_readme("owner/repo")
        assert "Error fetching README" in res


class TestGetRecentCommits:
    @patch("tools.github_search.requests.get")
    def test_commits_success(self, mock_get, tool: GitHubSearchTool) -> None:
        mock_data = [
            {"commit": {"message": "Fix bug", "author": {"name": "Alice", "date": "2023-01-01T12:00:00Z"}}},
            {"commit": {"message": "Add feature", "author": {"name": "Bob", "date": "2023-01-02T12:00:00Z"}}},
        ]
        mock_get.return_value = _mock_response(200, mock_data)

        res = tool.get_recent_commits("owner/repo", 2)
        assert "- [2023-01-01] Alice: Fix bug" in res
        assert "- [2023-01-02] Bob: Add feature" in res

    @patch("tools.github_search.requests.get")
    def test_commits_empty(self, mock_get, tool: GitHubSearchTool) -> None:
        mock_get.return_value = _mock_response(200, [])
        assert "No recent commits" in tool.get_recent_commits("owner/repo")


class TestGetOpenIssues:
    @patch("tools.github_search.requests.get")
    def test_issues_success(self, mock_get, tool: GitHubSearchTool) -> None:
        mock_data = [
            {"title": "Crash on startup", "user": {"login": "charlie"}},
            {"title": "Add dark mode", "user": {"login": "dave"}, "pull_request": {}},
        ]
        mock_get.return_value = _mock_response(200, mock_data)

        res = tool.get_open_issues("owner/repo", 2)
        assert "- [Issue] Crash on startup (by charlie)" in res
        assert "- [PR] Add dark mode (by dave)" in res

    @patch("tools.github_search.requests.get")
    def test_issues_empty(self, mock_get, tool: GitHubSearchTool) -> None:
        mock_get.return_value = _mock_response(200, [])
        assert "No open issues found" in tool.get_open_issues("owner/repo")
