"""
/lit — Literature review from primary sources with consensus mapping.

Produces:
  - Overview of the field
  - Key papers and their contributions
  - Consensus points
  - Active debates / open questions
  - Research gaps
  - Recommended reading path
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
You are an expert astrophysicist tasked with writing a comprehensive literature review.

Process:
1. Search NASA ADS broadly for the topic (at least 4 queries varying the approach)
2. Identify the 10-20 most influential papers by citation count and recency
3. Fetch abstracts for all key papers
4. Search for review articles specifically (use "doctype:review" or "title:review")
5. Identify the founding papers, major milestones, and recent developments

Output format (Markdown):
# Literature Review: <topic>

## Overview
<2-3 paragraph field overview>

## Key Papers
<table or list: bibcode | authors | year | contribution | citations>

## Consensus
<points where the community agrees>

## Active Debates
<open questions, competing theories, unresolved tensions>

## Research Gaps
<what is not yet known or studied>

## Recommended Reading Path
<ordered list for someone new to the field>

## Full Bibliography
<BibTeX block>

Always include bibcode citations inline as (Author et al. YEAR, bibcode).
"""


def run(topic: str, console: Console, extra_context: str = "") -> None:
    console.print(Panel(f"[bold]Literature Review[/bold]: {topic}", style="green"))
    llm = get_llm()

    agent = Agent(llm, ADS_TOOLS + WEB_TOOLS, system=_SYSTEM, name="LitReviewer")
    console.print(Rule("Surveying the literature"))

    result = agent.run(
        f"Write a comprehensive literature review on: {topic}",
        console=console,
        extra_context=extra_context,
    )

    slug = slugify(topic)
    path = write_output(
        slug=slug,
        artifact_type="lit-review",
        content=result,
        workflow="/lit",
    )
    console.print(f"\n[green]✓[/green] Saved to [bold]{path}[/bold]")
