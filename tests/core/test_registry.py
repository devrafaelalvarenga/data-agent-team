from core.registry import (
    METRIC_REGISTRY,
    PROVIDER_REGISTRY,
    register_metric,
    register_provider,
)


def test_register_metric_adds_to_registry():
    @register_metric("test_metric_ok")
    def my_metric(sample):
        return 1.0

    assert METRIC_REGISTRY["test_metric_ok"] is my_metric


def test_register_metric_preserves_function_behavior():
    @register_metric("test_metric_passthrough")
    def my_metric(sample):
        return 0.5

    assert my_metric(sample=[]) == 0.5


def test_register_provider_adds_to_registry():
    @register_provider("test_provider_ok")
    def my_provider():
        return "client"

    assert PROVIDER_REGISTRY["test_provider_ok"] is my_provider


def test_metric_and_provider_registries_are_independent():
    @register_metric("test_shared_name")
    def metric_fn(sample):
        return 1.0

    @register_provider("test_shared_name")
    def provider_fn():
        return "client"

    assert METRIC_REGISTRY["test_shared_name"] is metric_fn
    assert PROVIDER_REGISTRY["test_shared_name"] is provider_fn


def test_registering_same_name_twice_overwrites_previous():
    @register_metric("test_overwrite")
    def first(sample):
        return 0.0

    @register_metric("test_overwrite")
    def second(sample):
        return 1.0

    assert METRIC_REGISTRY["test_overwrite"] is second
