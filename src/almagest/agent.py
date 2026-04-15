"""Agentic loop — drives a single agent through tool-use until completion.

Usage:
    agent = Agent(llm, tools=ALL_TOOLS, system="You are a researcher...")
    result = agent.run("Find papers about dark matter halos", console=console)
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.markup import escape

from .llm.base import BaseLLM, LLMResponse, Message
from .llm.claude import ClaudeLLM
from .tools import execute_tool


class Agent:
    """Single agent that loops until it produces a final answer."""

    MAX_ITERATIONS = 30

    def __init__(
        self,
        llm: BaseLLM,
        tools: list[dict[str, Any]],
        system: str = "",
        name: str = "Agent",
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.system = system
        self.name = name

    def run(
        self,
        task: str,
        console: Console | None = None,
        extra_context: str = "",
    ) -> str:
        """Run the agent on a task. Returns the final text output."""
        if console is None:
            console = Console()

        prompt = task
        if extra_context:
            prompt = f"{extra_context}\n\n---\n\n{task}"

        messages: list[Message] = [Message(role="user", content=prompt)]

        for iteration in range(self.MAX_ITERATIONS):
            response = self.llm.chat(
                messages=messages,
                system=self.system,
                tools=self.tools if self.tools else None,
            )

            if response.stop_reason == "end_turn" or not response.tool_calls:
                if response.content:
                    return response.content
                # No content but stopped — return whatever we have
                return ""

            # Handle tool calls
            if response.content:
                console.print(f"[dim]{escape(response.content[:200])}[/dim]")

            # Build assistant message with tool use blocks (Anthropic format)
            assistant_content = _build_assistant_content(response, self.llm)
            messages.append(Message(role="assistant", content=assistant_content))

            # Execute all tool calls and collect results
            tool_results = []
            for tc in response.tool_calls:
                console.print(
                    f"  [cyan]→ {tc.name}[/cyan]([dim]{_fmt_args(tc.arguments)}[/dim])"
                )
                result = execute_tool(tc.name, tc.arguments)
                preview = result[:150].replace("\n", " ")
                console.print(f"    [dim]{escape(preview)}...[/dim]" if len(result) > 150 else f"    [dim]{escape(result)}[/dim]")

                tool_results.append(
                    _build_tool_result(tc.id, result, self.llm)
                )

            messages.append(Message(role="user", content=tool_results))

        return "[Max iterations reached]"


def _build_assistant_content(response: LLMResponse, llm: BaseLLM) -> list[dict[str, Any]]:
    """Build the assistant message content in the format expected by the LLM."""
    blocks: list[dict[str, Any]] = []
    if response.content:
        blocks.append({"type": "text", "text": response.content})
    for tc in response.tool_calls:
        blocks.append({
            "type": "tool_use",
            "id": tc.id,
            "name": tc.name,
            "input": tc.arguments,
        })
    return blocks


def _build_tool_result(tool_call_id: str, content: str, llm: BaseLLM) -> dict[str, Any]:
    """Build a tool result block compatible with the LLM backend."""
    if isinstance(llm, ClaudeLLM):
        return llm.make_tool_result_message(tool_call_id, content)
    # OpenAI-compatible format
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }


def _fmt_args(args: dict[str, Any]) -> str:
    parts = []
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 40:
            parts.append(f"{k}={v[:40]!r}…")
        else:
            parts.append(f"{k}={v!r}")
    return ", ".join(parts)


class MultiAgent:
    """Orchestrator that runs multiple sub-agents in sequence or parallel."""

    def __init__(self, llm: BaseLLM, tools: list[dict[str, Any]]) -> None:
        self.llm = llm
        self.tools = tools

    def run_parallel(
        self,
        tasks: list[tuple[str, str]],  # (agent_name, task)
        system: str = "",
        console: Console | None = None,
    ) -> list[str]:
        """Run multiple agents on independent tasks (sequentially for now)."""
        results = []
        for name, task in tasks:
            if console:
                console.print(f"\n[bold cyan][ {name} ][/bold cyan]")
            agent = Agent(self.llm, self.tools, system=system, name=name)
            results.append(agent.run(task, console=console))
        return results
