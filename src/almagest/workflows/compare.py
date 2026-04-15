"""
/compare — Side-by-side source comparison with agreement and conflict matrix.

Compares multiple papers or approaches on a topic and produces:
  - Agreement matrix
  - Conflict points
  - Methodological differences
  - Recommendation
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from ..agent import Agent
from ..llm import get_llm
from ..output import slugify, write_output
from ..tools import ADS_TOOLS, WEB_TOOLS


_SYSTEM = """\
You are a scientific analyst comparing competing theories, methods, or results in astrophysics.

Your comparison process:
1. Search ADS for papers on both sides of the topic
2. Identify the key claims and results of each approach/paper
3. Fetch abstracts and details for the main papers
4. Systematically compare them across multiple dimensions

Output format:

## Overview
<brief description of what is being compared>

## Papers Compared
<table: bibcode | authors | year | approach/position | citations>

## Comparison Matrix
<table with rows = dimensions (method, data, result, assumptions, etc.)
 and columns = each approach/paper>

## Points of Agreement
<bullet list with citations>

## Points of Conflict
<bullet list, each with:
  - Claim A (bibcode) vs Claim B (bibcode)
  - Nature of conflict
  - Current state of evidence>

## Methodological Differences
<key differences in approach that explain disagreements>

## Verdict
<which approach has stronger evidence, or if the question is unresolved>

## Open Questions
<what would resolve the remaining conflicts>
"""


def run(topic: str, console: Console, extra_context: str = "") -> None:
    console.print(Panel(f"[bold]Compare[/bold]: {topic}", style="yellow"))
    llm = get_llm()

    agent = Agent(llm, ADS_TOOLS + WEB_TOOLS, system=_SYSTEM, name="Comparator")
    console.print(Rule("Building comparison matrix"))

    result = agent.run(
        f"Produce a side-by-side comparison of the main approaches/results on: {topic}",
        console=console,
        extra_context=extra_context,
    )

    slug = slugify(topic)
    path = write_output(
        slug=slug,
        artifact_type="comparison",
        content=f"# Comparison: {topic}\n\n{result}",
        workflow="/compare",
    )
    console.print(f"\n[green]✓[/green] Saved to [bold]{path}[/bold]")
