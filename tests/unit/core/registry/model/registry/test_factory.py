#!/usr/bin/env python3
"""Unit tests for the ModelFactory.

Tests instantiation of provider models and error conditions.
"""

import pytest
from typing import Any, Dict

from src.ember.core.registry.model.registry.factory import ModelFactory
from src.ember.core.registry.model.schemas.model_info import ModelInfo
from src.ember.core.registry.model.schemas.provider_info import ProviderInfo
from src.ember.core.registry.model.schemas.cost import ModelCost, RateLimit
from src.ember.core.registry.model.utils.model_registry_exceptions import (
    ProviderConfigError,
)


# Dummy provider class for testing
class DummyProviderModel:
    PROVIDER_NAME = "DummyProvider"

    def __init__(self, model_info: ModelInfo) -> None:
        self.model_info = model_info

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        return f"Echo: {prompt}"


# Dummy discover function that returns our dummy provider.
def dummy_discover_providers(*, package_path: str) -> Dict[str, type]:
    return {"DummyProvider": DummyProviderModel}


@pytest.fixture(autouse=True)
def patch_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.ember.core.registry.model.registry.factory.discover_providers_in_package",
        dummy_discover_providers,
    )


def create_dummy_model_info(model_id: str = "dummy:factory") -> ModelInfo:
    return ModelInfo(
        id=model_id,
        name="DummyFactoryModel",
        cost=ModelCost(input_cost_per_thousand=1.0, output_cost_per_thousand=2.0),
        rate_limit=RateLimit(tokens_per_minute=1000, requests_per_minute=100),
        provider=ProviderInfo(name="DummyProvider", default_api_key="dummy_key"),
        api_key="dummy_key",
    )


def test_create_model_from_info_success() -> None:
    """Test that ModelFactory.create_model_from_info successfully creates a DummyProviderModel."""
    dummy_info = create_dummy_model_info("dummy:factory")
    model_instance = ModelFactory.create_model_from_info(model_info=dummy_info)
    assert isinstance(model_instance, DummyProviderModel)
    assert model_instance.model_info.id == "dummy:factory"


def test_create_model_from_info_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that an invalid model id causes ProviderConfigError."""
    dummy_info = create_dummy_model_info("invalid:model")

    # Monkey-patch parse_model_str to always raise ValueError
    def mock_parse_model_str(model_str: str) -> str:
        raise ValueError("Invalid model ID format")

    monkeypatch.setattr(
        "src.ember.core.registry.model.registry.factory.parse_model_str",
        mock_parse_model_str,
    )

    with pytest.raises(ProviderConfigError):
        ModelFactory.create_model_from_info(model_info=dummy_info)
