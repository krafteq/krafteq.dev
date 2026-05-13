"""
Config loader and LangChain model factory.

Replaces the old custom providers/ layer — LangChain's model wrappers
handle the provider differences so we don't have to.
"""

import os
import json
from pathlib import Path


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path) as f:
        return json.load(f)


def make_model(cfg: dict):
    """
    Build a LangChain chat model from a config dict entry.

    Supported providers:
      anthropic           → ChatAnthropic  (pip install langchain-anthropic)
      openai              → ChatOpenAI     (pip install langchain-openai)
      groq                → ChatOpenAI with Groq base_url
      together            → ChatOpenAI with Together base_url
      mistral             → ChatOpenAI with Mistral base_url
      ollama              → ChatOpenAI with Ollama base_url (no key needed)
    """
    provider   = cfg.get("provider", "anthropic").lower()
    model_name = cfg["model"]
    api_key    = os.environ.get(cfg.get("api_key_env", ""), "") or "none"
    base_url   = cfg.get("base_url") or None
    max_tokens = cfg.get("max_tokens", 4096)

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError("Run: pip install langchain-anthropic")
        if api_key == "none":
            raise EnvironmentError(
                f"Missing API key. Set {cfg.get('api_key_env', 'ANTHROPIC_API_KEY')} env var."
            )
        return ChatAnthropic(
            model=model_name,
            anthropic_api_key=api_key,
            max_tokens=max_tokens,
        )

    # All OpenAI-compatible providers (openai, groq, together, mistral, ollama)
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError("Run: pip install langchain-openai")

    kwargs = dict(
        model=model_name,
        api_key=api_key,
        max_tokens=max_tokens,
    )
    if base_url:
        kwargs["base_url"] = base_url

    return ChatOpenAI(**kwargs)


def get_agent_cfg(cfg: dict, role: str) -> dict:
    """
    Get config for a specific agent role.
    Falls back to 'developer' config if the role isn't explicitly defined.
    This lets you define reviewer/tester once and share with developer.
    """
    return cfg.get(role, cfg.get("developer", {}))
