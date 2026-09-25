from unittest.mock import MagicMock, patch

import pytest

from core import providers
from core.providers.google_ai_studio import build_google_ai_studio_client
from core.registry import PROVIDER_REGISTRY


def test_provider_is_registered():
    assert PROVIDER_REGISTRY["google_ai_studio"] is build_google_ai_studio_client


def test_build_client_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_AI_STUDIO_API_KEY", raising=False)
    with pytest.raises(KeyError):
        build_google_ai_studio_client()


def test_generate_calls_gemini_with_default_model(monkeypatch):
    monkeypatch.setenv("GOOGLE_AI_STUDIO_API_KEY", "fake-key")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="resposta")

    with patch.object(
        providers.google_ai_studio.genai, "Client", return_value=mock_client
    ) as mock_ctor:
        generate = build_google_ai_studio_client()
        result = generate("qual a tensão nominal?")

    mock_ctor.assert_called_once_with(api_key="fake-key")
    mock_client.models.generate_content.assert_called_once_with(
        model="gemini-flash-latest", contents="qual a tensão nominal?", config=None
    )
    assert result == "resposta"


def test_generate_uses_custom_model_and_system_instruction(monkeypatch):
    monkeypatch.setenv("GOOGLE_AI_STUDIO_API_KEY", "fake-key")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="ok")

    with patch.object(
        providers.google_ai_studio.genai, "Client", return_value=mock_client
    ):
        generate = build_google_ai_studio_client(model="gemini-2.5-flash")
        generate("prompt", system_instruction="seja conciso")

    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-flash"
    assert call_kwargs["config"].system_instruction == "seja conciso"
