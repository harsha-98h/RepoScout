"""
RepoScout - GitHub Repository Discovery Agent
Main entry point with flexible result counts.
"""

from __future__ import annotations

import re
import sys

import config
from agent.reposcout_agent import RepoScoutAgent
from tools.github_search import GitHubSearchTool
from tools.repo_evaluator import RepoEvaluator
from utils.exceptions import PromptInjectionDetected
from utils.logger import setup_logger
from utils.sanitizer import sanitize_query

logger = setup_logger("main")


def format_repositories_for_llm(repositories: list, max_show: int = 10) -> str:
    """Format repository data for LLM observation.

    Args:
        repositories: List of repository dicts (or error dict).
        max_show:     Maximum number to display.

    Returns:
        Formatted string ready for the LLM context window.
    """
    if not repositories:
        return "No repositories found."

    # Single-item error payload returned by GitHubSearchTool
    if (
        isinstance(repositories, list)
        and len(repositories) == 1
        and isinstance(repositories[0], dict)
        and repositories[0].get("error")
    ):
        return repositories[0].get("message", "Error occurred during search.")

    evaluator = RepoEvaluator()
    quality_repos = evaluator.filter_quality_repos(repositories, min_score=40)

    if not quality_repos:
        return "No high-quality repositories found matching your criteria."

    repos_to_show = quality_repos[:max_show]
    logger.debug(
        "📊 Displaying %d repositories (from %d total).",
        len(repos_to_show),
        len(repositories),
    )

    formatted = [
        (
            f"Repository: {repo['name']}\n"
            f"Description: {repo['description']}\n"
            f"Stars: {repo['stars']:,}\n"
            f"Language: {repo['language']}\n"
            f"URL: {repo['url']}\n"
            f"Quality Score: {repo['quality_score']}/100\n"
            f"Why useful: {evaluator.explain_why_useful(repo)}"
        )
        for repo in repos_to_show
    ]
    return "\n\n".join(formatted)


def main() -> None:
    """Initialise and run the RepoScout interactive loop."""
    print("=" * 60)
    print(f"🔍 {config.AGENT_NAME} - GitHub Repository Discovery Agent")
    print("=" * 60)

    if not config.OPENAI_API_KEY:
        print(
            "❌  OPENAI_API_KEY not found in .env! "
            "Please add it before running RepoScout."
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # Initialise agent and tools
    # ------------------------------------------------------------------
    print("🔧 Initialising agent…")
    agent = RepoScoutAgent()
    github_tool = GitHubSearchTool()

    def search_github_wrapper(query: str) -> str:
        """Wrapper that detects the requested result count from the query."""
        numbers = re.findall(r"\b(\d+)\b", query)
        max_results = min(max(int(numbers[0]), 10), 20) if numbers else 10
        logger.debug("🎯 Requested %d results.", max_results)
        repos = github_tool.search_repositories(query, max_results=max_results)
        return format_repositories_for_llm(repos, max_show=max_results)

    agent.register_tool(
        "search_github",
        search_github_wrapper,
        "Search GitHub repositories. Supports count in query like 'Find 10 repos' "
        "(default 10, max 20).",
    )
    agent.register_tool(
        "get_repo_details",
        github_tool.get_repository_details,
        "Get detailed information about a specific repository (format: owner/repo).",
    )
    agent.register_tool(
        "read_readme",
        github_tool.get_readme,
        "Read the README.md file of a repository to understand what it does and how to use it (format: owner/repo).",
    )
    agent.register_tool(
        "analyze_commits",
        lambda repo: github_tool.get_recent_commits(repo.strip(), 5),
        "Get the 5 most recent commits for a repository to see active development (format: owner/repo).",
    )
    agent.register_tool(
        "read_issues",
        lambda repo: github_tool.get_open_issues(repo.strip(), 5),
        "Get the 5 most recent open issues/PRs for a repository to see bugs or features being worked on (format: owner/repo).",
    )

    logger.info("✅ Agent ready.")
    logger.info("=" * 60)
    logger.info("Ask me to find GitHub repositories!")
    logger.info("Type 'quit' to exit, 'trace' to see reasoning.")
    logger.info("=" * 60)
    logger.info("Example queries:")
    logger.info("  • Find 10 AI agent repositories")
    logger.info("  • I want 15 Python machine learning projects")
    logger.info("  • Show me 5 web development frameworks")

    # ------------------------------------------------------------------
    # Interactive loop
    # ------------------------------------------------------------------
    while True:
        try:
            question = input("\n🔍 What are you looking for? ").strip()
        except (EOFError, KeyboardInterrupt):
            logger.info("\n👋 Goodbye!")
            break

        if not question:
            continue

        if question.lower() in {"quit", "exit", "q"}:
            logger.info("👋 Goodbye!")
            break

        if question.lower() == "trace":
            agent.print_trace()
            continue

        # Sanitize before sending to the LLM
        try:
            question = sanitize_query(question)
        except PromptInjectionDetected as exc:
            logger.warning("🛡️  %s", exc)
            continue
        except ValueError as exc:
            logger.warning("⚠️  %s", exc)
            continue

        try:
            answer = agent.search(question)
            logger.info("=" * 60)
            logger.info(answer)
            logger.info("=" * 60)
        except Exception as exc:
            logger.error("❌ Error processing query: %s", exc)
            logger.info("Please try again or check your API key.")


if __name__ == "__main__":
    main()