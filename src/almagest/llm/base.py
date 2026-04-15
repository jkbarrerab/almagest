"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class Message:
    role: str  # "user" | "assistant" | "tool"
    content: str | list[dict[str, Any]]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"  # "end_turn" | "tool_use" | "max_tokens"
    input_tokens: int = 0
    output_tokens: int = 0


class BaseLLM(ABC):
    """Common interface for all LLM backends."""

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Send a conversation and return the response (non-streaming)."""

    @abstractmethod
    def stream_chat(
        self,
        messages: list[Message],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 8192,
    ) -> Iterator[str]:
        """Stream text tokens from the LLM."""

    def supports_tools(self) -> bool:
        """Whether this backend supports structured tool use."""
        return True
