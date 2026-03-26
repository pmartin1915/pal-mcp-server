"""Registry loader for AWS Bedrock model capabilities."""

from __future__ import annotations

from ..shared import ProviderType
from .base import CapabilityModelRegistry


class BedrockModelRegistry(CapabilityModelRegistry):
    """Capability registry backed by ``conf/bedrock_models.json``."""

    def __init__(self, config_path: str | None = None) -> None:
        super().__init__(
            env_var_name="BEDROCK_MODELS_CONFIG_PATH",
            default_filename="bedrock_models.json",
            provider=ProviderType.BEDROCK,
            friendly_prefix="Bedrock ({model})",
            config_path=config_path,
        )
