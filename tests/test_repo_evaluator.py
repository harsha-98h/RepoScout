"""
Pytest suite for RepoEvaluator.
"""

from __future__ import annotations

import pytest

from tools.repo_evaluator import RepoEvaluator


@pytest.fixture()
def evaluator() -> RepoEvaluator:
    return RepoEvaluator()


def _make_repo(**overrides) -> dict:
    base = {
        "name": "owner/repo",
        "stars": 0,
        "forks": 0,
        "license": "No license",
        "description": "No description",
        "topics": [],
        "language": "Unknown",
    }
    base.update(overrides)
    return base


class TestEvaluateQuality:
    def test_empty_repo_scores_zero(self, evaluator: RepoEvaluator) -> None:
        assert evaluator.evaluate_quality(_make_repo()) == 0

    def test_high_stars_scores_40(self, evaluator: RepoEvaluator) -> None:
        score = evaluator.evaluate_quality(_make_repo(stars=20_000))
        assert score >= 40

    def test_max_score_capped_at_100(self, evaluator: RepoEvaluator) -> None:
        repo = _make_repo(
            stars=50_000,
            forks=5_000,
            license="MIT",
            description="Great repo",
            topics=["ai", "ml"],
            language="Python",
        )
        assert evaluator.evaluate_quality(repo) <= 100

    def test_license_adds_10_points(self, evaluator: RepoEvaluator) -> None:
        without = evaluator.evaluate_quality(_make_repo(stars=1_000))
        with_license = evaluator.evaluate_quality(_make_repo(stars=1_000, license="MIT"))
        assert with_license - without == 10

    def test_description_adds_10_points(self, evaluator: RepoEvaluator) -> None:
        without = evaluator.evaluate_quality(_make_repo(stars=1_000))
        with_desc = evaluator.evaluate_quality(
            _make_repo(stars=1_000, description="Useful library")
        )
        assert with_desc - without == 10


class TestFilterQualityRepos:
    def test_filters_below_min_score(self, evaluator: RepoEvaluator) -> None:
        repos = [_make_repo(), _make_repo(stars=50_000, forks=5_000, license="MIT", description="x", topics=["a"], language="Python")]
        filtered = evaluator.filter_quality_repos(repos, min_score=40)
        assert len(filtered) == 1

    def test_sorted_descending(self, evaluator: RepoEvaluator) -> None:
        repos = [
            _make_repo(stars=500),
            _make_repo(stars=50_000, forks=5_000, license="MIT", description="Great", topics=["ai"], language="Python"),
        ]
        filtered = evaluator.filter_quality_repos(repos, min_score=0)
        assert filtered[0]["quality_score"] >= filtered[-1]["quality_score"]


class TestExplainWhyUseful:
    def test_includes_stars(self, evaluator: RepoEvaluator) -> None:
        explanation = evaluator.explain_why_useful(_make_repo(stars=15_000))
        assert "15,000" in explanation

    def test_falls_back_to_active(self, evaluator: RepoEvaluator) -> None:
        explanation = evaluator.explain_why_useful(_make_repo())
        assert "Active" in explanation
