"""
Provider factory.

Usage:
    from providers import make_provider
    provider = make_provider(config_entry)
"""

import os
from .base import BaseProvider, ChatResponse, ToolCall, ToolParam, ToolResult


def make_provider(cfg: dict) -> BaseProvider:
    """
    Build a provider from a config dict (one entry from agent.config.json).

    Expected keys:
      provider     — "anthropic" | "openai" | "groq" | "together" | "mistral" | "ollama"
      model        — model name string
      api_key_env  — env var name that holds the API key (omit for Ollama)
      base_url     — optional override URL (for local models, Groq, etc.)
      max_tokens   — optional int (defaults to 4096)
    """
    provider_name = cfg.get("provider", "anthropic").lower()
    model         = cfg["model"]
    max_tokens    = cfg.get("max_tokens", 4096)
    base_url      = cfg.get("base_url") or None

    # Resolve API key from environment
    key_env = cfg.get("api_key_env", "")
    api_key = os.environ.get(key_env, "") if key_env else ""

    # Shorthand aliases → canonical provider
    openai_compat = {"openai", "groq", "together", "mistral", "ollama", "openai_compatible"}

    if provider_name == "anthropic":
        if not api_key:
            raise EnvironmentError(
                f"Anthropic API key not found. Set the '{key_env}' environment variable."
            )
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(model=model, api_key=api_key, base_url=base_url, max_tokens=max_tokens)

    elif provider_name in openai_compat:
        # For Ollama, a real key isn't needed
        if not api_key and provider_name != "ollama":
            raise EnvironmentError(
                f"API key not found for provider '{provider_name}'. "
                f"Set the '{key_env}' environment variable."
            )
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(model=model, api_key=api_key or "ollama", base_url=base_url, max_tokens=max_tokens)

    else:
        raise ValueError(
            f"Unknown provider '{provider_name}'. "
            f"Supported: anthropic, openai, groq, together, mistral, ollama"
        )


__all__ = ["make_provider", "BaseProvider", "ChatResponse", "ToolCall", "ToolParam", "ToolResult"]
