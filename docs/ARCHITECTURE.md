# Arquitetura: Time de Agentes de Engenharia de Dados

## Visão geral

Um framework reutilizável de agentes especializados para pipelines de dados, estruturado em camadas medallion (bronze/silver/gold), onde cada etapa do ETL tem um **agente especialista** (executa a tarefa) e um **agente/checagem supervisor** (valida o resultado antes de liberar a próxima etapa).

O framework é separado em duas camadas:
- **`core/`** — genérico, reutilizável entre qualquer projeto de dados
- **`projects/`** — implementações específicas de cada caso de uso (o primeiro é `ai-energy-data-project`)

> Objetivo estratégico: o projeto de energia (PRODIST + DRP/DRC + DEC/FEC) é a **primeira aplicação** dessa plataforma, não o produto final. O framework deve funcionar para qualquer pipeline de dados futuro.

## Princípio de design não-negociável: LLM só onde há julgamento real

Nem toda etapa do pipeline deve ser um agente LLM. Chamadas de LLM têm custo, latência (~950ms de overhead de coordenação por agente) e risco de erro não-determinístico. A regra:

- **Python determinístico**: tarefas com critério objetivo e verificável (schema, contagem, completude, threshold numérico)
- **Agente LLM**: tarefas que exigem julgamento semântico (fidelidade de um chunk à fonte, qualidade de uma extração estruturada a partir de texto livre)

Essa distinção é aplicada explicitamente em cada uma das 4 tasks abaixo — não é opcional, é regra de arquitetura.

## As 4 Tasks

| Task | Especialista | Supervisor | LLM? | Camada de saída |
|---|---|---|---|---|
| **1 — Extract** | Lê dados brutos da fonte (API, CSV, PDF) | Valida schema, contagem de linhas, completude, checksum | ❌ Não — determinístico | Bronze |
| **2 — Transform** | Processa/transforma dado bruto (ex: chunking semântico, extração estruturada de texto) | Avalia fidelidade e qualidade da transformação (a fonte foi respeitada? nada foi alucinado?) | ✅ Sim | Silver |
| **3 — Harness** | Amostra o output da Task 2, roda métricas de eval configuradas, calcula nota final | — (a própria task já é o mecanismo de verificação) | Parcial — métricas determinísticas + 1 métrica de LLM-as-judge (fidelidade semântica) | — (decide destino) |
| **4 — Load** | Se nota do Harness ≥ threshold → grava em Gold. Se não → grava em tabela de Auditoria | Checagem do threshold (comparação numérica) | ❌ Não — determinístico | Gold ou Auditoria |

## Fluxo de dados

```
[Fonte de dados]
       │
       ▼
Task 1 — Extract (especialista)
       │
       ▼
Supervisor 1 (determinístico: schema, completude, checksum)
       │  aprovado?
       ▼
   BRONZE
       │
       ▼
Task 2 — Transform (especialista LLM)
       │
       ▼
Supervisor 2 (agente LLM: fidelidade à fonte, qualidade da extração)
       │  aprovado?
       ▼
   SILVER
       │
       ▼
Task 3 — Harness (amostra + métricas + nota final)
       │
       ├── nota ≥ threshold ──► Task 4 — Load ──► GOLD
       │
       └── nota < threshold ──► Task 4 — Load ──► AUDITORIA (tabela de rejeitados)
```

## Estrutura de pastas

```
data-agent-team/
├── core/                              # FRAMEWORK — reutilizável entre projetos
│   ├── contracts.py                   # BronzeRecord, SilverRecord, EvalResult, SupervisorVerdict, AuditRecord
│   ├── registry.py                    # resolve nomes do config.yaml em métricas/providers reais
│   ├── extract/
│   │   └── base.py                    # ExtractSpecialist (ABC) + ExtractSupervisor (genérico, configurável)
│   ├── transform/
│   │   └── base.py                    # TransformSpecialist (ABC) + TransformSupervisor (ABC, LLM)
│   ├── harness/
│   │   ├── base.py                    # Harness genérico: recebe métricas configuráveis
│   │   └── metrics.py                 # implementações de métrica, registradas via @register_metric
│   ├── load/
│   │   └── base.py                    # LoadGate: genérico, gera AuditRecord automaticamente
│   └── orchestration/
│       └── dag_factory.py             # lê config.yaml, resolve registry, gera DAG do Airflow
│
├── projects/                          # ESPECÍFICO de cada caso de uso
│   └── ai-energy-data-project/
│       ├── config.yaml                # thresholds, fontes, métricas escolhidas
│       ├── extract_impl.py            # implementa ExtractSpecialist p/ ANEEL/PRODIST
│       ├── transform_impl.py          # implementa TransformSpecialist (chunking LLM do PRODIST)
│       └── docs/
│           └── architecture.md        # decisões técnicas específicas deste projeto (chunking, thresholds)
│
├── tests/
│   ├── core/                          # testes do framework genérico
│   └── projects/
│       └── ai-energy-data-project/
│
├── docs/
│   └── ARCHITECTURE.md         # este documento (arquitetura do framework)
│
├── README.md                          # página inicial do repositório (GitHub)
├── CLAUDE.md                          # único, na raiz -- governa framework + todos os projetos
├── requirements.txt
├── .env.example
└── .gitignore
```

## Contratos principais (interfaces)

```python
# core/contracts.py
from dataclasses import dataclass, field
from typing import Any
import uuid


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class BronzeRecord:
    id: str = field(
        default_factory=_new_id
    )  # identificador próprio -- necessário para rastreabilidade
    source: str = ""
    raw_content: Any = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SilverRecord:
    id: str = field(
        default_factory=_new_id
    )  # identificador próprio do silver (distinto do bronze_ref)
    bronze_ref: str = ""  # referência ao BronzeRecord.id de origem
    transformed_content: Any = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SupervisorVerdict:
    approved: bool
    details: list[str]


@dataclass
class EvalResult:
    score: float
    passed: bool
    breakdown: dict[str, float]


@dataclass
class AuditRecord:
    """O que é gravado na tabela de auditoria quando a Task 3 reprova um lote."""

    silver_ref: str  # referência ao SilverRecord.id que foi rejeitado
    reason: dict[str, float]  # breakdown do EvalResult que causou a reprovação
    rejected_at: str  # timestamp ISO 8601
    raw_content: Any  # conteúdo original, para permitir reprocessamento manual
    metadata: dict = field(default_factory=dict)
```

## Registry: resolvendo strings do config.yaml em código real

`config.yaml` referencia providers e métricas como **strings** (`llm_provider: google_ai_studio`, `metrics: [faithfulness_to_source, ...]`), mas o código precisa de **objetos/funções reais**. Sem um mecanismo explícito de resolução, essas strings viram "mágica" que só funciona se alguém souber, de cabeça, qual função cada nome corresponde — exatamente o tipo de acoplamento implícito que este framework existe para evitar.

Solução: um **registry central**, onde cada `core/` module expõe suas implementações disponíveis por nome, e o `dag_factory.py` faz a resolução na hora de montar o pipeline.

```python
# core/registry.py
from typing import Callable

METRIC_REGISTRY: dict[str, Callable] = {}
PROVIDER_REGISTRY: dict[str, Callable] = {}


def register_metric(name: str):
    """Decorator: registra uma função de métrica pelo nome usado no config.yaml."""

    def wrapper(fn: Callable) -> Callable:
        METRIC_REGISTRY[name] = fn
        return fn

    return wrapper


def register_provider(name: str):
    """Decorator: registra um client/factory de LLM provider pelo nome usado no config.yaml."""

    def wrapper(fn: Callable) -> Callable:
        PROVIDER_REGISTRY[name] = fn
        return fn

    return wrapper
```

```python
# core/harness/metrics.py (exemplo de uso do registry)
from core.registry import register_metric


@register_metric("faithfulness_to_source")
def faithfulness_to_source(sample: list) -> float: ...


@register_metric("chunk_size_valid")
def chunk_size_valid(sample: list) -> float: ...
```

O `dag_factory.py` (Task de orquestração) lê `config.yaml`, busca cada nome no `METRIC_REGISTRY`/`PROVIDER_REGISTRY`, e monta o `Harness` já com as funções reais resolvidas — o `config.yaml` nunca precisa saber onde a função vive, só o nome dela.

```python
# core/extract/base.py
from abc import ABC, abstractmethod
from core.contracts import BronzeRecord, SupervisorVerdict


class ExtractSpecialist(ABC):
    """Cada projeto implementa isso com sua lógica de extração específica."""

    @abstractmethod
    def extract(self) -> BronzeRecord: ...


class ExtractSupervisor:
    """
    Genérico -- a LÓGICA das checagens é a mesma em qualquer projeto,
    mas os LIMIARES vêm de config.yaml (cada fonte pode ter regras diferentes:
    'atualizado' significa algo distinto para um PDF normativo e para um CSV mensal).
    """

    def __init__(
        self,
        schema_rules: dict,
        completeness_min_ratio: float,
        freshness_max_hours: int,
    ):
        self.schema_rules = schema_rules
        self.completeness_min_ratio = completeness_min_ratio
        self.freshness_max_hours = freshness_max_hours

    def review(self, record: BronzeRecord) -> SupervisorVerdict:
        checks = {
            "schema_valido": self._check_schema(record),
            "completo": self._check_completeness(record),
            "atualizado": self._check_freshness(record),
        }
        return SupervisorVerdict(
            approved=all(checks.values()),
            details=[k for k, v in checks.items() if not v],
        )

    def _check_schema(self, record: BronzeRecord) -> bool: ...
    def _check_completeness(self, record: BronzeRecord) -> bool: ...
    def _check_freshness(self, record: BronzeRecord) -> bool: ...
```

```python
# core/transform/base.py
from abc import ABC, abstractmethod
from core.contracts import BronzeRecord, SilverRecord, SupervisorVerdict


class TransformSpecialist(ABC):
    """Cada projeto implementa a lógica de transformação (pode envolver LLM)."""

    @abstractmethod
    def transform(self, record: BronzeRecord) -> SilverRecord: ...


class TransformSupervisor(ABC):
    """
    Agente LLM -- avalia fidelidade e qualidade semântica da transformação.
    Cada projeto pode customizar o prompt de avaliação, mas a interface é fixa.
    """

    @abstractmethod
    def review(
        self, bronze: BronzeRecord, silver: SilverRecord
    ) -> SupervisorVerdict: ...
```

```python
# core/harness/base.py
import random
from typing import Callable
from core.contracts import SilverRecord, EvalResult


class Harness:
    """
    Genérico -- recebe métricas configuráveis via config.yaml e AMOSTRA a população
    de silver records recebida, usando sample_size/sample_strategy do config
    (não avalia a população inteira -- isso é decisão explícita de custo/performance).
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
```

```python
# core/load/base.py
from datetime import datetime, timezone
from core.contracts import EvalResult, SilverRecord, AuditRecord


class LoadGate:
    """100% genérico -- só decide o destino com base no resultado do Harness."""

    def __init__(self, gold_writer: Callable, audit_writer: Callable):
        self.gold_writer = gold_writer
        self.audit_writer = audit_writer

    def load(self, records: list[SilverRecord], eval_result: EvalResult) -> str:
        if eval_result.passed:
            self.gold_writer(records)
            return "gold"

        audit_records = [
            AuditRecord(
                silver_ref=r.id,
                reason=eval_result.breakdown,
                rejected_at=datetime.now(timezone.utc).isoformat(),
                raw_content=r.transformed_content,
                metadata=r.metadata,
            )
            for r in records
        ]
        self.audit_writer(audit_records)
        return "audit"
```

> **Nota sobre destinos heterogêneos:** `bronze_destination` varia por fonte porque a natureza do dado é diferente — o PDF do PRODIST é um blob (vai para Cloud Storage), enquanto os CSVs da ANEEL são tabulares (vão para BigQuery). Já `silver` tem **dois destinos simultâneos**: `silver_destination` (tabela estruturada no BigQuery, para auditoria/consulta SQL dos chunks) e `silver_vector_destination` (o mesmo conteúdo, embedado no Chroma, para retrieval semântico). Ambos representam o mesmo dado, em formatos diferentes, servindo propósitos diferentes — isso deve ficar explícito no `config.yaml`, nunca implícito no código do agente.

## Exemplo de config.yaml por projeto

```yaml
# projects/ai-energy-data-project/config.yaml
project_name: ai-energy-data-project

extract:
  sources:
    - prodist_pdf
    - aneel_drp_drc_csv
    - aneel_dec_fec_csv
  bronze_destination:
    prodist_pdf: gcs://ai-energy-data-bucket/bronze/prodist/
    aneel_drp_drc_csv: bigquery.energy_quality.bronze_drp_drc
    aneel_dec_fec_csv: bigquery.energy_quality.bronze_dec_fec
  # limiares do ExtractSupervisor -- diferentes por natureza de fonte
  supervisor:
    prodist_pdf:
      completeness_min_ratio: 1.0     # PDF normativo: ou baixou completo, ou reprova
      freshness_max_hours: 8760       # 1 ano -- PRODIST muda raramente
    aneel_drp_drc_csv:
      completeness_min_ratio: 0.95
      freshness_max_hours: 2160       # ~90 dias -- dado trimestral
    aneel_dec_fec_csv:
      completeness_min_ratio: 0.95
      freshness_max_hours: 8760       # dado anual

transform:
  chunking_strategy: por_secao_numerada
  llm_provider: google_ai_studio       # resolvido via PROVIDER_REGISTRY (core/registry.py)
  silver_destination: bigquery.energy_quality.silver_prodist_chunks
  # embeddings do silver alimentam o vector DB -- destino separado, pois não é tabular
  silver_vector_destination: chroma://local/prodist_chunks

harness:
  sample_size: 30              # nº de registros amostrados por execução
  sample_strategy: random       # random | stratified_by_section
  metrics:                      # cada nome resolvido via METRIC_REGISTRY (core/registry.py)
    - faithfulness_to_source
    - chunk_size_valid
    - metadata_extracted
  threshold: 0.8

load:
  gold_destination: bigquery.energy_quality.gold
  audit_destination: bigquery.energy_quality.audit
```

## Regras de implementação (para o Claude Code seguir)

1. **Nunca implementar Task 1 (Extract) ou Task 4 (Load) como agente LLM.** São determinísticas por design. Se surgir a tentação de usar LLM nessas etapas, é sinal de que o requisito não está bem definido — resolver isso com regra Python, não com prompt.
2. **Toda nova implementação de projeto vive em `projects/<nome>/`, nunca em `core/`.** O `core/` só muda quando um segundo projeto real expõe a necessidade de generalizar algo.
3. **Toda métrica do Harness deve ser testável isoladamente** (função pura que recebe uma amostra e retorna um score entre 0 e 1) **e registrada via `@register_metric`** — nunca referenciada por string sem estar no registry.
4. **O `config.yaml` é a fonte de verdade de thresholds e destinos** — nunca hardcode threshold, nome de tabela ou limiar de supervisor dentro do código dos agentes.
5. Existe **um único `CLAUDE.md`, na raiz de `data-agent-team/`**, que governa o framework inteiro e todos os projetos dentro de `projects/`. Não criar `CLAUDE.md` por projeto.
6. Seguir as regras já estabelecidas no `CLAUDE.md` raiz (custo zero GCP, testes obrigatórios em `core/` e nas implementações de projeto, documentação de decisões técnicas).

## Roadmap de implementação sugerido

1. `core/contracts.py` — definir os dataclasses (incluindo `AuditRecord`)
2. `core/registry.py` — mecanismo de registro de métricas e providers por nome
3. `core/extract/base.py` — especialista e supervisor genéricos de extração, com thresholds configuráveis
4. `projects/ai-energy-data-project/extract_impl.py` — implementar `ExtractSpecialist` do zero para as 3 fontes (PRODIST PDF, DRP/DRC CSV, DEC/FEC CSV) — nenhum código do Projeto 1 anterior é reaproveitado, pois foi descartado
5. `core/transform/base.py` — interfaces de transformação
6. `projects/ai-energy-data-project/transform_impl.py` — chunking semântico do PRODIST via LLM
7. `core/harness/base.py` + `core/harness/metrics.py` — métricas iniciais registradas (faithfulness, chunk_size_valid, metadata_extracted)
8. `core/load/base.py` — gate de carga gold/auditoria, gerando `AuditRecord`
9. `core/orchestration/dag_factory.py` — gerar DAG do Airflow a partir do `config.yaml`, resolvendo registry
10. Testes para cada componente do `core/`
11. Documentar decisões e resultados específicos do projeto em `projects/ai-energy-data-project/docs/architecture.md`