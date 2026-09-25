# Decisões técnicas: ai-energy-data-project

Ver `docs/ARCHITECTURE.md` para a arquitetura genérica do framework. Este
documento cobre só decisões específicas deste projeto.

## Status por fonte

| Fonte | Extract | Transform | Harness/Load | DAG |
|---|---|---|---|---|
| `prodist_pdf` | ✅ `ProdistPdfExtractSpecialist` | ✅ `PdistChunkingTransformSpecialist` + `PdistFidelityTransformSupervisor` (LLM) | ✅ genérico (`core/harness`, `core/load`) | ✅ `ai_energy_prodist_pipeline` |
| `aneel_drp_drc_parquet` | ✅ `AneelParquetExtractSpecialist` | ✅ `AneelTabularTransformSpecialist` + `AneelTabularTransformSupervisor` (determinístico) | ✅ genérico | ✅ `ai_energy_aneel_drp_drc_parquet_pipeline` |
| `aneel_dec_fec_parquet` | ✅ `AneelParquetExtractSpecialist` | ✅ `AneelTabularTransformSpecialist` + `AneelTabularTransformSupervisor` (determinístico) | ✅ genérico | ✅ `ai_energy_aneel_dec_fec_parquet_pipeline` |

Todas as 3 DAGs vivem em `dags/ai_energy_data_project.py` (`_build_prodist_dag` +
`_build_aneel_dag`, genérico para as duas fontes tabulares).

## Extract das fontes ANEEL: Parquet, não CSV

Trocado de CSV para Parquet em 25/09/2026: schema tipado embutido (não
precisa mais declarar tipo de coluna manualmente em `schema_rules` do
`config.yaml`) e carga nativa mais eficiente no BigQuery -- ver
`docs/integrations/aneel-dados-abertos.md`. `AneelParquetExtractSpecialist`
converte colunas de data/decimal do parquet para ISO string/float, já que
não são JSON-safe por padrão e `raw_content` precisa trafegar via XCom.

## Decisão: Transform das fontes ANEEL (DRP/DRC, DEC/FEC) é determinístico

Decidido em 25/09/2026: **determinístico, sem LLM**
(`AneelTabularTransformSpecialist`/`AneelTabularTransformSupervisor` em
`transform_impl.py`). Dado tabular já vem tipado do Parquet (ver Extract
acima), sem ambiguidade textual -- não há julgamento semântico real a fazer.
A regra não-negociável do framework é "LLM só onde há julgamento semântico
real"; forçar LLM aqui (só para manter uniformidade com o PDF do PRODIST)
contradiria o próprio princípio.

O supervisor checa: `linhas_preservadas` (nada perdido/adicionado no
pass-through Bronze→Silver), `schema_consistente` (todas as linhas com o
mesmo conjunto de colunas) e, opcionalmente, `colunas_esperadas` (só ativa
se `expected_columns` for configurado em `config.yaml` -- ainda vazio hoje,
porque o schema real dos resources Parquet nunca foi inspecionado contra
dado ao vivo; preencher na primeira execução real).

Se no futuro aparecer um caso real de julgamento semântico (ex.: detectar
padrão anômalo que exija interpretação, não só validação de domínio), dá
para trocar por um `TransformSupervisor` LLM sem quebrar a interface.

## Harness das fontes ANEEL: sem `chunk_size_valid`, `sample_size: 1`

`chunk_size_valid` não entra nas métricas de `aneel_drp_drc_parquet`/
`aneel_dec_fec_parquet`: não há conceito de "chunk" em dado tabular, e
`AneelTabularTransformSpecialist` não popula `metadata["chunk_sizes"]` --
incluir a métrica só puxaria a nota pra 0 à toa. Fica só
`faithfulness_to_source` (agrega `transform_approved`) e
`metadata_extracted` (valida contra `expected_metadata_fields`, que o
specialist já declara). `sample_size: 1` porque hoje o Bronze inteiro (a
tabela completa) é um único `SilverRecord` por execução -- reavaliar se um
dia o pipeline passar a processar linha a linha.

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
ativo e observar as 3 DAGs (`ai_energy_prodist_pipeline`,
`ai_energy_aneel_drp_drc_parquet_pipeline`,
`ai_energy_aneel_dec_fec_parquet_pipeline`) na UI do Airflow.
