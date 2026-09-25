# Integração: Google AI Studio (Gemini)

## O que é

API de geração de texto do Gemini via Google AI Studio (não Vertex AI) -- cota
gratuita diária, sem billing obrigatório. Usada como LLM provider registrado no
`core/registry.py` sob o nome `google_ai_studio`, referenciado por qualquer
`config.yaml` de projeto (`transform.llm_provider: google_ai_studio`).

## SDK e docs oficiais

- SDK: [`google-genai`](https://pypi.org/project/google-genai/) (pacote Python
  oficial, GA desde maio de 2025 -- substitui o antigo `google-generativeai`)
- Docs: [ai.google.dev/gemini-api/docs](https://ai.google.dev/gemini-api/docs)
- Repositório: [github.com/googleapis/python-genai](https://github.com/googleapis/python-genai)

## Uso no código

Implementação: `core/providers/google_ai_studio.py`. Padrão confirmado no
README oficial do SDK (`client.models.generate_content(model=..., contents=...,
config=types.GenerateContentConfig(...))`, resposta em `response.text`).

```python
from core.registry import PROVIDER_REGISTRY

build_client = PROVIDER_REGISTRY["google_ai_studio"]
generate = build_client(model="gemini-flash-latest")  # model vem do config.yaml
texto = generate("prompt aqui", system_instruction="opcional")
```

## Configuração necessária

- `.env`: `GOOGLE_AI_STUDIO_API_KEY` (gerada em https://aistudio.google.com/apikey,
  associada ao mesmo `GCP_PROJECT_ID` usado por Cloud Storage/BigQuery)
- Nome do modelo: parâmetro `model` do factory, nunca hardcoded fora do
  `config.yaml` do projeto -- ver regra de "proibido hardcode" no `CLAUDE.md`

## Onde é usada

`projects/ai-energy-data-project/transform_impl.py`:
- `PdistChunkingTransformSpecialist`: limpa cada seção do PRODIST extraída do
  PDF (remove cabeçalho/rodapé/hifenização, sem alterar conteúdo normativo)
- `PdistFidelityTransformSupervisor`: julga, por seção, se a limpeza foi fiel
  ao texto bruto

## Limitações conhecidas

- Rate limits do tier gratuito não são documentados publicamente em valores
  fixos -- consultar https://aistudio.google.com/rate-limit com a key ativa.
- Não foi possível fazer uma chamada real de smoke test durante o
  desenvolvimento: o sandbox de execução usado não tem saída de rede via
  `requests`/HTTP direta (só via ferramentas de fetch com rota própria). Os
  testes cobrem a lógica com o client do `google-genai` mockado.
