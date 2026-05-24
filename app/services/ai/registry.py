"""AI provider registry: factory functions to instantiate providers from settings."""

from .anthropic_provider import AnthropicProvider
from .base import AIProvider
from .bedrock_provider import BedrockProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

PROVIDERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GeminiProvider,
    "bedrock": BedrockProvider,
}


def get_provider(provider_name: str, settings: dict) -> AIProvider:
    """Create a provider instance from settings dict."""
    if provider_name == "openai":
        return OpenAIProvider(api_key=settings.get("openai_api_key", ""))
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=settings.get("anthropic_api_key", ""))
    if provider_name == "google":
        return GeminiProvider(api_key=settings.get("google_api_key", ""))
    if provider_name == "bedrock":
        return BedrockProvider(
            aws_profile=settings.get("aws_profile", ""),
            aws_region=settings.get("aws_region", "us-east-1"),
        )
    raise ValueError(f"Unknown provider: {provider_name}")


def get_available_providers(settings: dict) -> list[str]:
    """Return list of provider names that have valid credentials configured."""
    available = []
    if settings.get("openai_api_key"):
        available.append("openai")
    if settings.get("anthropic_api_key"):
        available.append("anthropic")
    if settings.get("google_api_key"):
        available.append("google")
    if settings.get("aws_profile"):
        available.append("bedrock")
    return available
