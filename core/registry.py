"""Registry central: resolve nomes usados em config.yaml para métricas e providers reais.

Ver docs/ARCHITECTURE.md, seção "Registry: resolvendo strings do config.yaml em código real".
"""

from collections.abc import Callable

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
