"""
/autoresearch — Autonomous loop: hypothesize → search → analyze → refine.

Runs a self-directed research loop that:
  1. Forms an initial hypothesis from the seed idea
  2. Searches ADS to find supporting/refuting evidence
  3. Refines the hypothesis based on findings
  4. Repeats until convergence or --max-rounds reached
  5. Writes a final research report
"""

from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from ..agent import Agent
from ..llm import get_llm, BaseLLM
from ..output import slugify, write_output
from ..tools import ADS_TOOLS, WEB_TOOLS


_HYPOTHESIS_SYSTEM = """\
You are a creative astrophysics researcher forming and refining hypotheses.

Given a research idea and (optionally) prior findings, respond with ONLY a JSON object:
{
  "hypothesis": "<clear, testable hypothesis statement>",
  "predictions": ["<prediction 1>", "<prediction 2>", ...],
  "search_queries": ["<ADS query 1>", "<ADS query 2>", "<ADS query 3>"],
  "converged": false
}

Set "converged": true when the hypothesis is well-supported or refuted by evidence
and further searching is unlikely to change the conclusion.
"""

_INVESTIGATOR_SYSTEM = """\
You are a rigorous astrophysics investigator testing a specific hypothesis.

Given a hypothesis and search queries:
1. Run each search query on NASA ADS
2. Fetch abstracts of the most relevant papers (top 5-8)
3. Assess each paper: does it SUPPORT, REFUTE, or is NEUTRAL to the hypothesis?
4. Summarize the evidence and suggest how to refine the hypothesis

Output:
## Evidence Found
<paper summaries with stance>

## Assessment
SUPPORTED / REFUTED / MIXED / INSUFFICIENT EVIDENCE

## Key Insight
<1-2 sentences on the most important finding>

## Suggested Refinements
<how to update the hypothesis based on this evidence>
"""

_REPORT_SYSTEM = """\
You are a scientific writer producing a final research report.

Given a research idea and the full history of hypothesis iterations and evidence,
write a structured research report:

# Auto-Research Report: <idea>

## Executive Summary
## Initial Hypothesis
## Research Iterations
<for each round: hypothesis → evidence → refinement>
## Final Hypothesis
## Supporting Evidence
## Contradicting Evidence
## Conclusions
## Future Directions
## References (BibTeX)
"""


def run(idea: str, max_rounds: int, console: Console, extra_context: str = "") -> None:
    console.print(Panel(f"[bold]Auto-Research[/bold]: {idea}", style="cyan"))
    llm = get_llm()

    history = []
    current_findings = ""

    for round_num in range(1, max_rounds + 1):
        console.print(Rule(f"Round {round_num}/{max_rounds}"))

        # Step 1 — form/refine hypothesis
        hyp_agent = Agent(llm, [], system=_HYPOTHESIS_SYSTEM, name="Hypothesis")
        hyp_prompt = f"Research idea: {idea}"
        if extra_context:
            hyp_prompt += f"\n\nAdditional context from user:\n{extra_context}"
        if current_findings:
            hyp_prompt += f"\n\nPrior findings:\n{current_findings}"

        raw = hyp_agent.run(hyp_prompt, console=console)
        try:
            hyp_data = json.loads(_extract_json(raw))
        except Exception:
            console.print(f"[yellow]Could not parse hypothesis JSON, using raw output[/yellow]")
            hyp_data = {"hypothesis": raw, "predictions": [], "search_queries": [idea], "converged": False}

        hypothesis = hyp_data.get("hypothesis", raw)
        queries = hyp_data.get("search_queries", [idea])
        converged = hyp_data.get("converged", False)

        console.print(f"\n[bold]Hypothesis:[/bold] {hypothesis}")

        # Step 2 — investigate
        inv_agent = Agent(llm, ADS_TOOLS + WEB_TOOLS, system=_INVESTIGATOR_SYSTEM, name="Investigator")
        inv_prompt = (
            f"Hypothesis: {hypothesis}\n"
            f"Test using these search queries: {queries}\n"
            f"Predictions to check: {hyp_data.get('predictions', [])}"
        )
        findings = inv_agent.run(inv_prompt, console=console)
        current_findings = findings

        history.append({
            "round": round_num,
            "hypothesis": hypothesis,
            "findings": findings,
            "converged": converged,
        })

        if converged:
            console.print(f"\n[green]Converged after {round_num} rounds.[/green]")
            break

    # Write final report
    console.print(Rule("Writing final report"))
    history_text = "\n\n---\n\n".join(
        f"**Round {h['round']}**\nHypothesis: {h['hypothesis']}\n\nFindings:\n{h['findings']}"
        for h in history
    )
    report_agent = Agent(llm, ADS_TOOLS, system=_REPORT_SYSTEM, name="Reporter")
    report = report_agent.run(
        f"Research idea: {idea}\n\nFull research history:\n\n{history_text}",
        console=console,
    )

    slug = slugify(idea)
    path = write_output(
        slug=slug,
        artifact_type="autoresearch",
        content=report,
        workflow="/autoresearch",
    )
    console.print(f"\n[green]✓[/green] Saved to [bold]{path}[/bold]")


def _extract_json(text: str) -> str:
    """Extract first JSON block from text."""
    import re
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return m.group(1)
    # Try to find raw JSON object
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return m.group(0)
    return text
