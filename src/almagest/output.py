"""Output management — writes research artifacts with provenance sidecars."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from . import config


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60]


def write_output(
    slug: str,
    artifact_type: str,
    content: str,
    sources: list[str] | None = None,
    workflow: str = "",
) -> Path:
    """Write a research artifact and its provenance sidecar.

    Args:
        slug: Short identifier for the topic.
        artifact_type: e.g. 'brief', 'lit-review', 'peer-review', 'draft', etc.
        content: Markdown content to write.
        sources: List of ADS bibcodes or URLs used.
        workflow: Which workflow produced this (e.g. '/deepresearch').
    """
    outdir = config.output_dir()
    filename = f"{slug}-{artifact_type}.md"
    path = outdir / filename

    path.write_text(content, encoding="utf-8")

    # Write provenance sidecar
    prov_path = outdir / f"{slug}-{artifact_type}.provenance.md"
    _write_provenance(prov_path, filename, workflow, sources or [])

    return path


def _write_provenance(
    path: Path,
    artifact: str,
    workflow: str,
    sources: list[str],
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"# Provenance: {artifact}",
        "",
        f"- **Generated**: {ts}",
        f"- **Workflow**: {workflow or 'unknown'}",
        f"- **Sources**: {len(sources)}",
        "",
        "## Sources",
        "",
    ]
    for s in sources:
        if s.startswith("http"):
            lines.append(f"- [{s}]({s})")
        else:
            lines.append(f"- ADS: [{s}](https://ui.adsabs.harvard.edu/abs/{s})")
    if not sources:
        lines.append("- (none recorded)")
    lines += [
        "",
        "## Verification status",
        "",
        "- [ ] Citations spot-checked",
        "- [ ] Claims verified against source abstracts",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
