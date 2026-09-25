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
    """Agente LLM -- avalia fidelidade e qualidade semântica da transformação.

    Diferente do ExtractSupervisor (determinístico e genérico), aqui não há uma
    lógica de checagem reutilizável entre projetos: o julgamento é semântico e
    depende da fonte/transformação específica. Cada projeto implementa seu
    próprio prompt de avaliação; a interface é fixa para que o Harness (Task 3)
    possa tratar qualquer TransformSupervisor de forma uniforme.
    """

    @abstractmethod
    def review(
        self, bronze: BronzeRecord, silver: SilverRecord
    ) -> SupervisorVerdict: ...
