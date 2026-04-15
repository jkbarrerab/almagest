"""
/replicate — Replication plan and execution in a sandboxed environment.

Steps:
  1. Parse the paper's methods and data requirements
  2. Generate a step-by-step replication plan
  3. Optionally scaffold and execute code in Docker
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from ..agent import Agent
from .. import ads_client
from ..llm import get_llm
from ..output import slugify, write_output
from ..tools import ALL_TOOLS


_SYSTEM = """\
You are an expert astrophysicist and software engineer specializing in reproducing published results.

Your replication process:
1. Fetch the paper from ADS and extract:
   - Key observational/simulation results to reproduce
   - Data sources (telescope/survey, data release, filters)
   - Software and methods used
   - Key figures and their data
2. Search ADS for any public data associated with this paper (CDS, MAST, ESO, etc.)
3. Check for existing code repositories
4. Create a detailed, step-by-step replication plan

Replication plan format:

## Paper Summary
<1 paragraph on what needs to be replicated>

## Data Requirements
<data products needed, sources, access instructions>

## Software Dependencies
<packages, versions, environment setup>

## Replication Steps
Numbered steps, each with:
- What to do
- Expected output
- Verification criterion

## Docker Environment
<Dockerfile snippet for the environment>

## Key Figures to Reproduce
<list the main figures/tables and what produces them>

## Estimated Complexity
TRIVIAL / MODERATE / COMPLEX / VERY COMPLEX

If the user asks to execute, use the bash tool to:
- Clone repositories
- Set up environment
- Run key scripts
"""


def run(bibcode: str, execute: bool, console: Console, extra_context: str = "") -> None:
    label = "Replication Plan + Execute" if execute else "Replication Plan"
    console.print(Panel(f"[bold]{label}[/bold]: {bibcode}", style="blue"))
    llm = get_llm()

    try:
        paper = ads_client.get_paper(bibcode)
        title = (paper.get("title") or ["?"])[0]
        console.print(f"Planning replication of: [italic]{title}[/italic]")
    except Exception as e:
        console.print(f"[yellow]Warning: {e}[/yellow]")
        title = bibcode

    exec_instruction = ""
    if execute:
        exec_instruction = (
            "\n\nAfter creating the plan, USE THE BASH TOOL to begin execution: "
            "clone any repositories, set up the environment, and run the first steps."
        )

    agent = Agent(llm, ALL_TOOLS, system=_SYSTEM, name="Replicator")
    console.print(Rule("Building replication plan"))

    result = agent.run(
        f"Create a detailed replication plan for: {bibcode}{exec_instruction}",
        console=console,
        extra_context=extra_context,
    )

    slug = slugify(title if title != bibcode else bibcode)
    path = write_output(
        slug=slug,
        artifact_type="replication",
        content=f"# Replication Plan: {title}\n\n**Bibcode**: {bibcode}\n\n{result}",
        sources=[bibcode],
        workflow="/replicate",
    )
    console.print(f"\n[green]✓[/green] Saved to [bold]{path}[/bold]")
