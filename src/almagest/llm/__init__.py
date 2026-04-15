"""LLM provider abstraction — Claude (default) or any OpenAI-compatible local LLM."""

from __future__ import annotations

from .. import config
from .base import BaseLLM, Message, ToolCall, ToolResult


def get_llm() -> BaseLLM:
    """Return the configured LLM instance."""
    provider = config.llm_provider()
    if provider == "claude":
        from .claude import ClaudeLLM
        return ClaudeLLM(model=config.claude_model(), api_key=config.anthropic_key())
    elif provider == "local":
        from .local import LocalLLM
        return LocalLLM(
            base_url=config.local_llm_base_url(),
            model=config.local_llm_model(),
            api_key=config.local_llm_api_key(),
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider!r}. Set LLM_PROVIDER=claude or local.")


__all__ = ["get_llm", "BaseLLM", "Message", "ToolCall", "ToolResult"]
