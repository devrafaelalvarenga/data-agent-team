"""Harness (Task 3): amostra a população de silver records e roda métricas
configuráveis para calcular a nota que decide o destino na Task 4.
Ver docs/ARCHITECTURE.md, seção "As 4 Tasks".
"""

import random
from collections.abc import Callable

from core.contracts import EvalResult, SilverRecord


class Harness:
    """Genérico -- recebe métricas configuráveis via config.yaml e amostra a
    população de silver records recebida, usando sample_size/sample_strategy
    do config (não avalia a população inteira -- decisão explícita de
    custo/performance).
    """

    def __init__(
        self,
        metrics: dict[str, Callable[[list[SilverRecord]], float]],
        threshold: float,
        sample_size: int,
        sample_strategy: str = "random",
    ):
        self.metrics = metrics
        self.threshold = threshold
        self.sample_size = sample_size
        self.sample_strategy = sample_strategy

    def _sample(self, population: list[SilverRecord]) -> list[SilverRecord]:
        if len(population) <= self.sample_size:
            return population
        if self.sample_strategy == "random":
            return random.sample(population, self.sample_size)
        raise NotImplementedError(
            f"Estratégia de amostragem '{self.sample_strategy}' não implementada"
        )

    def evaluate(self, population: list[SilverRecord]) -> EvalResult:
        sample = self._sample(population)
        breakdown = {name: fn(sample) for name, fn in self.metrics.items()}
        final_score = sum(breakdown.values()) / len(breakdown)
        return EvalResult(
            score=final_score, passed=final_score >= self.threshold, breakdown=breakdown
        )
