"""
/deepresearch — Multi-agent investigation across papers, web, and code.

Architecture:
  1. Planner  → breaks the topic into 3-5 research questions
  2. Researchers (one per question) → gather evidence from ADS
  3. Synthesizer → merges findings, resolves conflicts, writes the brief
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from ..agent import Agent, MultiAgent
from ..llm import get_llm
from ..output import slugify, write_output
from ..tools import ALL_TOOLS, ADS_TOOLS, WEB_TOOLS


_PLANNER_SYSTEM = """\
You are a research planner for astronomy and astrophysics.
Given a research topic, produce a JSON list of 3-5 focused research questions
that together cover the topic comprehensively.
Respond ONLY with a valid JSON array of strings, nothing else.
Example: ["What are the main formation mechanisms of X?", "How does Y evolve over time?"]
"""

_RESEARCHER_SYSTEM = """\
You are an expert astrophysics researcher with deep knowledge of the NASA ADS database.
Your job is to answer a specific research question by:
1. Searching NASA ADS for relevant papers (use multiple targeted queries)
2. Fetching abstracts and key details of the top papers
3. Synthesizing the evidence into a concise answer with inline citations (bibcodes)

Always cite your sources as [Author et al. YEAR](bibcode).
Be thorough: run at least 3 different search queries before concluding.
"""

_SYNTHESIZER_SYSTEM = """\
You are a scientific writer synthesizing research findings from multiple investigators.
You receive a set of research question → findings pairs and must produce:
1. An executive summary (2-3 paragraphs)
2. Key findings per question with supporting evidence
3. Areas of consensus
4. Open questions and disagreements
5. A bibliography (BibTeX format)

Format as clean Markdown. Include all bibcodes as inline citations.
"""


def run(topic: str, console: Console, extra_context: str = "") -> None:
    console.print(Panel(f"[bold]Deep Research[/bold]: {topic}", style="cyan"))
    llm = get_llm()
    multi = MultiAgent(llm, ALL_TOOLS)

    # Step 1 — plan
    console.print(Rule("Planning research questions"))
    planner = Agent(llm, [], system=_PLANNER_SYSTEM, name="Planner")
    import json
    raw = planner.run(f"Topic: {topic}", console=console)
    try:
        questions = json.loads(raw.strip())
        if not isinstance(questions, list):
            questions = [topic]
    except Exception:
        questions = [topic]

    for i, q in enumerate(questions, 1):
        console.print(f"  [green]{i}.[/green] {q}")

    # Step 2 — research each question
    console.print(Rule("Running researchers"))
    tasks = [(f"Researcher {i+1}", q) for i, q in enumerate(questions)]
    findings = multi.run_parallel(tasks, system=_RESEARCHER_SYSTEM, console=console)

    # Step 3 — synthesize
    console.print(Rule("Synthesizing findings"))
    synthesis_input = "\n\n---\n\n".join(
        f"**Research Question {i+1}**: {q}\n\n**Findings**:\n{f}"
        for i, (q, f) in enumerate(zip(questions, findings))
    )
    synth = Agent(llm, ADS_TOOLS + WEB_TOOLS, system=_SYNTHESIZER_SYSTEM, name="Synthesizer")
    brief = synth.run(
        f"Synthesize these research findings on: {topic}\n\n{synthesis_input}",
        console=console,
        extra_context=extra_context,
    )

    # Save output
    slug = slugify(topic)
    path = write_output(
        slug=slug,
        artifact_type="deep-research",
        content=f"# Deep Research: {topic}\n\n{brief}",
        workflow="/deepresearch",
    )
    console.print(f"\n[green]✓[/green] Saved to [bold]{path}[/bold]")
    console.print(brief[:1000] + ("..." if len(brief) > 1000 else ""))
