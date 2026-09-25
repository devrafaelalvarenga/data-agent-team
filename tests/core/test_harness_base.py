from unittest.mock import patch

import pytest

from core.contracts import EvalResult, SilverRecord
from core.harness.base import Harness


def _population(n: int) -> list[SilverRecord]:
    return [SilverRecord() for _ in range(n)]


def test_sample_returns_population_unchanged_when_smaller_than_sample_size():
    harness = Harness(metrics={}, threshold=0.5, sample_size=10)
    population = _population(3)
    assert harness._sample(population) == population


def test_sample_returns_population_unchanged_when_equal_to_sample_size():
    harness = Harness(metrics={}, threshold=0.5, sample_size=3)
    population = _population(3)
    assert harness._sample(population) == population


def test_sample_random_returns_subset_of_requested_size():
    harness = Harness(
        metrics={}, threshold=0.5, sample_size=2, sample_strategy="random"
    )
    population = _population(5)

    with patch(
        "core.harness.base.random.sample", return_value=population[:2]
    ) as mocked_sample:
        result = harness._sample(population)

    mocked_sample.assert_called_once_with(population, 2)
    assert result == population[:2]


def test_sample_raises_for_unknown_strategy():
    harness = Harness(
        metrics={}, threshold=0.5, sample_size=2, sample_strategy="stratified"
    )
    with pytest.raises(NotImplementedError, match="stratified"):
        harness._sample(_population(5))


def test_evaluate_averages_metric_breakdown_and_passes_threshold():
    harness = Harness(
        metrics={
            "metric_a": lambda sample: 1.0,
            "metric_b": lambda sample: 0.6,
        },
        threshold=0.7,
        sample_size=10,
    )
    result = harness.evaluate(_population(2))

    assert result == EvalResult(
        score=0.8, passed=True, breakdown={"metric_a": 1.0, "metric_b": 0.6}
    )


def test_evaluate_fails_below_threshold():
    harness = Harness(
        metrics={"metric_a": lambda sample: 0.4},
        threshold=0.5,
        sample_size=10,
    )
    result = harness.evaluate(_population(1))

    assert not result.passed
    assert result.score == 0.4


def test_evaluate_runs_metrics_against_the_sample_not_full_population():
    seen_sample_sizes = []
    harness = Harness(
        metrics={"metric": lambda sample: seen_sample_sizes.append(len(sample)) or 1.0},
        threshold=0.5,
        sample_size=2,
    )

    with patch("core.harness.base.random.sample", side_effect=lambda pop, k: pop[:k]):
        harness.evaluate(_population(10))

    assert seen_sample_sizes == [2]
