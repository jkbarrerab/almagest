"""
/coauthor — Friendly co-author review of a draft, delivered as an email.

Accepts either an ADS bibcode, a local PDF path, or both.
The agent reads the paper as a trusted collaborator and writes a warm,
personal email to the authors with honest feedback and encouragement.

Output:
  - A Markdown file formatted as an email
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
You are a trusted co-author and collaborator who has been asked to read a draft
before submission and share your thoughts by email.

Your process:
1. Fetch the paper metadata and abstract from ADS
2. Search for related work that should be discussed or cited
3. Get the paper's references to understand the context
4. Write a friendly, personal email to the authors with your feedback

Write the output as a Markdown email with this structure:

---
**To:** [Author names, or "Dear colleagues" if unknown]
**From:** [Your name as collaborator]
**Subject:** Re: [paper title]

---

[Body of the email — warm, personal, honest. Use paragraphs, not bullet lists.
Cover: overall impression, what works well, specific concerns (explained clearly
but kindly), any missing references worth adding, and an encouraging close.]

Keep the tone of a colleague who wants the paper to succeed.
Do not use journal-referee severity labels (CRITICAL, MAJOR, etc.).
"""

_SYSTEM_PDF = """\
You are a trusted co-author and collaborator who has been asked to read a draft
before submission and share your thoughts by email.

The full text of the paper is provided directly in the user message.

Your process:
1. Read the provided paper text carefully
2. Search NASA ADS for related work that should be discussed or cited
3. Check key claims against the literature
4. Write a friendly, personal email to the authors with your feedback

Write the output as a Markdown email with this structure:

---
**To:** [Author names if visible in the text, otherwise "Dear colleagues"]
**From:** [Your name as collaborator]
**Subject:** Re: [paper title]

---

[Body of the email — warm, personal, honest. Use paragraphs, not bullet lists.
Cover: overall impression, what works well, specific concerns (explained clearly
but kindly, quoting the relevant passage when helpful), any missing references
worth adding, and an encouraging close.]

Keep the tone of a colleague who wants the paper to succeed.
Do not use journal-referee severity labels (CRITICAL, MAJOR, etc.).
"""


def run(
    bibcode: str | None,
    console: Console,
    pdf_path: str | None = None,
    extra_context: str = "",
) -> None:
    label = bibcode or (Path(pdf_path).name if pdf_path else "?")
    console.print(Panel(f"[bold]Co-author Review[/bold]: {label}", style="cyan"))
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
            console.print(f"Reading: [italic]{title}[/italic]")
        except Exception as e:
            console.print(f"[yellow]Warning: could not fetch ADS metadata: {e}[/yellow]")

    # --- Build task ---
    if pdf_text and bibcode:
        system = _SYSTEM_PDF
        task = (
            f"Write a friendly co-author review email for this paper (bibcode: {bibcode}).\n\n"
            f"Full paper text:\n\n{pdf_text}"
        )
    elif pdf_text:
        system = _SYSTEM_PDF
        task = f"Write a friendly co-author review email for this paper.\n\nFull paper text:\n\n{pdf_text}"
        title = Path(pdf_path).stem
    else:
        system = _SYSTEM_BIBCODE
        task = f"Write a friendly co-author review email for this paper: {bibcode}"

    agent = Agent(llm, ADS_TOOLS + WEB_TOOLS, system=system, name="CoAuthor")
    console.print(Rule("Reading draft"))

    result = agent.run(task, console=console, extra_context=extra_context)

    slug = slugify(title)
    path = write_output(
        slug=slug,
        artifact_type="coauthor-review",
        content=result,
        sources=sources,
        workflow="/coauthor",
    )
    console.print(f"\n[green]✓[/green] Saved to [bold]{path}[/bold]")
