"""
/audit — Paper-to-code mismatch audit for reproducibility.

Checks whether the code linked in the paper (GitHub, Zenodo, CDS, etc.)
matches the claims, parameters, and methods described in the abstract/paper.

Output:
  - Claimed methods vs. implemented methods
  - Parameter values: paper vs. code
  - Missing functionality
  - Reproducibility verdict
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from ..agent import Agent
from .. import ads_client
from ..llm import get_llm
from ..output import slugify, write_output
from ..tools import ALL_TOOLS


_SYSTEM = """\
You are a reproducibility auditor for astrophysics research.

Your task:
1. Fetch the paper from ADS and extract all claims about:
   - Methods and algorithms
   - Parameter values and thresholds
   - Data products used
   - Software versions mentioned
2. Find any linked code repositories:
   - Check paper identifiers for GitHub/Zenodo links
   - Search for "bibcode ascl:" or "property:software" entries
   - Use fetch_url to retrieve README and key source files
3. Compare paper claims to code implementation:
   - Are all described methods implemented?
   - Do parameter values match?
   - Are data inputs/outputs consistent?
4. Run the bash tool to inspect code if repos are cloned

Output format:

## Paper Claims
<table: Claim | Location in paper | Verification status>

## Code Findings
<what was found in the code repo(s)>

## Mismatches
Each issue with severity:
- [CRITICAL] — results cannot be reproduced
- [SIGNIFICANT] — substantial deviation from paper
- [MINOR] — small discrepancy, unlikely to affect results
- [OK] — claim verified in code

## Reproducibility Verdict
REPRODUCIBLE / PARTIALLY REPRODUCIBLE / NOT REPRODUCIBLE / CANNOT ASSESS

## Recommendations
<steps to improve reproducibility>

Be precise: quote specific line numbers or function names when referencing code.
"""


def run(bibcode: str, console: Console, extra_context: str = "") -> None:
    console.print(Panel(f"[bold]Reproducibility Audit[/bold]: {bibcode}", style="magenta"))
    llm = get_llm()

    try:
        paper = ads_client.get_paper(bibcode)
        title = (paper.get("title") or ["?"])[0]
        console.print(f"Auditing: [italic]{title}[/italic]")
    except Exception as e:
        console.print(f"[yellow]Warning: {e}[/yellow]")
        title = bibcode

    agent = Agent(llm, ALL_TOOLS, system=_SYSTEM, name="ReproAuditor")
    console.print(Rule("Running reproducibility audit"))

    result = agent.run(
        f"Audit the reproducibility of this paper: {bibcode}\n"
        f"Find any associated code repositories and compare claims to implementation.",
        console=console,
        extra_context=extra_context,
    )

    slug = slugify(title if title != bibcode else bibcode)
    path = write_output(
        slug=slug,
        artifact_type="audit",
        content=f"# Reproducibility Audit: {title}\n\n**Bibcode**: {bibcode}\n\n{result}",
        sources=[bibcode],
        workflow="/audit",
    )
    console.print(f"\n[green]✓[/green] Saved to [bold]{path}[/bold]")
