"""
Domain models for RepoScout.

Using :mod:`dataclasses` for structured, type-safe data instead of
plain dictionaries, which eliminates key-error bugs and improves IDE
auto-completion throughout the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Repository:
    """Represents a single GitHub repository returned by search."""

    name: str
    description: str = "No description"
    stars: int = 0
    forks: int = 0
    language: str = "Unknown"
    url: str = ""
    topics: list[str] = field(default_factory=list)
    last_updated: str = "Unknown"
    license: str = "No license"
    open_issues: int = 0
    created_at: str = "Unknown"
    quality_score: int = 0

    @classmethod
    def from_api_item(cls, item: dict) -> "Repository":
        """Construct a :class:`Repository` from a raw GitHub API search item."""
        return cls(
            name=item.get("full_name", ""),
            description=item.get("description") or "No description",
            stars=item.get("stargazers_count", 0),
            forks=item.get("forks_count", 0),
            language=item.get("language") or "Unknown",
            url=item.get("html_url", ""),
            topics=item.get("topics", []),
            last_updated=item.get("updated_at", "Unknown"),
            license=(
                item["license"]["name"]
                if item.get("license")
                else "No license"
            ),
        )

    @classmethod
    def from_api_detail(cls, data: dict) -> "Repository":
        """Construct a :class:`Repository` from a raw GitHub API detail response."""
        return cls(
            name=data.get("full_name", ""),
            description=data.get("description") or "No description",
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            language=data.get("language") or "Unknown",
            url=data.get("html_url", ""),
            topics=data.get("topics", []),
            last_updated=data.get("updated_at", "Unknown"),
            license=(
                data["license"]["name"]
                if data.get("license")
                else "No license"
            ),
            open_issues=data.get("open_issues_count", 0),
            created_at=data.get("created_at", "Unknown"),
        )


@dataclass
class SearchResult:
    """Wraps the outcome of a GitHub repository search."""

    repositories: list[Repository] = field(default_factory=list)
    query: str = ""
    total_count: int = 0
    error: bool = False
    message: str = ""
