"""
/review — Simulated peer review with severity scores and a revision plan.

Accepts either an ADS bibcode, a local PDF path, or both.

Output:
  - Summary of the paper
  - Strengths
  - Weaknesses (scored: critical / major / minor / cosmetic)
  - Missing citations
  - Statistical/methodological concerns
  - Actionable revision plan
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from ..agent import Agent
from .. import ads_client
from ..llm import get_llm
from ..output import slugify, write_output
from ..tools import ADS_TOOLS, WEB_TOOLS, extract_pdf_text


_SYSTEM_BIBCODE = """\
You are an expert peer reviewer for high-impact astrophysics journals (ApJ, MNRAS, A&A).

Your review process:
1. Fetch the paper metadata and abstract from ADS
2. Search for related work the authors may have missed
3. Get the paper's references to understand what they cite
4. Search for any known replication issues or follow-up papers

Your review must include:

## Summary
<2-3 sentences on the paper's claim and approach>

## Recommendation
ACCEPT / MINOR REVISION / MAJOR REVISION / REJECT (choose one)

## Strengths
<bullet list>

## Weaknesses
Each issue labeled:
- [CRITICAL] — fatal flaw, paper cannot be accepted without addressing this
- [MAJOR] — significant concern requiring new analysis or rewriting
- [MINOR] — can be addressed with moderate effort
- [COSMETIC] — style/clarity, no re-analysis needed

## Missing Citations
<list key papers that should have been cited, with ADS bibcodes>

## Statistical / Methodological Concerns
<specific issues with methods, statistics, data quality>

## Revision Plan
<numbered actionable steps the authors should take>

Be rigorous but fair. Cite specific claims from the abstract to support your critique.
"""

_SYSTEM_PDF = """\
You are an expert peer reviewer for high-impact astrophysics journals (ApJ, MNRAS, A&A).

The full text of the paper is provided directly in the user message.

Your review process:
1. Read the provided paper text carefully
2. Search NASA ADS for related work the authors may have missed
3. Search ADS for the papers cited in the reference list to verify they exist and support the claims
4. Look for any follow-up or conflicting papers published after this one

Your review must include:

## Summary
<2-3 sentences on the paper's claim and approach>

## Recommendation
ACCEPT / MINOR REVISION / MAJOR REVISION / REJECT (choose one)

## Strengths
<bullet list>

## Weaknesses
Each issue labeled:
- [CRITICAL] — fatal flaw, paper cannot be accepted without addressing this
- [MAJOR] — significant concern requiring new analysis or rewriting
- [MINOR] — can be addressed with moderate effort
- [COSMETIC] — style/clarity, no re-analysis needed

## Missing Citations
<list key papers that should have been cited, with ADS bibcodes>

## Statistical / Methodological Concerns
<specific issues with methods, statistics, data quality>

## Revision Plan
<numbered actionable steps the authors should take>

Be rigorous but fair. Quote specific sentences from the paper to support your critique.
"""


def run(
    bibcode: str | None,
    console: Console,
    pdf_path: str | None = None,
    extra_context: str = "",
) -> None:
    label = bibcode or Path(pdf_path).name if pdf_path else "?"
    console.print(Panel(f"[bold]Peer Review[/bold]: {label}", style="yellow"))
    llm = get_llm()

    title = label
    sources = []
    pdf_text = None

    # --- Extract PDF text if provided ---
    if pdf_path:
        console.print(f"Reading PDF: [dim]{pdf_path}[/dim]")
        try:
            pdf_text = extract_pdf_text(pdf_path)
            console.print(f"  [dim]{len(pdf_text):,} chars extracted[/dim]")
        except Exception as e:
            console.print(f"[red]Error reading PDF: {e}[/red]")
            return

    # --- Fetch ADS metadata if bibcode provided ---
    if bibcode:
        try:
            paper = ads_client.get_paper(bibcode)
            title = (paper.get("title") or ["?"])[0]
            sources.append(bibcode)
            console.print(f"Reviewing: [italic]{title}[/italic]")
        except Exception as e:
            console.print(f"[yellow]Warning: could not fetch ADS metadata: {e}[/yellow]")

    # --- Build task prompt ---
    if pdf_text and bibcode:
        # Combined: both PDF text and ADS bibcode
        system = _SYSTEM_PDF
        task = (
            f"Review this paper (bibcode: {bibcode}).\n\n"
            f"Full paper text:\n\n{pdf_text}"
        )
    elif pdf_text:
        # PDF only
        system = _SYSTEM_PDF
        task = f"Review this paper.\n\nFull paper text:\n\n{pdf_text}"
        title = Path(pdf_path).stem  # use filename as title
    else:
        # Bibcode only (original behaviour)
        system = _SYSTEM_BIBCODE
        task = f"Conduct a rigorous peer review of this paper: {bibcode}"

    agent = Agent(llm, ADS_TOOLS + WEB_TOOLS, system=system, name="PeerReviewer")
    console.print(Rule("Conducting peer review"))

    result = agent.run(task, console=console, extra_context=extra_context)

    slug = slugify(title)
    header_lines = [f"# Peer Review: {title}"]
    if bibcode:
        header_lines.append(f"\n**Bibcode**: {bibcode}")
    if pdf_path:
        header_lines.append(f"**Source PDF**: {pdf_path}")

    path = write_output(
        slug=slug,
        artifact_type="peer-review",
        content="\n".join(header_lines) + "\n\n" + result,
        sources=sources,
        workflow="/review",
    )
    console.print(f"\n[green]✓[/green] Saved to [bold]{path}[/bold]")
