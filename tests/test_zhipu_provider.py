"""Tests for Zhipu provider implementation."""

import os
from unittest.mock import MagicMock, patch

import pytest

from providers.shared import ProviderType
from providers.zhipu import ZhipuModelProvider


class TestZhipuProvider:
    """Test Zhipu provider functionality."""

    def setup_method(self):
        """Set up clean state before each test."""
        # Clear restriction service cache before each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

    def teardown_method(self):
        """Clean up after each test to avoid singleton issues."""
        # Clear restriction service cache after each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

    @patch.dict(os.environ, {"ZHIPU_API_KEY": "test-key"})
    def test_initialization(self):
        """Test provider initialization."""
        provider = ZhipuModelProvider("test-key")
        assert provider.api_key == "test-key"
        assert provider.get_provider_type() == ProviderType.ZHIPU
        assert provider.base_url == "https://open.bigmodel.cn/api/paas/v4"

    def test_initialization_with_custom_url(self):
        """Test provider initialization with custom base URL."""
        provider = ZhipuModelProvider("test-key", base_url="https://custom.example/v4")
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://custom.example/v4"

    def test_model_validation(self):
        """Test model name validation."""
        provider = ZhipuModelProvider("test-key")

        # Test valid models
        assert provider.validate_model_name("glm-4-flash") is True
        assert provider.validate_model_name("glm") is True
        assert provider.validate_model_name("glm-flash") is True
        assert provider.validate_model_name("glm-4") is True
        assert provider.validate_model_name("glm-4.7-flash") is True
        assert provider.validate_model_name("glm-4.7") is True
        assert provider.validate_model_name("glm-flash-4.7") is True

        # Test invalid model
        assert provider.validate_model_name("invalid-model") is False
        assert provider.validate_model_name("gpt-4") is False
        assert provider.validate_model_name("gemini-pro") is False
        assert provider.validate_model_name("grok-4") is False
        assert provider.validate_model_name("glm-3") is False
        assert provider.validate_model_name("glm3") is False

    def test_resolve_model_name(self):
        """Test model name resolution."""
        provider = ZhipuModelProvider("test-key")

        # Test shorthand resolution
        assert provider._resolve_model_name("glm") == "glm-4-flash"
        assert provider._resolve_model_name("glm-flash") == "glm-4-flash"
        assert provider._resolve_model_name("glm-4") == "glm-4-flash"
        assert provider._resolve_model_name("glm-4.7") == "glm-4.7-flash"
        assert provider._resolve_model_name("glm-flash-4.7") == "glm-4.7-flash"

        # Test full name passthrough
        assert provider._resolve_model_name("glm-4-flash") == "glm-4-flash"
        assert provider._resolve_model_name("glm-4.7-flash") == "glm-4.7-flash"

    def test_get_capabilities_glm4_flash(self):
        """Test getting model capabilities for GLM-4-Flash."""
        provider = ZhipuModelProvider("test-key")

        capabilities = provider.get_capabilities("glm-4-flash")
        assert capabilities.model_name == "glm-4-flash"
        assert capabilities.friendly_name == "Zhipu (GLM-4-Flash)"
        assert capabilities.context_window == 128_000
        assert capabilities.provider == ProviderType.ZHIPU
        assert capabilities.supports_extended_thinking is False
        assert capabilities.supports_system_prompts is True
        assert capabilities.supports_streaming is True
        assert capabilities.supports_function_calling is True
        assert capabilities.supports_json_mode is True
        assert capabilities.supports_images is False

        # Test temperature range
        assert capabilities.temperature_constraint.min_temp == 0.0
        assert capabilities.temperature_constraint.max_temp == 2.0
        assert capabilities.temperature_constraint.default_temp == 0.3

    def test_get_capabilities_glm4_7_flash(self):
        """Test getting model capabilities for GLM-4.7-Flash."""
        provider = ZhipuModelProvider("test-key")

        capabilities = provider.get_capabilities("glm-4.7-flash")
        assert capabilities.model_name == "glm-4.7-flash"
        assert capabilities.friendly_name == "Zhipu (GLM-4.7-Flash)"
        assert capabilities.context_window == 128_000
        assert capabilities.provider == ProviderType.ZHIPU
        assert capabilities.supports_extended_thinking is False
        assert capabilities.supports_function_calling is True
        assert capabilities.supports_json_mode is True
        assert capabilities.supports_images is False

    def test_get_capabilities_with_shorthand(self):
        """Test getting model capabilities with shorthand."""
        provider = ZhipuModelProvider("test-key")

        capabilities = provider.get_capabilities("glm")
        assert capabilities.model_name == "glm-4-flash"  # Should resolve to full name
        assert capabilities.context_window == 128_000

        capabilities_fast = provider.get_capabilities("glm-4.7")
        assert capabilities_fast.model_name == "glm-4.7-flash"  # Should resolve to full name

    def test_unsupported_model_capabilities(self):
        """Test error handling for unsupported models."""
        provider = ZhipuModelProvider("test-key")

        with pytest.raises(ValueError, match="Unsupported model 'invalid-model' for provider zhipu"):
            provider.get_capabilities("invalid-model")

    def test_extended_thinking_flags(self):
        """Zhipu capabilities should expose extended thinking support correctly."""
        provider = ZhipuModelProvider("test-key")

        thinking_aliases = [
            "glm-4-flash",
            "glm",
            "glm-flash",
            "glm-4",
            "glm-4.7-flash",
            "glm-4.7",
            "glm-flash-4.7",
        ]
        for alias in thinking_aliases:
            assert provider.get_capabilities(alias).supports_extended_thinking is False

    def test_provider_type(self):
        """Test provider type identification."""
        provider = ZhipuModelProvider("test-key")
        assert provider.get_provider_type() == ProviderType.ZHIPU

    @patch.dict(os.environ, {"ZHIPU_ALLOWED_MODELS": "glm-4-flash"})
    def test_model_restrictions(self):
        """Test model restrictions functionality."""
        # Clear cached restriction service
        import utils.model_restrictions
        from providers.registry import ModelProviderRegistry

        utils.model_restrictions._restriction_service = None
        ModelProviderRegistry.reset_for_testing()

        provider = ZhipuModelProvider("test-key")

        # glm-4-flash should be allowed (including alias)
        assert provider.validate_model_name("glm-4-flash") is True
        assert provider.validate_model_name("glm") is True

        # glm-4.7-flash should be blocked by restrictions
        assert provider.validate_model_name("glm-4.7-flash") is False
        assert provider.validate_model_name("glm-4.7") is False

    @patch.dict(os.environ, {"ZHIPU_ALLOWED_MODELS": "glm-4.7"})
    def test_multiple_model_restrictions(self):
        """Restrictions should allow aliases for GLM-4.7 Flash."""
        # Clear cached restriction service
        import utils.model_restrictions
        from providers.registry import ModelProviderRegistry

        utils.model_restrictions._restriction_service = None
        ModelProviderRegistry.reset_for_testing()

        provider = ZhipuModelProvider("test-key")

        # Alias should be allowed (resolves to glm-4.7-flash)
        assert provider.validate_model_name("glm-4.7") is True

        # Canonical name is not allowed unless explicitly listed
        assert provider.validate_model_name("glm-4.7-flash") is False

        # glm-4-flash should NOT be allowed
        assert provider.validate_model_name("glm-4-flash") is False

    @patch.dict(os.environ, {"ZHIPU_ALLOWED_MODELS": "glm,glm-4,glm-4.7,glm-4.7-flash"})
    def test_both_shorthand_and_full_name_allowed(self):
        """Test that aliases and canonical names can be allowed together."""
        # Clear cached restriction service
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = ZhipuModelProvider("test-key")

        # Both shorthand and full name should be allowed when explicitly listed
        assert provider.validate_model_name("glm") is True  # Alias explicitly allowed
        assert provider.validate_model_name("glm-4") is True  # Alias explicitly allowed
        assert provider.validate_model_name("glm-4-flash") is True  # Canonical name resolved from alias
        assert provider.validate_model_name("glm-4.7") is True  # Alias explicitly allowed
        assert provider.validate_model_name("glm-4.7-flash") is True  # Canonical name explicitly allowed

    @patch.dict(os.environ, {"ZHIPU_ALLOWED_MODELS": ""})
    def test_empty_restrictions_allows_all(self):
        """Test that empty restrictions allow all models."""
        # Clear cached restriction service
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = ZhipuModelProvider("test-key")

        assert provider.validate_model_name("glm-4-flash") is True
        assert provider.validate_model_name("glm-4.7-flash") is True
        assert provider.validate_model_name("glm") is True
        assert provider.validate_model_name("glm-4.7") is True

    def test_friendly_name(self):
        """Test friendly name constant."""
        provider = ZhipuModelProvider("test-key")
        assert provider.FRIENDLY_NAME == "Zhipu"

        capabilities = provider.get_capabilities("glm-4-flash")
        assert capabilities.friendly_name == "Zhipu (GLM-4-Flash)"

    def test_supported_models_structure(self):
        """Test that MODEL_CAPABILITIES has the correct structure."""
        provider = ZhipuModelProvider("test-key")

        # Check that all expected base models are present
        assert "glm-4-flash" in provider.MODEL_CAPABILITIES
        assert "glm-4.7-flash" in provider.MODEL_CAPABILITIES

        # Check model configs have required fields
        from providers.shared import ModelCapabilities

        glm4_config = provider.MODEL_CAPABILITIES["glm-4-flash"]
        assert isinstance(glm4_config, ModelCapabilities)
        assert hasattr(glm4_config, "context_window")
        assert hasattr(glm4_config, "supports_extended_thinking")
        assert hasattr(glm4_config, "aliases")
        assert glm4_config.context_window == 128_000
        assert glm4_config.supports_extended_thinking is False

        # Check aliases are correctly structured
        assert "glm" in glm4_config.aliases
        assert "glm-flash" in glm4_config.aliases
        assert "glm-4" in glm4_config.aliases

        glm47_config = provider.MODEL_CAPABILITIES["glm-4.7-flash"]
        assert glm47_config.context_window == 128_000
        assert glm47_config.supports_extended_thinking is False
        assert "glm-4.7" in glm47_config.aliases
        assert "glm-flash-4.7" in glm47_config.aliases

    @patch("providers.openai_compatible.OpenAI")
    def test_generate_content_resolves_alias_before_api_call(self, mock_openai_class):
        """Test that generate_content resolves aliases before making API calls.

        This is the CRITICAL test that ensures aliases like 'glm' get resolved
        to 'glm-4-flash' before being sent to Zhipu API.
        """
        # Set up mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock the completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "glm-4-flash"  # API returns the resolved model name
        mock_response.id = "test-id"
        mock_response.created = 1234567890
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client.chat.completions.create.return_value = mock_response

        provider = ZhipuModelProvider("test-key")

        # Call generate_content with alias 'glm'
        result = provider.generate_content(
            prompt="Test prompt", model_name="glm", temperature=0.7  # This should be resolved to "glm-4-flash"
        )

        # Verify the API was called with the RESOLVED model name
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]

        # CRITICAL ASSERTION: The API should receive "glm-4-flash", not "glm"
        assert (
            call_kwargs["model"] == "glm-4-flash"
        ), f"Expected 'glm-4-flash' but API received '{call_kwargs['model']}'"

        # Verify other parameters
        assert call_kwargs["temperature"] == 0.7
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"
        assert call_kwargs["messages"][0]["content"] == "Test prompt"

        # Verify response
        assert result.content == "Test response"
        assert result.model_name == "glm-4-flash"  # Should be the resolved name

    @patch("providers.openai_compatible.OpenAI")
    def test_generate_content_other_aliases(self, mock_openai_class):
        """Test other alias resolutions in generate_content."""
        from unittest.mock import MagicMock

        # Set up mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_client.chat.completions.create.return_value = mock_response

        provider = ZhipuModelProvider("test-key")

        # Test glm-flash -> glm-4-flash
        mock_response.model = "glm-4-flash"
        provider.generate_content(prompt="Test", model_name="glm-flash", temperature=0.7)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "glm-4-flash"

        # Test glm-4 -> glm-4-flash
        provider.generate_content(prompt="Test", model_name="glm-4", temperature=0.7)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "glm-4-flash"

        # Test glm-4.7 -> glm-4.7-flash
        mock_response.model = "glm-4.7-flash"
        provider.generate_content(prompt="Test", model_name="glm-4.7", temperature=0.7)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "glm-4.7-flash"

        # Test glm-flash-4.7 -> glm-4.7-flash
        provider.generate_content(prompt="Test", model_name="glm-flash-4.7", temperature=0.7)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "glm-4.7-flash"
