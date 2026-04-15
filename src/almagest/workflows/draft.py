"""
/draft — Polished paper-style draft with inline citations from findings.

Produces a full paper-style draft (not submission-ready, but well-structured)
with inline ADS citations, suitable as a starting point for a real paper.
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
You are a scientific writer producing an astrophysics paper draft.

Research process:
1. Search ADS extensively for papers on the topic (at least 5 searches)
2. Identify key results, methods, and open questions
3. Fetch abstracts of the 15-25 most relevant papers
4. Find any recent review papers for context
5. Retrieve BibTeX entries for all cited papers

Draft structure (LaTeX-friendly Markdown):

# <Title>

**Abstract**: <150-250 words>

## 1. Introduction
<motivation, context, what this paper addresses>
<cite key background papers with (Author et al. YEAR)>

## 2. Background / Previous Work
<summary of relevant prior work with citations>

## 3. Methods
<proposed approach or analysis>

## 4. Results
<main findings, with reference to hypothetical figures/tables>

## 5. Discussion
<interpretation, comparison to prior work>

## 6. Conclusions
<summary and future directions>

## References
<BibTeX block with all cited papers>

Style: Write in the style of an ApJ or MNRAS paper.
Every factual claim must have a citation. Mark speculative content with [INFERRED].
"""


def run(topic: str, console: Console, extra_context: str = "") -> None:
    console.print(Panel(f"[bold]Draft[/bold]: {topic}", style="green"))
    llm = get_llm()

    agent = Agent(llm, ADS_TOOLS + WEB_TOOLS, system=_SYSTEM, name="Writer")
    console.print(Rule("Researching and drafting"))

    result = agent.run(
        f"Write a polished paper-style draft on: {topic}\n"
        f"Research the topic thoroughly before writing.",
        console=console,
        extra_context=extra_context,
    )

    slug = slugify(topic)
    path = write_output(
        slug=slug,
        artifact_type="draft",
        content=result,
        workflow="/draft",
    )
    console.print(f"\n[green]✓[/green] Saved to [bold]{path}[/bold]")
