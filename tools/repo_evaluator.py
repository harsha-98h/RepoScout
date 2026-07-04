"""
Repository Quality Evaluator.

Evaluates and ranks :class:`models.Repository` objects (or legacy dicts)
using a weighted scoring system, and provides human-readable explanations.
"""

from __future__ import annotations

from utils.logger import setup_logger

logger = setup_logger(__name__)


class RepoEvaluator:
    """Evaluate repository quality based on quantitative GitHub signals."""

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def evaluate_quality(self, repo: dict) -> int:
        """Return a 0–100 quality score for *repo*.

        Scoring breakdown:
          - Stars  (max 40 pts)
          - Forks  (max 20 pts)
          - License       10 pts
          - Description   10 pts
          - Topics        10 pts
          - Language      10 pts

        Args:
            repo: Repository data dictionary (keys: ``stars``, ``forks``,
                  ``license``, ``description``, ``topics``, ``language``).

        Returns:
            Integer quality score capped at 100.
        """
        score = 0

        # Stars (max 40 pts)
        stars: int = repo.get("stars", 0)
        if stars >= 10_000:
            score += 40
        elif stars >= 5_000:
            score += 35
        elif stars >= 1_000:
            score += 30
        elif stars >= 500:
            score += 20
        elif stars >= 100:
            score += 10

        # Forks (max 20 pts)
        forks: int = repo.get("forks", 0)
        if forks >= 1_000:
            score += 20
        elif forks >= 500:
            score += 15
        elif forks >= 100:
            score += 10
        elif forks >= 50:
            score += 5

        # License (10 pts)
        if repo.get("license") and repo["license"] != "No license":
            score += 10

        # Description (10 pts)
        description: str = repo.get("description", "")
        if description and description != "No description":
            score += 10

        # Topics (10 pts)
        if len(repo.get("topics", [])) > 0:
            score += 10

        # Language (10 pts)
        if repo.get("language") and repo["language"] != "Unknown":
            score += 10

        return min(score, 100)

    def filter_quality_repos(
        self, repositories: list[dict], min_score: int = 50
    ) -> list[dict]:
        """Score, filter, and sort *repositories* by quality.

        Args:
            repositories: List of repository data dicts.
            min_score:    Minimum score threshold (0–100, default 50).

        Returns:
            Filtered list of dicts sorted by ``quality_score`` descending.
        """
        for repo in repositories:
            repo["quality_score"] = self.evaluate_quality(repo)

        filtered = [r for r in repositories if r["quality_score"] >= min_score]
        filtered.sort(key=lambda r: r["quality_score"], reverse=True)

        logger.debug("📊 Filtered to %d high-quality repositories.", len(filtered))
        return filtered

    # ------------------------------------------------------------------
    # Explanation
    # ------------------------------------------------------------------

    def explain_why_useful(self, repo: dict) -> str:
        """Generate a one-line explanation of why *repo* is worth using.

        Args:
            repo: Repository data dict.

        Returns:
            Human-readable explanation string.
        """
        reasons: list[str] = []

        stars: int = repo.get("stars", 0)
        if stars >= 10_000:
            reasons.append(f"Very popular with {stars:,}+ stars")
        elif stars >= 1_000:
            reasons.append(f"Popular with {stars:,}+ stars")

        license_name: str = repo.get("license", "No license")
        if license_name and license_name != "No license":
            reasons.append(f"Open source ({license_name})")

        language: str = repo.get("language", "Unknown")
        if language and language != "Unknown":
            reasons.append(f"Written in {language}")

        topics: list[str] = repo.get("topics", [])
        if topics:
            reasons.append(f"Topics: {', '.join(topics[:3])}")

        return (". ".join(reasons) + ".") if reasons else "Active repository."