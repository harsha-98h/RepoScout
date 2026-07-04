"""
GitHub Search Tool.

Enhanced with intelligent in-process caching, typed retry logic, and
properly typed return values.  Uses the custom exception hierarchy from
:mod:`utils.exceptions` instead of bare ``Exception`` raises.
"""

from __future__ import annotations

import base64
import re
from typing import Any

import requests

import config
from utils.cache_manager import CacheManager
from utils.error_handler import ErrorDetector
from utils.exceptions import GitHubAPIError
from utils.logger import setup_logger
from utils.retry_manager import RetryManager

logger = setup_logger(__name__)


class GitHubSearchTool:
    """Search GitHub repositories using the GitHub REST API.

    Enhanced with:
    - In-process TTL cache (30 min default)
    - Exponential-backoff retry on transient failures
    - Typed return values and custom exception hierarchy
    - Flexible result-count auto-detection from the query string
    """

    def __init__(self) -> None:
        self.base_url: str = config.GITHUB_API_BASE

        self.headers: dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
        }

        if config.GITHUB_TOKEN:
            self.headers["Authorization"] = f"token {config.GITHUB_TOKEN}"

        self.detector = ErrorDetector()
        self.retry_manager = RetryManager(max_retries=3, base_delay=1.0, max_delay=30.0)
        self.cache_manager = CacheManager(ttl_seconds=1800)  # 30-min cache

    # ------------------------------------------------------------------
    # Public: search
    # ------------------------------------------------------------------

    def search_repositories(
        self, query: str, max_results: int | None = None
    ) -> list[dict[str, Any]]:
        """Search GitHub repositories.

        The result count can be specified directly via *max_results* **or**
        embedded in the query string (e.g. "Find 10 AI agent repos").

        Args:
            query:       GitHub search query string.
            max_results: Number of results to return (1–20).  Auto-detected
                         from *query* when ``None``.

        Returns:
            List of repository dicts, or an error dict on permanent failure.
        """
        max_results = self._resolve_max_results(query, max_results)
        logger.info("🔍 Searching GitHub for: %s (max %d results)", query, max_results)

        cache_key = f"search:{query}:{max_results}"
        cached = self.cache_manager.get(cache_key)
        if cached is not None:
            logger.info("✅ Cache hit for query: %s", query)
            return cached  # type: ignore[return-value]

        try:
            results: list[dict[str, Any]] = self.retry_manager.execute_with_retry(
                self._search_api, query, max_results
            )
            self.cache_manager.set(cache_key, results)
            return results

        except GitHubAPIError as exc:
            logger.error("❌ GitHub API error after retries: %s", exc)
            return self._error_response(str(exc))

        except Exception as exc:
            logger.error("❌ Unexpected error during search: %s", exc)
            return self._error_response(
                "GitHub search unavailable. Please try again later or add a "
                "GitHub token for higher rate limits."
            )

    # ------------------------------------------------------------------
    # Public: repository details
    # ------------------------------------------------------------------

    def get_repository_details(self, repo_name: str) -> dict[str, Any]:
        """Fetch detailed information for a single repository.

        Args:
            repo_name: Full repository name in ``owner/repo`` format.

        Returns:
            Repository detail dict, or an error dict on failure.
        """
        logger.info("📊 Fetching details for: %s", repo_name)

        cache_key = f"repo_details:{repo_name}"
        cached = self.cache_manager.get(cache_key)
        if cached:
            logger.info("✅ Cache hit for repo: %s", repo_name)
            return cached  # type: ignore[return-value]

        try:
            result: dict[str, Any] = self.retry_manager.execute_with_retry(
                self._get_details_api, repo_name
            )
            self.cache_manager.set(cache_key, result)
            return result

        except GitHubAPIError as exc:
            logger.error("❌ Failed to fetch details for %s: %s", repo_name, exc)
            return self._error_response(str(exc))

        except Exception as exc:
            logger.error("❌ Unexpected error fetching %s: %s", repo_name, exc)
            return self._error_response(
                f"Unable to fetch details for '{repo_name}'. "
                "Repository might not exist or API is unavailable."
            )

    # ------------------------------------------------------------------
    # Public: new advanced analysis tools
    # ------------------------------------------------------------------

    def get_readme(self, repo_name: str) -> str:
        """Fetch and decode the README for a repository.
        
        Args:
            repo_name: Full repository name in ``owner/repo`` format.
            
        Returns:
            The decoded README content (truncated to 4000 chars to save LLM context).
        """
        logger.info("📄 Fetching README for: %s", repo_name)
        cache_key = f"readme:{repo_name}"
        cached = self.cache_manager.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        try:
            content: str = self.retry_manager.execute_with_retry(self._get_readme_api, repo_name)
            self.cache_manager.set(cache_key, content)
            return content
        except Exception as exc:
            logger.error("❌ Failed to fetch README for %s: %s", repo_name, exc)
            return f"Error fetching README: {exc}"

    def get_recent_commits(self, repo_name: str, count: int = 5) -> str:
        """Fetch the most recent commits for a repository.
        
        Args:
            repo_name: Full repository name in ``owner/repo`` format.
            count: Number of commits to fetch (max 20).
            
        Returns:
            Formatted string of recent commits.
        """
        count = max(1, min(int(count), 20))
        logger.info("🔄 Fetching %d recent commits for: %s", count, repo_name)
        cache_key = f"commits:{repo_name}:{count}"
        cached = self.cache_manager.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        try:
            formatted_commits: str = self.retry_manager.execute_with_retry(
                self._get_commits_api, repo_name, count
            )
            self.cache_manager.set(cache_key, formatted_commits)
            return formatted_commits
        except Exception as exc:
            logger.error("❌ Failed to fetch commits for %s: %s", repo_name, exc)
            return f"Error fetching commits: {exc}"

    def get_open_issues(self, repo_name: str, count: int = 5) -> str:
        """Fetch the most recent open issues for a repository.
        
        Args:
            repo_name: Full repository name in ``owner/repo`` format.
            count: Number of issues to fetch (max 20).
            
        Returns:
            Formatted string of recent open issues.
        """
        count = max(1, min(int(count), 20))
        logger.info("🐛 Fetching %d open issues for: %s", count, repo_name)
        cache_key = f"issues:{repo_name}:{count}"
        cached = self.cache_manager.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        try:
            formatted_issues: str = self.retry_manager.execute_with_retry(
                self._get_issues_api, repo_name, count
            )
            self.cache_manager.set(cache_key, formatted_issues)
            return formatted_issues
        except Exception as exc:
            logger.error("❌ Failed to fetch issues for %s: %s", repo_name, exc)
            return f"Error fetching issues: {exc}"

    # ------------------------------------------------------------------
    # Internal: API calls
    # ------------------------------------------------------------------

    def _search_api(self, query: str, max_results: int) -> list[dict[str, Any]]:
        """Call the GitHub search/repositories endpoint.

        Args:
            query:       Search query string.
            max_results: Maximum items to return.

        Returns:
            List of normalised repository dicts.

        Raises:
            GitHubAPIError: For non-2xx responses.
        """
        url = f"{self.base_url}/search/repositories"
        params: dict[str, Any] = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": max_results,
        }

        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        self.detector.raise_for_api_error(response)

        items: list[dict] = response.json().get("items", [])[:max_results]
        repositories = [self._normalise_item(item) for item in items]

        logger.debug("✅ Found %d repositories.", len(repositories))
        return repositories

    def _get_details_api(self, repo_name: str) -> dict[str, Any]:
        """Call the GitHub repos/{owner}/{repo} endpoint.

        Args:
            repo_name: Full ``owner/repo`` identifier.

        Returns:
            Normalised repository detail dict.

        Raises:
            GitHubAPIError: For non-2xx responses.
        """
        url = f"{self.base_url}/repos/{repo_name}"
        response = requests.get(url, headers=self.headers, timeout=10)
        self.detector.raise_for_api_error(response)

        data: dict = response.json()
        details: dict[str, Any] = {
            "name": data.get("full_name"),
            "description": data.get("description") or "No description",
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "language": data.get("language") or "Unknown",
            "license": (data["license"]["name"] if data.get("license") else "No license"),
            "topics": data.get("topics", []),
            "created_at": data.get("created_at", "Unknown"),
            "updated_at": data.get("updated_at", "Unknown"),
            "url": data.get("html_url"),
        }

        logger.info("✅ Retrieved details for %s.", repo_name)
        return details

    def _get_readme_api(self, repo_name: str) -> str:
        """Call the GitHub repos/{owner}/{repo}/readme endpoint."""
        url = f"{self.base_url}/repos/{repo_name}/readme"
        response = requests.get(url, headers=self.headers, timeout=10)
        self.detector.raise_for_api_error(response)

        data = response.json()
        encoded_content = data.get("content", "")
        if not encoded_content:
            return "README is empty or missing."

        decoded_bytes = base64.b64decode(encoded_content)
        decoded_str = decoded_bytes.decode("utf-8", errors="replace")
        
        # Truncate to save LLM context window limits
        max_len = 4000
        if len(decoded_str) > max_len:
            return decoded_str[:max_len] + "\n\n...[README TRUNCATED]..."
        return decoded_str

    def _get_commits_api(self, repo_name: str, count: int) -> str:
        """Call the GitHub repos/{owner}/{repo}/commits endpoint."""
        url = f"{self.base_url}/repos/{repo_name}/commits"
        params = {"per_page": count}
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        self.detector.raise_for_api_error(response)

        commits = response.json()
        if not commits:
            return "No recent commits found."

        formatted = []
        for c in commits:
            commit_data = c.get("commit", {})
            message = commit_data.get("message", "No message").split("\n")[0]  # Just first line
            author = commit_data.get("author", {}).get("name", "Unknown")
            date = commit_data.get("author", {}).get("date", "Unknown")[:10]
            formatted.append(f"- [{date}] {author}: {message}")

        return "\n".join(formatted)

    def _get_issues_api(self, repo_name: str, count: int) -> str:
        """Call the GitHub repos/{owner}/{repo}/issues endpoint."""
        url = f"{self.base_url}/repos/{repo_name}/issues"
        params = {"state": "open", "sort": "created", "direction": "desc", "per_page": count}
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        self.detector.raise_for_api_error(response)

        issues = response.json()
        # GitHub API returns PRs as issues too, we can filter them out or keep them. 
        # We will keep them but note them if needed.
        if not issues:
            return "No open issues found."

        formatted = []
        for i in issues:
            title = i.get("title", "No title")
            user = i.get("user", {}).get("login", "Unknown")
            is_pr = "pull_request" in i
            type_lbl = "[PR]" if is_pr else "[Issue]"
            formatted.append(f"- {type_lbl} {title} (by {user})")

        return "\n".join(formatted)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_max_results(query: str, max_results: int | None) -> int:
        """Determine the effective result count.

        Args:
            query:       Raw query string from the user.
            max_results: Explicit override (may be ``None``).

        Returns:
            Validated integer in the range [1, 20].
        """
        if max_results is None:
            numbers = re.findall(r"\b(\d+)\b", query)
            if numbers:
                max_results = int(numbers[0])
                logger.info("📊 Auto-detected result count from query: %d", max_results)
            else:
                max_results = 10
        return max(1, min(max_results, 20))

    @staticmethod
    def _normalise_item(item: dict) -> dict[str, Any]:
        """Convert a raw API search item into a normalised repository dict.

        Args:
            item: Single element from the GitHub search ``items`` array.

        Returns:
            Normalised dict with consistent keys.
        """
        return {
            "name": item.get("full_name"),
            "description": item.get("description") or "No description",
            "stars": item.get("stargazers_count", 0),
            "forks": item.get("forks_count", 0),
            "language": item.get("language") or "Unknown",
            "url": item.get("html_url"),
            "topics": item.get("topics", []),
            "last_updated": item.get("updated_at", "Unknown"),
            "license": (
                item["license"]["name"] if item.get("license") else "No license"
            ),
        }

    @staticmethod
    def _error_response(message: str) -> list:  # type: ignore[return]
        """Build a sentinel error payload that callers can detect.

        Args:
            message: Human-readable description of the failure.

        Returns:
            A list containing a single error dict.
        """
        return [{"error": True, "message": message, "repositories": []}]