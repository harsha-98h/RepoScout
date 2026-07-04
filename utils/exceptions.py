"""
Custom exception hierarchy for RepoScout Agent.

Replace broad ``except Exception`` blocks with these specific types
so that genuine programming errors are not silently swallowed.
"""


class RepoScoutError(Exception):
    """Base exception for all RepoScout errors."""


# ---------------------------------------------------------------------------
# GitHub API Exceptions
# ---------------------------------------------------------------------------


class GitHubAPIError(RepoScoutError):
    """Raised when the GitHub API returns an unexpected response."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitExceeded(GitHubAPIError):
    """Raised when the GitHub API rate limit has been reached."""

    def __init__(self, wait_seconds: int = 3600) -> None:
        super().__init__(
            f"GitHub API rate limit exceeded. Please add a GitHub token or wait "
            f"{wait_seconds} seconds.",
            status_code=403,
        )
        self.wait_seconds = wait_seconds


class RepositoryNotFound(GitHubAPIError):
    """Raised when the requested repository does not exist."""

    def __init__(self, repo_name: str) -> None:
        super().__init__(f"Repository '{repo_name}' not found.", status_code=404)
        self.repo_name = repo_name


class InvalidSearchQuery(GitHubAPIError):
    """Raised when GitHub rejects a search query as invalid (HTTP 422)."""

    def __init__(self, query: str) -> None:
        super().__init__(
            f"Search query is invalid: '{query}'. Try different keywords.",
            status_code=422,
        )
        self.query = query


# ---------------------------------------------------------------------------
# Network Exceptions
# ---------------------------------------------------------------------------


class NetworkError(RepoScoutError):
    """Raised for connection / timeout failures."""


class RequestTimeoutError(NetworkError):
    """Raised when a request to the GitHub API times out."""


class ConnectionFailedError(NetworkError):
    """Raised when cannot reach GitHub at all."""


# ---------------------------------------------------------------------------
# Agent / Tool Exceptions
# ---------------------------------------------------------------------------


class ToolNotFoundError(RepoScoutError):
    """Raised when the LLM requests a tool that is not registered."""

    def __init__(self, tool_name: str, available: list[str]) -> None:
        super().__init__(
            f"Tool '{tool_name}' not found. Available tools: {', '.join(available)}"
        )
        self.tool_name = tool_name
        self.available = available


class ToolExecutionError(RepoScoutError):
    """Raised when a registered tool raises an unexpected error."""

    def __init__(self, tool_name: str, cause: Exception) -> None:
        super().__init__(f"Error executing tool '{tool_name}': {cause}")
        self.tool_name = tool_name
        self.cause = cause


class MaxIterationsExceeded(RepoScoutError):
    """Raised when the ReAct loop exhausts its maximum iteration budget."""


class PromptInjectionDetected(RepoScoutError):
    """Raised when suspicious content is detected in user input."""
