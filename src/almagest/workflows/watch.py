"""
/watch — Recurring monitor for new papers, code, or updates on a topic.

Runs a saved search on ADS on a schedule (using system cron or a simple loop)
and reports new papers since the last check.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from .. import ads_client, config
from ..agent import Agent
from ..llm import get_llm
from ..output import slugify
from ..tools import ADS_TOOLS

_WATCHES_FILE = Path.home() / ".almagest" / "watches.json"

_DIGEST_SYSTEM = """\
You are a research monitor writing a concise digest of new astronomy papers.

Given a list of new papers on a topic, write a brief digest:
- Group papers by sub-topic if there are many
- Highlight the most impactful ones (by citation count or novelty)
- Flag any papers that are especially relevant or surprising
- Keep it under 500 words

Format as Markdown suitable for a quick read.
"""


def _load_watches() -> dict:
    if _WATCHES_FILE.exists():
        return json.loads(_WATCHES_FILE.read_text())
    return {}


def _save_watches(watches: dict) -> None:
    _WATCHES_FILE.parent.mkdir(parents=True, exist_ok=True)
    _WATCHES_FILE.write_text(json.dumps(watches, indent=2))


def add_watch(topic: str, query: str | None, console: Console) -> None:
    """Register a new watch."""
    watches = _load_watches()
    slug = slugify(topic)
    search_query = query or topic
    watches[slug] = {
        "topic": topic,
        "query": search_query,
        "last_checked": None,
        "known_bibcodes": [],
        "added": datetime.now(timezone.utc).isoformat(),
    }
    _save_watches(watches)
    console.print(f"[green]✓[/green] Watch added: [bold]{topic}[/bold] (query: {search_query!r})")
    console.print(f"Run [bold]almagest watch run[/bold] to check for new papers.")


def list_watches(console: Console) -> None:
    """List all registered watches."""
    watches = _load_watches()
    if not watches:
        console.print("[dim]No watches registered. Use 'almagest watch add <topic>'[/dim]")
        return

    table = Table(title="Active Watches")
    table.add_column("Slug", style="cyan")
    table.add_column("Topic")
    table.add_column("Query", style="dim")
    table.add_column("Last checked", style="dim")
    for slug, w in watches.items():
        last = w.get("last_checked") or "never"
        table.add_row(slug, w["topic"], w["query"], last)
    console.print(table)


def remove_watch(slug: str, console: Console) -> None:
    watches = _load_watches()
    if slug not in watches:
        console.print(f"[red]Watch not found: {slug}[/red]")
        return
    del watches[slug]
    _save_watches(watches)
    console.print(f"[green]✓[/green] Removed watch: {slug}")


def run_watches(console: Console, digest: bool) -> None:
    """Check all watches for new papers."""
    watches = _load_watches()
    if not watches:
        console.print("[dim]No watches to run.[/dim]")
        return

    llm = get_llm() if digest else None
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    any_new = False
    for slug, w in watches.items():
        console.print(Rule(f"Checking: {w['topic']}"))

        # Build a date-filtered query to find recent papers
        query = w["query"]
        last = w.get("last_checked")
        if last:
            year = last[:4]
            query = f"({query}) pubdate:[{year} TO *]"

        try:
            papers = ads_client.search(query, limit=20, sort="date desc")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            continue

        known = set(w.get("known_bibcodes", []))
        new_papers = [p for p in papers if p["bibcode"] not in known]

        if not new_papers:
            console.print(f"  [dim]No new papers.[/dim]")
        else:
            any_new = True
            console.print(f"  [green]{len(new_papers)} new paper(s)[/green]")
            for p in new_papers:
                console.print(f"  • {ads_client.format_paper_summary(p)}")

            if digest and llm and new_papers:
                paper_list = "\n".join(ads_client.format_paper_summary(p) for p in new_papers)
                agent = Agent(llm, ADS_TOOLS, system=_DIGEST_SYSTEM, name="Digest")
                d = agent.run(
                    f"Topic: {w['topic']}\n\nNew papers:\n{paper_list}",
                    console=console,
                )
                digest_path = config.output_dir() / f"{slug}-digest-{today}.md"
                digest_path.write_text(
                    f"# Watch Digest: {w['topic']}\n\n**Date**: {today}\n\n{d}",
                    encoding="utf-8",
                )
                console.print(f"  Digest saved to [bold]{digest_path}[/bold]")

            # Update known bibcodes
            watches[slug]["known_bibcodes"] = list(
                known | {p["bibcode"] for p in papers}
            )

        watches[slug]["last_checked"] = now.isoformat()

    _save_watches(watches)
    if not any_new:
        console.print("\n[dim]All watches are up to date.[/dim]")
