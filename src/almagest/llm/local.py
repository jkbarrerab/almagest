"""OpenAI-compatible local LLM backend (Ollama, LM Studio, vLLM, etc.).

Tool use is attempted via OpenAI function-calling format; if the model
doesn't support it, we fall back to a text-only conversation where tool
calls are extracted from ```json code blocks in the response.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterator

from openai import OpenAI

from .base import BaseLLM, LLMResponse, Message, ToolCall


_TOOL_CALL_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


class LocalLLM(BaseLLM):
    def __init__(self, base_url: str, model: str, api_key: str = "ollama") -> None:
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        result = []
        for m in messages:
            if isinstance(m.content, str):
                result.append({"role": m.role, "content": m.content})
            else:
                # Flatten tool_result blocks into text for local models
                parts = []
                for block in m.content:
                    if isinstance(block, dict):
                        if block.get("type") == "tool_result":
                            parts.append(f"[Tool result]: {block.get('content', '')}")
                        elif block.get("type") == "text":
                            parts.append(block.get("text", ""))
                        else:
                            parts.append(str(block))
                    else:
                        parts.append(str(block))
                result.append({"role": m.role, "content": "\n".join(parts)})
        return result

    def chat(
        self,
        messages: list[Message],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        converted = self._convert_messages(messages)
        if system:
            converted = [{"role": "system", "content": system}] + converted

        # Try native function-calling first
        if tools:
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"],
                    },
                }
                for t in tools
            ]
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=converted,
                    tools=openai_tools,
                    max_tokens=max_tokens,
                )
                msg = response.choices[0].message
                tool_calls = []
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_calls.append(
                            ToolCall(
                                id=tc.id,
                                name=tc.function.name,
                                arguments=json.loads(tc.function.arguments),
                            )
                        )
                stop = response.choices[0].finish_reason or "stop"
                stop_reason = "tool_use" if tool_calls else "end_turn"
                return LLMResponse(
                    content=msg.content or "",
                    tool_calls=tool_calls,
                    stop_reason=stop_reason,
                )
            except Exception:
                # Fall through to text-based approach
                pass

            # Fallback: inject tool descriptions as system text and parse JSON blocks
            tool_desc = _tools_as_text(tools)
            if system:
                converted[0]["content"] += "\n\n" + tool_desc
            else:
                converted = [{"role": "system", "content": tool_desc}] + converted

        response = self.client.chat.completions.create(
            model=self.model,
            messages=converted,
            max_tokens=max_tokens,
        )
        text = response.choices[0].message.content or ""
        tool_calls = _extract_tool_calls(text)
        return LLMResponse(
            content=text,
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
        )

    def stream_chat(
        self,
        messages: list[Message],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 8192,
    ) -> Iterator[str]:
        converted = self._convert_messages(messages)
        if system:
            converted = [{"role": "system", "content": system}] + converted

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=converted,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def supports_tools(self) -> bool:
        return True  # we try native first, then fallback


def _tools_as_text(tools: list[dict[str, Any]]) -> str:
    lines = [
        "You have access to the following tools. To call a tool, respond with a JSON code block:",
        "```json",
        '{"tool": "<name>", "arguments": {<key>: <value>, ...}}',
        "```",
        "",
    ]
    for t in tools:
        lines.append(f"- **{t['name']}**: {t['description']}")
    return "\n".join(lines)


def _extract_tool_calls(text: str) -> list[ToolCall]:
    calls = []
    for i, m in enumerate(_TOOL_CALL_RE.finditer(text)):
        try:
            data = json.loads(m.group(1))
            if "tool" in data and "arguments" in data:
                calls.append(
                    ToolCall(
                        id=f"local_{i}",
                        name=data["tool"],
                        arguments=data["arguments"],
                    )
                )
        except json.JSONDecodeError:
            pass
    return calls
