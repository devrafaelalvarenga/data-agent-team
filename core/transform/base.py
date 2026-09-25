"""Transform: processa/transforma o dado bruto (specialist, pode envolver LLM) e
avalia fidelidade/qualidade semântica antes de liberar para Silver (supervisor, LLM).
Ver docs/ARCHITECTURE.md, seção "As 4 Tasks".
"""

from abc import ABC, abstractmethod

from core.contracts import BronzeRecord, SilverRecord, SupervisorVerdict


class TransformSpecialist(ABC):
    """Cada projeto implementa a lógica de transformação (pode envolver LLM)."""

    @abstractmethod
    def transform(self, record: BronzeRecord) -> SilverRecord: ...


class TransformSupervisor(ABC):
    """Tipicamente um agente LLM -- avalia fidelidade e qualidade semântica da
    transformação, quando há julgamento semântico real a fazer (ex.: decidir
    o que é ruído de PDF vs. conteúdo normativo). A regra não-negociável do
    framework é "LLM só onde há julgamento semântico real" -- se uma fonte
    específica não tem ambiguidade nenhuma para resolver (ex.: dado tabular
    já tipado, sem texto livre), o projeto pode implementar este supervisor
    de forma 100% determinística (ver
    `projects/ai-energy-data-project/transform_impl.py`,
    `AneelTabularTransformSupervisor`) -- a interface continua a mesma para
    que o Harness (Task 3) trate qualquer TransformSupervisor de forma
    uniforme, LLM ou não.

    Diferente do ExtractSupervisor, não há uma lógica de checagem genérica
    reutilizável entre projetos aqui: cada projeto implementa a lógica (via
    prompt de LLM ou checagem determinística) de acordo com o que a fonte
    realmente precisa.
    """

    @abstractmethod
    def review(
        self, bronze: BronzeRecord, silver: SilverRecord
    ) -> SupervisorVerdict: ...
