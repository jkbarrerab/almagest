"""Main CLI entry point — all 9 workflows as Click commands."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()

LOGO = """[bold cyan]
   ╔═╗╦  ╔╦╗╔═╗╔═╗╔═╗╔═╗╔╦╗
   ╠═╣║  ║║║╠═╣║ ╦║╣ ╚═╗ ║
   ╩ ╩╩═╝╩ ╩╩ ╩╚═╝╚═╝╚═╝ ╩
[/bold cyan][dim]  AI research agent for NASA ADS[/dim]
"""

# ---------------------------------------------------------------------------
# Reusable context options (applied to all workflow commands)
# ---------------------------------------------------------------------------

_context_options = [
    click.option(
        "--context", "extra_context",
        default=None,
        metavar="TEXT",
        help="Extra instructions or notes passed to the agent (inline text).",
    ),
    click.option(
        "--context-file",
        type=click.Path(exists=True, dir_okay=False),
        default=None,
        metavar="PATH",
        help="Path to a .txt or .md file whose content is passed to the agent.",
    ),
]


def with_context_options(fn):
    """Decorator that adds --context and --context-file to a Click command."""
    for opt in reversed(_context_options):
        fn = opt(fn)
    return fn


def resolve_context(extra_context: str | None, context_file: str | None) -> str:
    """Merge --context and --context-file into a single string."""
    parts = []
    if extra_context:
        parts.append(extra_context.strip())
    if context_file:
        try:
            parts.append(Path(context_file).read_text(encoding="utf-8").strip())
        except Exception as e:
            console.print(f"[yellow]Warning: could not read --context-file: {e}[/yellow]")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Main group
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option("0.1.0", prog_name="almagest")
def main(ctx: click.Context) -> None:
    """ADS Research — AI research agent for NASA Astrophysics Data System.

    \b
    Workflows:
      deepresearch  Multi-agent investigation across papers, web, and code
      lit           Literature review with consensus mapping
      source        Literature search for a specific astronomical object or position
      review        Simulated peer review with severity scores
      audit         Paper-to-code reproducibility audit
      replicate     Replication plan (and optional execution)
      compare       Side-by-side source comparison matrix
      draft         Paper-style draft with inline citations
      autoresearch  Autonomous hypothesis→search→refine loop
      watch         Recurring monitor for new papers on a topic

    \b
    All workflow commands accept --context and --context-file to pass
    extra instructions or notes to the agent.
    """
    if ctx.invoked_subcommand is None:
        console.print(LOGO)
        console.print(ctx.get_help())


# ---------------------------------------------------------------------------
# /deepresearch
# ---------------------------------------------------------------------------

@main.command()
@click.argument("topic")
@with_context_options
def deepresearch(topic: str, extra_context: str | None, context_file: str | None) -> None:
    """Multi-agent investigation across papers, web, and code.

    \b
    TOPIC: research question or subject, e.g. "dark matter halo formation"

    \b
    Examples:
      almagest deepresearch "AGN feedback quenching"
      almagest deepresearch "AGN feedback" --context "Focus on low-mass galaxies"
      almagest deepresearch "AGN feedback" --context-file my_notes.md
    """
    from .workflows import deepresearch as wf
    ctx = resolve_context(extra_context, context_file)
    _run_workflow(wf.run, topic, extra_context=ctx)


# ---------------------------------------------------------------------------
# /lit
# ---------------------------------------------------------------------------

@main.command()
@click.argument("topic")
@with_context_options
def lit(topic: str, extra_context: str | None, context_file: str | None) -> None:
    """Literature review from primary sources with consensus mapping.

    \b
    TOPIC: subject to review, e.g. "stellar feedback in dwarf galaxies"

    \b
    Examples:
      almagest lit "oxygen abundance gradients"
      almagest lit "oxygen abundance gradients" --context "Include IFU surveys only"
    """
    from .workflows import lit as wf
    ctx = resolve_context(extra_context, context_file)
    _run_workflow(wf.run, topic, extra_context=ctx)


# ---------------------------------------------------------------------------
# /review
# ---------------------------------------------------------------------------

@main.command()
@click.argument("bibcode", required=False, default=None)
@click.option(
    "--pdf",
    "pdf_path",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a local PDF file to review.",
)
@with_context_options
def review(
    bibcode: str | None,
    pdf_path: str | None,
    extra_context: str | None,
    context_file: str | None,
) -> None:
    """Simulated peer review with severity scores and a revision plan.

    \b
    Accepts a bibcode, a local PDF, or both:
      almagest review 2023ApJ...950...72C
      almagest review --pdf /path/to/paper.pdf
      almagest review 2023ApJ...950...72C --pdf /path/to/paper.pdf

    \b
    Pass extra context to guide the review:
      almagest review --pdf paper.pdf --context "Also consider these papers:
        2021ApJ...910...72C (metallicity gradients)
        2019MNRAS.484.5230R (IFU methodology)"
      almagest review --pdf paper.pdf --context-file my_notes.md
    """
    if not bibcode and not pdf_path:
        raise click.UsageError("Provide a BIBCODE, --pdf PATH, or both.")
    _check_env()
    ctx = resolve_context(extra_context, context_file)
    from .workflows import review as wf
    try:
        wf.run(bibcode=bibcode, console=console, pdf_path=pdf_path, extra_context=ctx)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


# ---------------------------------------------------------------------------
# /audit
# ---------------------------------------------------------------------------

@main.command()
@click.argument("bibcode")
@with_context_options
def audit(bibcode: str, extra_context: str | None, context_file: str | None) -> None:
    """Paper-to-code mismatch audit for reproducibility.

    BIBCODE: ADS bibcode of the paper to audit
    """
    from .workflows import audit as wf
    ctx = resolve_context(extra_context, context_file)
    _run_workflow(wf.run, bibcode, extra_context=ctx)


# ---------------------------------------------------------------------------
# /replicate
# ---------------------------------------------------------------------------

@main.command()
@click.argument("bibcode")
@click.option("--execute", is_flag=True, default=False, help="Execute the plan in a sandboxed environment")
@with_context_options
def replicate(
    bibcode: str,
    execute: bool,
    extra_context: str | None,
    context_file: str | None,
) -> None:
    """Replication plan and execution in a sandboxed environment.

    BIBCODE: ADS bibcode of the paper to replicate
    """
    from .workflows import replicate as wf
    ctx = resolve_context(extra_context, context_file)

    def _run(topic: str, c: Console, **kwargs) -> None:
        wf.run(topic, execute=execute, console=c, extra_context=ctx)

    _run_workflow(_run, bibcode, extra_context=ctx)


# ---------------------------------------------------------------------------
# /compare
# ---------------------------------------------------------------------------

@main.command()
@click.argument("topic")
@with_context_options
def compare(topic: str, extra_context: str | None, context_file: str | None) -> None:
    """Side-by-side source comparison with agreement and conflict matrix.

    TOPIC: competing approaches or papers to compare,
           e.g. "NFW vs Einasto dark matter profiles"
    """
    from .workflows import compare as wf
    ctx = resolve_context(extra_context, context_file)
    _run_workflow(wf.run, topic, extra_context=ctx)


# ---------------------------------------------------------------------------
# /draft
# ---------------------------------------------------------------------------

@main.command()
@click.argument("topic")
@with_context_options
def draft(topic: str, extra_context: str | None, context_file: str | None) -> None:
    """Polished paper-style draft with inline citations from findings.

    TOPIC: subject to write about, e.g. "AGN feedback in galaxy clusters"
    """
    from .workflows import draft as wf
    ctx = resolve_context(extra_context, context_file)
    _run_workflow(wf.run, topic, extra_context=ctx)


# ---------------------------------------------------------------------------
# /autoresearch
# ---------------------------------------------------------------------------

@main.command()
@click.argument("idea")
@click.option("--max-rounds", default=5, show_default=True, help="Maximum hypothesis refinement rounds")
@with_context_options
def autoresearch(
    idea: str,
    max_rounds: int,
    extra_context: str | None,
    context_file: str | None,
) -> None:
    """Autonomous loop: hypothesize, search, measure, repeat.

    IDEA: seed research idea, e.g. "galaxy quenching driven by AGN feedback"
    """
    from .workflows import autoresearch as wf
    ctx = resolve_context(extra_context, context_file)

    def _run(topic: str, c: Console, **kwargs) -> None:
        wf.run(topic, max_rounds=max_rounds, console=c, extra_context=ctx)

    _run_workflow(_run, idea, extra_context=ctx)


# ---------------------------------------------------------------------------
# /watch
# ---------------------------------------------------------------------------

@main.group()
def watch() -> None:
    """Recurring monitor for new papers, code, or updates on a topic."""


@watch.command("add")
@click.argument("topic")
@click.option("--query", default=None, help="Custom ADS query (defaults to the topic text)")
def watch_add(topic: str, query: str | None) -> None:
    """Add a new paper watch for TOPIC."""
    from .workflows.watch import add_watch
    add_watch(topic, query, console)


@watch.command("list")
def watch_list() -> None:
    """List all registered watches."""
    from .workflows.watch import list_watches
    list_watches(console)


@watch.command("remove")
@click.argument("slug")
def watch_remove(slug: str) -> None:
    """Remove a watch by its slug."""
    from .workflows.watch import remove_watch
    remove_watch(slug, console)


@watch.command("run")
@click.option("--digest", is_flag=True, default=False, help="Generate an AI digest of new papers")
def watch_run(digest: bool) -> None:
    """Check all watches and report new papers."""
    from .workflows.watch import run_watches
    run_watches(console, digest=digest)


# ---------------------------------------------------------------------------
# /source
# ---------------------------------------------------------------------------

@main.command()
@click.argument("name", required=False, default=None)
@click.option("--topic", default="", help="Science topic filter, e.g. 'integral field spectroscopy'")
@click.option("--ra",  type=float, default=None, metavar="DEG", help="Right Ascension in decimal degrees")
@click.option("--dec", type=float, default=None, metavar="DEG", help="Declination in decimal degrees")
@click.option(
    "--radius", "radius_str", default="2arcmin", show_default=True,
    metavar="RADIUS",
    help="Search radius: '5arcmin', '30arcsec', '0.5deg', or plain number (= arcmin)",
)
@with_context_options
def source(
    name: str | None,
    topic: str,
    ra: float | None,
    dec: float | None,
    radius_str: str,
    extra_context: str | None,
    context_file: str | None,
) -> None:
    """Literature search and analysis for a specific astronomical source.

    \b
    By object name:
      almagest source "NGC 1068"
      almagest source "NGC 1068" --topic "integral field spectroscopy"
      almagest source "M87" --topic "jet kinematics"

    \b
    By sky position:
      almagest source --ra 40.669 --dec -0.014 --radius 5arcmin
      almagest source --ra 40.669 --dec -0.014 --radius 0.5deg --topic "AGN"

    \b
    With extra context:
      almagest source "NGC 1068" --topic "IFU" \\
        --context "Focus on MUSE and SINFONI observations post-2015"
    """
    if not name and (ra is None or dec is None):
        raise click.UsageError(
            "Provide an object NAME or both --ra and --dec (with optional --radius)."
        )
    _check_env()
    ctx = resolve_context(extra_context, context_file)
    radius_deg = _parse_radius_deg(radius_str)

    from .workflows import source as wf
    try:
        wf.run(
            name=name,
            console=console,
            topic=topic,
            ra=ra,
            dec=dec,
            radius_deg=radius_deg if (ra is not None and dec is not None) else None,
            extra_context=ctx,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


# ---------------------------------------------------------------------------
# Utility commands
# ---------------------------------------------------------------------------

@main.command()
@click.argument("query")
@click.option("--limit", default=10, show_default=True)
@click.option("--sort", default="citation_count desc", show_default=True)
def search(query: str, limit: int, sort: str) -> None:
    """Quick ADS paper search.

    QUERY: ADS query string
    """
    from . import ads_client
    _check_env()
    try:
        papers = ads_client.search(query, limit=limit, sort=sort)
        if not papers:
            console.print("[dim]No results.[/dim]")
            return
        console.print(f"\n[bold]{len(papers)} results[/bold] for: {query}\n")
        for p in papers:
            console.print(ads_client.format_paper_summary(p))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("bibcode")
def show(bibcode: str) -> None:
    """Show full details for an ADS bibcode."""
    from . import ads_client
    _check_env()
    try:
        paper = ads_client.get_paper(bibcode)
        console.print(ads_client.format_paper_detail(paper))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
def config_check() -> None:
    """Verify your environment is configured correctly."""
    from . import config as cfg

    console.print(Panel("[bold]Configuration Check[/bold]", style="cyan"))
    ok = True

    def check(label: str, fn) -> None:
        nonlocal ok
        try:
            val = fn()
            masked = str(val)[:6] + "..." if len(str(val)) > 10 else str(val)
            console.print(f"  [green]✓[/green] {label}: {masked}")
        except EnvironmentError as e:
            console.print(f"  [red]✗[/red] {label}: {e}")
            ok = False

    check("ADS_API_TOKEN", cfg.ads_token)
    check("LLM_PROVIDER", cfg.llm_provider)
    if cfg.llm_provider() == "claude":
        check("ANTHROPIC_API_KEY", cfg.anthropic_key)
        console.print(f"  [dim]  model: {cfg.claude_model()}[/dim]")
    else:
        console.print(f"  [dim]  local model: {cfg.local_llm_model()} @ {cfg.local_llm_base_url()}[/dim]")
    console.print(f"  [dim]  output dir: {cfg.output_dir()}[/dim]")

    if ok:
        console.print("\n[green]All checks passed.[/green]")
    else:
        console.print("\n[red]Some checks failed. Copy .env.example to .env and fill in the values.[/red]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_radius_deg(s: str) -> float:
    """Parse a radius string into decimal degrees.

    Accepts: "5arcmin", "30arcsec", "0.5deg", or a plain number (treated as arcmin).
    """
    s = s.strip().lower()
    try:
        if s.endswith("arcsec"):
            return float(s[:-6]) / 3600
        if s.endswith("arcmin"):
            return float(s[:-6]) / 60
        if s.endswith("deg"):
            return float(s[:-3])
        return float(s) / 60  # plain number → arcmin
    except ValueError:
        raise click.BadParameter(
            f"Cannot parse radius {s!r}. Use e.g. '5arcmin', '30arcsec', '0.5deg', or '5'."
        )


def _check_env() -> None:
    """Quick env sanity check before running any workflow."""
    try:
        from . import config as cfg
        cfg.ads_token()
    except EnvironmentError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)


def _run_workflow(fn, topic: str, extra_context: str = "") -> None:
    """Common wrapper: check env, run workflow, catch errors."""
    _check_env()
    try:
        fn(topic, console, extra_context=extra_context)
    except TypeError:
        # Workflow doesn't accept extra_context yet — call without it
        fn(topic, console)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)
