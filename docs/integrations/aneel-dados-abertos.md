# Integração: ANEEL Dados Abertos + PRODIST

## O que é

Fontes de dados públicas da ANEEL usadas pela Task 1 (Extract) do
`ai-energy-data-project`:

- **Portal de Dados Abertos** (`https://dadosabertos.aneel.gov.br`): CKAN
  público, expõe datasets de indicadores de qualidade de energia em CSV/ZIP/Parquet
- **PRODIST Módulo 8**: documento normativo estático (PDF), publicado fora do
  portal de dados abertos, em `git.aneel.gov.br` (repositório público de
  conteúdo regulatório da ANEEL)

## Docs oficiais consultadas

- Portal de Dados Abertos: https://dadosabertos.aneel.gov.br/
- API CKAN (padrão, documentação genérica do CKAN): `GET /api/3/action/package_show?id=<slug>`
- PRODIST (página oficial, lista as revisões vigentes de cada módulo):
  https://www.gov.br/aneel/pt-br/centrais-de-conteudos/procedimentos-regulatorios/prodist

## Uso no código

Implementação: `projects/ai-energy-data-project/extract_impl.py`.

- `AneelCsvExtractSpecialist`: resolve o resource CSV via `package_show` da
  API CKAN (`dataset_slug` + `resource_name` vêm do `config.yaml` do
  projeto) em vez de hardcodar a URL de download -- o UUID do resource muda
  quando a ANEEL republica o dataset, mas o slug do dataset e o nome do
  resource são estáveis.
- `ProdistPdfExtractSpecialist`: baixa o PDF de uma `url` fixa (config.yaml),
  usa o header HTTP `Last-Modified` para popular `source_updated_at`.

## Datasets/resources usados atualmente

Verificados manualmente em 2026-09-24 contra a API CKAN ao vivo -- UUIDs de
resource rotacionam, por isso o código nunca os hardcoda, só os nomes abaixo:

| Fonte | Dataset slug | Resource name |
|---|---|---|
| DRP/DRC | `indicadores-de-conformidade-do-nivel-de-tensao-em-regime-permanente` | `indicadores-conformidade-nivel-tensao` |
| DEC/FEC | `indicadores-coletivos-de-continuidade-dec-e-fec` | `indicadores-continuidade-coletivos-limite` (limites regulatórios; a série histórica completa está num resource ZIP separado -- reavaliar se este é o resource correto quando o `config.yaml` do projeto for escrito) |
| PRODIST Módulo 8 | -- | URL direta: `git.aneel.gov.br/publico/centralconteudo/-/raw/main/procreg/prodist/modulo08/aren20251137_Prodist_modulo_8_v14.pdf` (revisão v14, AREN 2025/1137) |

## Limitações conhecidas

- Nenhuma chamada de rede real foi feita durante o desenvolvimento: o sandbox
  de execução não tem saída de rede via `requests`. As URLs/slugs foram
  confirmados via ferramenta de fetch com rota de rede própria, não pela
  execução do código. Primeira validação real será na primeira DAG rodada.
- O resource de DEC/FEC escolhido (`indicadores-continuidade-coletivos-limite`)
  contém os limites regulatórios, não necessariamente a série de valores
  medidos -- decisão a revisitar ao definir o `config.yaml` do projeto.
