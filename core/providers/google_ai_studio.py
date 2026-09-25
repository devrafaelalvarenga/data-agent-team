"""Provider Google AI Studio (Gemini). Ver docs/integrations/google-ai-studio.md.

Registrado no PROVIDER_REGISTRY sob o nome 'google_ai_studio' -- qualquer
projeto referencia esse nome em config.yaml (ex.: transform.llm_provider),
nunca importa este módulo diretamente.
"""

import os
from collections.abc import Callable

from google import genai
from google.genai import types

from core.registry import register_provider

DEFAULT_MODEL = "gemini-flash-latest"


@register_provider("google_ai_studio")
def build_google_ai_studio_client(
    model: str = DEFAULT_MODEL,
) -> Callable[[str, str | None], str]:
    """Factory: monta o client do Gemini e retorna `generate(prompt, system_instruction=None)`.

    A API key nunca é hardcoded -- vem de GOOGLE_AI_STUDIO_API_KEY no .env.
    `model` vem do config.yaml do projeto, não é fixo aqui.
    """
    api_key = os.environ["GOOGLE_AI_STUDIO_API_KEY"]
    client = genai.Client(api_key=api_key)

    def generate(prompt: str, system_instruction: str | None = None) -> str:
        config = (
            types.GenerateContentConfig(system_instruction=system_instruction)
            if system_instruction
            else None
        )
        response = client.models.generate_content(
            model=model, contents=prompt, config=config
        )
        return response.text

    return generate
