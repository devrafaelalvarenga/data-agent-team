# Decisões técnicas: ai-energy-data-project

Ver `docs/ARCHITECTURE.md` para a arquitetura genérica do framework. Este
documento cobre só decisões específicas deste projeto.

## Status por fonte

| Fonte | Extract | Transform | Harness/Load | DAG |
|---|---|---|---|---|
| `prodist_pdf` | ✅ `ProdistPdfExtractSpecialist` | ✅ `PdistChunkingTransformSpecialist` + `PdistFidelityTransformSupervisor` | ✅ genérico (`core/harness`, `core/load`) | ✅ `dags/ai_energy_data_project.py` |
| `aneel_drp_drc_parquet` | ✅ `AneelParquetExtractSpecialist` | ❌ pendente | -- | ❌ pendente |
| `aneel_dec_fec_parquet` | ✅ `AneelParquetExtractSpecialist` | ❌ pendente | -- | ❌ pendente |

## Extract das fontes ANEEL: Parquet, não CSV

Trocado de CSV para Parquet em 25/09/2026: schema tipado embutido (não
precisa mais declarar tipo de coluna manualmente em `schema_rules` do
`config.yaml`) e carga nativa mais eficiente no BigQuery -- ver
`docs/integrations/aneel-dados-abertos.md`. `AneelParquetExtractSpecialist`
converte colunas de data/decimal do parquet para ISO string/float, já que
não são JSON-safe por padrão e `raw_content` precisa trafegar via XCom.

## Pendência: Transform das fontes ANEEL (DRP/DRC, DEC/FEC)

As duas fontes ainda não têm `TransformSpecialist`. Decisão a tomar antes de
implementar a DAG delas: dado tabular sem ambiguidade textual pode não
precisar de julgamento semântico de LLM na Task 2 (diferente do PDF do
PRODIST, que envolve limpar texto extraído e decidir o que é ruído de PDF vs.
conteúdo normativo). Duas opções:

1. **Transform determinístico** (Python puro: valida schema, calcula
   `completeness_ratio`, estrutura em `SilverRecord`) -- mais simples, mais
   barato, mas quebraria a regra "Task 2 sempre tem LLM" do `docs/ARCHITECTURE.md`
   se essa regra for lida literalmente. Argumento a favor: a regra
   não-negociável do projeto é "LLM só onde há julgamento semântico real" --
   se não há julgamento semântico real num dado tabular já estruturado (e
   agora já tipado via Parquet), forçar LLM aqui contradiria o próprio
   princípio.
2. **Transform com LLM mesmo assim**, para manter uniformidade entre fontes e
   cobrir casos como valores fora do domínio esperado (`dominio-indicadores.parquet`
   do dataset da ANEEL) que exigem julgamento.

Não decidido ainda -- revisar antes de implementar `transform_impl.py` para
essas duas fontes.

## Resource escolhido para DEC/FEC

`indicadores-continuidade-coletivos-2020-2029.parquet` (série histórica de
valores medidos 2020-2029) -- decisão do usuário em 25/09/2026, resolvendo a
pendência anterior. Não é `indicadores-continuidade-coletivos-limite`, que
só tem os limites regulatórios, não os valores medidos.

## `gold_writer`/`audit_writer` são placeholders

`dags/ai_energy_data_project.py` usa `_log_gold_writer`/`_log_audit_writer`
(só logam, não persistem) porque ainda não existe uma camada de
persistência real (GCS/BigQuery) implementada em `core/` ou neste projeto.
`LoadGate` já é genérico o suficiente para receber writers reais quando essa
camada existir -- não é preciso mudar `core/load/base.py`.

## Validação pendente

Nada neste projeto foi validado contra rede real ou contra o Airflow real
rodando: o ambiente de desenvolvimento usado não tinha acesso de rede via
`requests` no sandbox de execução, nem Docker rodando para `astro dev start`.
Primeira validação real de ponta a ponta: rodar `astro dev start` com Docker
ativo e observar a DAG `ai_energy_prodist_pipeline` na UI do Airflow.
