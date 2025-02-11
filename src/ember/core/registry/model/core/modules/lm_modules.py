import logging
from typing import Optional, Any
from pydantic import BaseModel, Field

from ember.core.registry.model.core.services.model_service import ModelService
from ember.core.registry.model.core.services.usage_service import UsageService
from ember.core.registry.model.model_registry import (
    ModelRegistry,
    GLOBAL_MODEL_REGISTRY,
)

logger: logging.Logger = logging.getLogger(__name__)


class LMModuleConfig(BaseModel):
    """Configuration settings for the Language Model module.

    Attributes:
        model_id (str): Identifier for selecting the underlying model provider.
        temperature (float): Sampling temperature for model generation.
        max_tokens (Optional[int]): Maximum tokens to generate in a single forward call.
        cot_prompt (Optional[str]): Chain-of-thought prompt appended to the user's prompt.
        persona (Optional[str]): Persona or role context prepended to the user query.
    """

    model_id: str = Field(
        default="openai:gpt-4o",
        description="String or enum-based identifier for picking the underlying model provider.",
    )
    temperature: float = Field(
        default=1.0,
        ge=0.0,
        le=5.0,
        description="Sampling temperature for model generation.",
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens to generate in a single forward call.",
    )
    cot_prompt: Optional[str] = Field(
        default=None,
        description="Optional chain-of-thought prompt or format appended to the user's prompt.",
    )
    persona: Optional[str] = Field(
        default=None,
        description="Optional persona or role context to be prepended to the user query.",
    )


def get_default_model_service(
    registry: ModelRegistry, usage_service: UsageService
) -> ModelService:
    """Creates and returns a default ModelService instance.

    This function uses the global model registry and instantiates a new UsageService.
    Default models can be registered here if needed.

    Returns:
        ModelService: A ModelService initialized with the global registry and a new UsageService.
    """
    registry = GLOBAL_MODEL_REGISTRY
    usage_service = UsageService()
    return ModelService(registry=registry, usage_service=usage_service)


class LMModule:
    """Language Model module that integrates with ModelService and optional usage tracking.

    This module is designed to generate text responses based on a user prompt. It merges
    persona and chain-of-thought details into the prompt and delegates model invocation to
    the ModelService.

    Example:
        lm_config = LMModuleConfig(model_id="provider:custom-model", temperature=0.7)
        lm_module = LMModule(config=lm_config)
        response_text = lm_module(prompt="Hello, world!")
    """

    def __init__(
        self,
        config: LMModuleConfig,
        model_service: Optional[ModelService] = None,
    ) -> None:
        """Initializes the LMModule.

        Args:
            config (LMModuleConfig): Configuration for model settings such as model_id and temperature.
            model_service (Optional[ModelService]): Service for model invocation. If None, a
                default ModelService is created.
        """
        if model_service is None:
            model_service = get_default_model_service()
        self.config: LMModuleConfig = config
        self.model_service: ModelService = model_service
        self._logger: logging.Logger = logging.getLogger(self.__class__.__name__)

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        """Enables the LMModule instance to be called like a function.

        This method simply forwards the call to the forward() method.

        Args:
            prompt (str): The input prompt to generate text from.
            **kwargs (Any): Additional keyword arguments for model invocation.

        Returns:
            str: The generated text response.
        """
        return self.forward(prompt=prompt, **kwargs)

    def forward(self, prompt: str, **kwargs: Any) -> str:
        """Generates text from a prompt by delegating the call to the ModelService.

        This method assembles a final prompt by merging persona information and a chain-of-thought
        prompt (if provided) with the user's prompt, then calls the ModelService to generate
        the response.

        Args:
            prompt (str): The user-provided prompt.
            **kwargs (Any): Additional parameters for model invocation (e.g., temperature, max_tokens).

        Returns:
            str: The generated text response.
        """
        final_prompt: str = self._assemble_full_prompt(user_prompt=prompt)
        response: Any = self.model_service.invoke_model(
            model_id=self.config.model_id,
            prompt=final_prompt,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            **kwargs,
        )
        # Return response content if available; otherwise, convert response to string.
        return response.data if hasattr(response, "data") else str(response)

    def _assemble_full_prompt(self, user_prompt: str) -> str:
        """Assembles the full prompt by merging persona and chain-of-thought details.

        Args:
            user_prompt (str): The base prompt provided by the user.

        Returns:
            str: The final prompt after merging additional context.
        """
        segments: list[str] = []
        if self.config.persona:
            segments.append(f"[Persona: {self.config.persona}]\n")
        segments.append(user_prompt.strip())
        if self.config.cot_prompt:
            segments.append(
                f"\n\n# Chain of Thought:\n{self.config.cot_prompt.strip()}"
            )
        return "\n".join(segments).strip()
