"""
/source — Literature search and analysis for a specific astronomical source.

Accepts:
  - A named object (NGC 1068, M87, Crab Nebula, 3C 273, …)
  - A sky position + radius (RA/Dec in decimal degrees)
  - An optional science topic to filter results (IFU, AGN, star formation, …)

Output:
  - Object overview
  - All papers found (sorted by citations + recent)
  - Key papers table
  - Timeline of key discoveries / observations
  - Instrument & survey coverage
  - Consensus findings
  - Open questions
  - BibTeX bibliography
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
You are an expert astrophysicist performing a targeted literature search for a specific
astronomical source using NASA ADS.

Your research process:
1. **Identify the object** — use ads_search_object to find all papers about it.
   If coordinates are provided, also use ads_search_position to cross-check.
2. **Broad search first** — run ads_search_object without a topic filter to get the
   full picture (top cited + most recent papers).
3. **Topic-filtered search** — if a science topic is specified, run a second
   ads_search_object with that topic to find the most relevant papers.
4. **Fetch key abstracts** — call ads_get_paper for the top 8-10 papers to get
   full metadata and abstracts.
5. **Synthesise** — write the structured report below.

Output format (Markdown):

# Source Literature: <object name>
*Topic filter: <topic or "all"*>

## Object Overview
<What type of object is it? Distance, redshift, notable characteristics.
  Cite the defining/discovery paper.>

## Papers Found
<Total papers in ADS | papers matching topic filter>

## Key Papers
| Bibcode | Authors | Year | Topic | Citations |
|---------|---------|------|-------|-----------|
<list top 10-15 papers>

## Timeline of Key Discoveries & Observations
<Chronological bullets: year — instrument/survey — key finding — (bibcode)>

## Instrument & Survey Coverage
<Which telescopes, instruments, and surveys have observed this source?
  e.g. HST, VLT/MUSE, ALMA, Chandra, Spitzer, SDSS, etc.>

## Consensus Findings
<What is well-established about this object? Cite supporting papers.>

## Open Questions
<What remains debated or unknown?>

## Bibliography
<BibTeX block for all cited papers — use ads_export_bibtex>

Always cite with (Author et al. YEAR, `bibcode`).
"""


def run(
    name: str | None,
    console: Console,
    topic: str = "",
    ra: float | None = None,
    dec: float | None = None,
    radius_deg: float | None = None,
    extra_context: str = "",
) -> None:
    # Build display label
    if name:
        label = name + (f" — {topic}" if topic else "")
    else:
        radius_arcmin = (radius_deg or 0.0333) * 60
        label = f"RA={ra:.4f} Dec={dec:+.4f} r={radius_arcmin:.1f}′"
        if topic:
            label += f" — {topic}"

    console.print(Panel(f"[bold]Source Literature[/bold]: {label}", style="cyan"))
    llm = get_llm()

    # Build the task prompt
    task_parts = []
    if name:
        task_parts.append(f"Astronomical object: {name}")
    if topic:
        task_parts.append(f"Science topic filter: {topic}")
    if ra is not None and dec is not None:
        radius_arcmin = (radius_deg or 0.0333) * 60
        task_parts.append(
            f"Sky position: RA={ra:.6f}°, Dec={dec:+.6f}°, radius={radius_arcmin:.2f} arcmin "
            f"(={radius_deg:.6f} deg)"
        )
    task_parts.append(
        "Search NASA ADS thoroughly, fetch key abstracts, and write the full structured report."
    )
    task = "\n".join(task_parts)

    agent = Agent(llm, ADS_TOOLS + WEB_TOOLS, system=_SYSTEM, name="SourceSearcher")
    console.print(Rule("Searching literature"))

    result = agent.run(task, console=console, extra_context=extra_context)

    slug = slugify(name or f"ra{ra:.2f}dec{dec:+.2f}")
    if topic:
        slug = slug + "-" + slugify(topic)

    sources = [name] if name else []
    path = write_output(
        slug=slug,
        artifact_type="source-lit",
        content=result,
        sources=sources,
        workflow="/source",
    )
    console.print(f"\n[green]✓[/green] Saved to [bold]{path}[/bold]")
