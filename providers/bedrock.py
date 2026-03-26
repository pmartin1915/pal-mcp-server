"""AWS Bedrock model provider implementation.

Uses the boto3 Bedrock Runtime ``converse`` API for a unified interface
across all Bedrock-hosted foundation models (Amazon Nova, Llama, Mistral, etc.).
"""

import logging
from typing import TYPE_CHECKING, ClassVar, Optional

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from .base import ModelProvider
from .registries.bedrock import BedrockModelRegistry
from .registry_provider_mixin import RegistryBackedProviderMixin
from .shared import ModelCapabilities, ModelResponse, ProviderType

logger = logging.getLogger(__name__)


class BedrockModelProvider(RegistryBackedProviderMixin, ModelProvider):
    """AWS Bedrock integration using the ``converse`` API via boto3.

    Authentication uses standard AWS credential chain:
    ``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY``, and ``AWS_DEFAULT_REGION``.
    """

    REGISTRY_CLASS = BedrockModelRegistry
    MODEL_CAPABILITIES: ClassVar[dict[str, ModelCapabilities]] = {}

    def __init__(self, api_key: str, **kwargs):
        """Initialize Bedrock provider.

        Args:
            api_key: AWS access key ID (also reads from environment via boto3).
            **kwargs: Optional ``region_name`` override.
        """
        self._ensure_registry()
        super().__init__(api_key, **kwargs)
        self._client = None
        self._region = kwargs.get("region_name")
        self._invalidate_capability_cache()

    # ------------------------------------------------------------------
    # Client access
    # ------------------------------------------------------------------

    @property
    def client(self):
        """Lazy initialization of Bedrock Runtime client."""
        if self._client is None:
            import boto3

            client_kwargs = {"service_name": "bedrock-runtime"}
            if self._region:
                client_kwargs["region_name"] = self._region
            self._client = boto3.client(**client_kwargs)
        return self._client

    # ------------------------------------------------------------------
    # Provider identity
    # ------------------------------------------------------------------

    def get_provider_type(self) -> ProviderType:
        return ProviderType.BEDROCK

    # ------------------------------------------------------------------
    # Request execution
    # ------------------------------------------------------------------

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using a Bedrock model via the ``converse`` API.

        Args:
            prompt: User prompt text.
            model_name: Canonical model ID or alias.
            system_prompt: Optional system instructions.
            temperature: Sampling temperature.
            max_output_tokens: Cap on output tokens.

        Returns:
            Normalised ModelResponse.
        """
        self.validate_parameters(model_name, temperature)
        capabilities = self.get_capabilities(model_name)
        resolved = self._resolve_model_name(model_name)

        # Build messages in Bedrock converse format
        messages = [
            {"role": "user", "content": [{"text": prompt}]},
        ]

        # Build inference config
        inference_config = {"temperature": temperature}
        effective_max_tokens = max_output_tokens or capabilities.max_output_tokens or 4096
        inference_config["maxTokens"] = effective_max_tokens

        # System prompt
        system_list = None
        if system_prompt and capabilities.supports_system_prompts:
            system_list = [{"text": system_prompt}]

        max_retries = 3
        retry_delays = [1, 3, 5]
        attempt_counter = {"value": 0}

        def _attempt() -> ModelResponse:
            attempt_counter["value"] += 1

            converse_kwargs = {
                "modelId": resolved,
                "messages": messages,
                "inferenceConfig": inference_config,
            }
            if system_list:
                converse_kwargs["system"] = system_list

            response = self.client.converse(**converse_kwargs)

            # Extract response content
            content = ""
            output = response.get("output", {})
            message = output.get("message", {})
            for block in message.get("content", []):
                if "text" in block:
                    content += block["text"]

            # Extract usage
            usage_raw = response.get("usage", {})
            usage = {
                "input_tokens": usage_raw.get("inputTokens", 0),
                "output_tokens": usage_raw.get("outputTokens", 0),
                "total_tokens": usage_raw.get("totalTokens", 0),
            }
            if usage["total_tokens"] == 0:
                usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]

            stop_reason = response.get("stopReason", "end_turn")

            return ModelResponse(
                content=content,
                usage=usage,
                model_name=resolved,
                friendly_name=f"Bedrock ({resolved.split('.')[-1].split('-v')[0] if '.' in resolved else resolved})",
                provider=ProviderType.BEDROCK,
                metadata={
                    "stop_reason": stop_reason,
                    "finish_reason": stop_reason,
                },
            )

        try:
            return self._run_with_retries(
                operation=_attempt,
                max_attempts=max_retries,
                delays=retry_delays,
                log_prefix=f"Bedrock API ({resolved})",
            )
        except Exception as exc:
            attempts = max(attempt_counter["value"], 1)
            error_msg = (
                f"Bedrock API error for model {resolved} after {attempts} attempt"
                f"{'s' if attempts > 1 else ''}: {exc}"
            )
            raise RuntimeError(error_msg) from exc

    # ------------------------------------------------------------------
    # Error classification
    # ------------------------------------------------------------------

    def _is_error_retryable(self, error: Exception) -> bool:
        """Classify Bedrock errors for retry logic."""
        error_str = str(error).lower()

        # Non-retryable
        if "validationexception" in error_str or "accessdeniedexception" in error_str:
            return False
        if "429" in error_str or "throttlingexception" in error_str:
            return True

        retryable = [
            "timeout", "connection", "serviceexception",
            "internalservererror", "502", "503", "504",
        ]
        return any(ind in error_str for ind in retryable)

    # ------------------------------------------------------------------
    # Model preferences
    # ------------------------------------------------------------------

    def get_preferred_model(self, category: "ToolModelCategory", allowed_models: list[str]) -> Optional[str]:
        """Select the best Bedrock model for a given task category."""
        from tools.models import ToolModelCategory

        if not allowed_models:
            return None

        def find_first(preferences: list[str]) -> Optional[str]:
            for model in preferences:
                if model in allowed_models:
                    return model
            return None

        if category == ToolModelCategory.EXTENDED_REASONING:
            preferred = find_first([
                "us.meta.llama3-3-70b-instruct-v1:0",
                "us.mistral.mistral-large-2407-v1:0",
                "us.amazon.nova-pro-v1:0",
            ])
            return preferred or allowed_models[0]

        elif category == ToolModelCategory.FAST_RESPONSE:
            preferred = find_first([
                "us.amazon.nova-micro-v1:0",
                "us.amazon.nova-lite-v1:0",
            ])
            return preferred or allowed_models[0]

        else:  # BALANCED
            preferred = find_first([
                "us.amazon.nova-pro-v1:0",
                "us.meta.llama3-3-70b-instruct-v1:0",
                "us.mistral.mistral-large-2407-v1:0",
            ])
            return preferred or allowed_models[0]


# Load registry data at import time
BedrockModelProvider._ensure_registry()
