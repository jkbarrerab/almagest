"""Tool definitions and execution layer.

Every tool is:
  - A JSON schema definition (for the LLM)
  - An implementation function
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

import httpx

from . import ads_client, config

# ---------------------------------------------------------------------------
# Tool schema definitions (passed to the LLM)
# ---------------------------------------------------------------------------

ADS_TOOLS: list[dict[str, Any]] = [
    {
        "name": "ads_search",
        "description": (
            "Search NASA ADS for astronomy/astrophysics papers. "
            "Supports full ADS query syntax (author:, year:, title:, abstract:, "
            "property:refereed, bibstem:, etc.). Returns structured paper records."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "ADS search query, e.g. 'dark matter halos year:2020-2024'",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of results (default 10, max 20)",
                    "default": 10,
                },
                "sort": {
                    "type": "string",
                    "description": "Sort order, e.g. 'citation_count desc', 'date desc'",
                    "default": "citation_count desc",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "ads_get_paper",
        "description": "Get full metadata and abstract for a paper by its ADS bibcode.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bibcode": {
                    "type": "string",
                    "description": "ADS bibcode, e.g. '2020ApJ...900L...1L'",
                }
            },
            "required": ["bibcode"],
        },
    },
    {
        "name": "ads_get_citations",
        "description": "Get papers that cite a given paper (sorted by citation count).",
        "input_schema": {
            "type": "object",
            "properties": {
                "bibcode": {"type": "string", "description": "ADS bibcode to find citers for"},
                "limit": {"type": "integer", "description": "Max results", "default": 15},
            },
            "required": ["bibcode"],
        },
    },
    {
        "name": "ads_get_references",
        "description": "Get papers referenced by a given paper.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bibcode": {"type": "string", "description": "ADS bibcode"},
                "limit": {"type": "integer", "description": "Max results", "default": 30},
            },
            "required": ["bibcode"],
        },
    },
    {
        "name": "ads_get_metrics",
        "description": "Get citation metrics (h-index, total citations, reads) for a list of bibcodes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bibcodes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ADS bibcodes",
                }
            },
            "required": ["bibcodes"],
        },
    },
    {
        "name": "ads_export_bibtex",
        "description": "Export a list of bibcodes as a BibTeX string.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bibcodes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ADS bibcodes to export",
                }
            },
            "required": ["bibcodes"],
        },
    },
    {
        "name": "ads_get_full_text",
        "description": "Attempt to retrieve the full text body of a paper (available for some open-access papers).",
        "input_schema": {
            "type": "object",
            "properties": {
                "bibcode": {"type": "string", "description": "ADS bibcode"}
            },
            "required": ["bibcode"],
        },
    },
    {
        "name": "ads_search_object",
        "description": (
            "Search NASA ADS for papers about a specific named astronomical object "
            "(e.g. 'NGC 1068', 'M87', 'Crab Nebula', '3C 273'). "
            "ADS resolves object names via SIMBAD and NED. "
            "Use the optional topic parameter to filter by science topic "
            "(e.g. 'integral field spectroscopy', 'AGN', 'star formation')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "description": "Astronomical object name, e.g. 'NGC 1068'",
                },
                "topic": {
                    "type": "string",
                    "description": "Optional science topic filter, e.g. 'integral field spectroscopy'",
                    "default": "",
                },
                "limit": {"type": "integer", "description": "Max results", "default": 20},
                "sort": {
                    "type": "string",
                    "description": "Sort order: 'citation_count desc' or 'date desc'",
                    "default": "citation_count desc",
                },
            },
            "required": ["object_name"],
        },
    },
    {
        "name": "ads_search_position",
        "description": (
            "Cone search on NASA ADS around a sky position (RA/Dec). "
            "Returns papers about objects within the search radius. "
            "Radius is in degrees; maximum is 1.0 deg (= 60 arcmin)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ra": {
                    "type": "number",
                    "description": "Right Ascension in decimal degrees (0–360)",
                },
                "dec": {
                    "type": "number",
                    "description": "Declination in decimal degrees (−90 to +90)",
                },
                "radius_deg": {
                    "type": "number",
                    "description": "Search radius in degrees (max 1.0 = 60 arcmin)",
                    "default": 0.0333,
                },
                "topic": {
                    "type": "string",
                    "description": "Optional science topic filter",
                    "default": "",
                },
                "limit": {"type": "integer", "description": "Max results", "default": 20},
                "sort": {
                    "type": "string",
                    "default": "citation_count desc",
                },
            },
            "required": ["ra", "dec"],
        },
    },
]

WEB_TOOLS: list[dict[str, Any]] = [
    {
        "name": "fetch_url",
        "description": "Fetch the text content of a URL (HTML stripped to readable text).",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL to fetch"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the web for information (requires TAVILY_API_KEY).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
]

FILE_TOOLS: list[dict[str, Any]] = [
    {
        "name": "write_file",
        "description": "Write content to a file in the outputs directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Filename relative to the outputs dir, e.g. 'dark-matter-brief.md'",
                },
                "content": {"type": "string", "description": "File content"},
            },
            "required": ["filename", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file from the outputs directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename relative to outputs dir"}
            },
            "required": ["filename"],
        },
    },
    {
        "name": "bash",
        "description": (
            "Run a shell command and return stdout+stderr. "
            "Use for git cloning repos, running Python scripts, docker commands, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 60)",
                    "default": 60,
                },
            },
            "required": ["command"],
        },
    },
]

ALL_TOOLS = ADS_TOOLS + WEB_TOOLS + FILE_TOOLS


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Dispatch a tool call and return the result as a string."""
    try:
        if name == "ads_search":
            return _ads_search(**arguments)
        elif name == "ads_get_paper":
            return _ads_get_paper(**arguments)
        elif name == "ads_get_citations":
            return _ads_get_citations(**arguments)
        elif name == "ads_get_references":
            return _ads_get_references(**arguments)
        elif name == "ads_get_metrics":
            return _ads_get_metrics(**arguments)
        elif name == "ads_export_bibtex":
            return ads_client.export_bibtex(**arguments)
        elif name == "ads_get_full_text":
            return _ads_get_full_text(**arguments)
        elif name == "ads_search_object":
            return _ads_search_object(**arguments)
        elif name == "ads_search_position":
            return _ads_search_position(**arguments)
        elif name == "fetch_url":
            return _fetch_url(**arguments)
        elif name == "web_search":
            return _web_search(**arguments)
        elif name == "write_file":
            return _write_file(**arguments)
        elif name == "read_file":
            return _read_file(**arguments)
        elif name == "bash":
            return _bash(**arguments)
        else:
            return f"[Error] Unknown tool: {name}"
    except Exception as e:
        return f"[Error in {name}]: {e}"


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------


def _ads_search(query: str, limit: int = 10, sort: str = "citation_count desc") -> str:
    papers = ads_client.search(query, limit=limit, sort=sort)
    if not papers:
        return f"No results found for query: {query}"
    lines = [f"Found {len(papers)} results for: {query}\n"]
    for p in papers:
        lines.append(ads_client.format_paper_summary(p))
    return "\n".join(lines)


def _ads_get_paper(bibcode: str) -> str:
    paper = ads_client.get_paper(bibcode)
    return ads_client.format_paper_detail(paper)


def _ads_get_citations(bibcode: str, limit: int = 15) -> str:
    papers = ads_client.get_citations(bibcode, limit=limit)
    if not papers:
        return f"No citations found for {bibcode}"
    lines = [f"Papers citing {bibcode} ({len(papers)} shown):\n"]
    for p in papers:
        lines.append(ads_client.format_paper_summary(p))
    return "\n".join(lines)


def _ads_get_references(bibcode: str, limit: int = 30) -> str:
    papers = ads_client.get_references(bibcode, limit=limit)
    if not papers:
        return f"No references found for {bibcode}"
    lines = [f"References in {bibcode} ({len(papers)} shown):\n"]
    for p in papers:
        lines.append(ads_client.format_paper_summary(p))
    return "\n".join(lines)


def _ads_get_metrics(bibcodes: list[str]) -> str:
    try:
        metrics = ads_client.get_metrics(bibcodes)
        return json.dumps(metrics, indent=2)
    except Exception as e:
        return f"Metrics unavailable: {e}"


def _ads_get_full_text(bibcode: str) -> str:
    text = ads_client.get_full_text(bibcode)
    if text:
        return text[:15000]  # cap to avoid context overflow
    return f"Full text not available for {bibcode} (open-access only)"


def _ads_search_object(
    object_name: str,
    topic: str = "",
    limit: int = 20,
    sort: str = "citation_count desc",
) -> str:
    papers = ads_client.search_object(object_name, topic=topic, limit=limit, sort=sort)
    if not papers:
        label = f"{object_name}" + (f" [{topic}]" if topic else "")
        return f"No ADS papers found for object: {label}"
    label = f"{object_name}" + (f" filtered by '{topic}'" if topic else "")
    lines = [f"Found {len(papers)} papers for object: {label}\n"]
    for p in papers:
        lines.append(ads_client.format_paper_summary(p))
    return "\n".join(lines)


def _ads_search_position(
    ra: float,
    dec: float,
    radius_deg: float = 0.0333,
    topic: str = "",
    limit: int = 20,
    sort: str = "citation_count desc",
) -> str:
    papers = ads_client.search_position(ra, dec, radius_deg, topic=topic, limit=limit, sort=sort)
    radius_arcmin = radius_deg * 60
    if not papers:
        return f"No ADS papers found within {radius_arcmin:.1f} arcmin of RA={ra:.4f} Dec={dec:+.4f}"
    label = f"RA={ra:.4f} Dec={dec:+.4f} r={radius_arcmin:.1f}′" + (f" [{topic}]" if topic else "")
    lines = [f"Found {len(papers)} papers within cone: {label}\n"]
    for p in papers:
        lines.append(ads_client.format_paper_summary(p))
    return "\n".join(lines)


def _fetch_url(url: str) -> str:
    try:
        r = httpx.get(url, follow_redirects=True, timeout=15)
        r.raise_for_status()
        # Very basic HTML stripping
        text = r.text
        import re
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s{3,}", "\n\n", text)
        return text.strip()[:10000]
    except Exception as e:
        return f"[Error fetching {url}]: {e}"


def _web_search(query: str, max_results: int = 5) -> str:
    provider = config.web_search_provider()
    if provider == "tavily":
        key = config.tavily_key()
        if not key:
            return "[Error] TAVILY_API_KEY not set"
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=key)
            result = client.search(query, max_results=max_results)
            lines = []
            for r in result.get("results", []):
                lines.append(f"**{r['title']}**\n{r['url']}\n{r.get('content', '')[:300]}\n")
            return "\n".join(lines) or "No results"
        except ImportError:
            return "[Error] tavily-python not installed. Run: pip install tavily-python"
        except Exception as e:
            return f"[Error in web_search]: {e}"
    return "[Web search not configured. Set WEB_SEARCH_PROVIDER=tavily and TAVILY_API_KEY]"


def _write_file(filename: str, content: str) -> str:
    path = config.output_dir() / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {path}"


def _read_file(filename: str) -> str:
    path = config.output_dir() / filename
    if not path.exists():
        return f"[Error] File not found: {path}"
    return path.read_text(encoding="utf-8")


def extract_pdf_text(path: str) -> str:
    """Extract and return all text from a local PDF file.

    Raises FileNotFoundError if the path does not exist.
    Raises ImportError if pypdf is not installed.
    """
    from pathlib import Path
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"PDF not found: {p}")
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf is required: pip install pypdf")
    reader = PdfReader(str(p))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages)
    # Cap to ~40k chars to avoid overwhelming the context window
    if len(text) > 40000:
        text = text[:40000] + "\n\n[... truncated at 40,000 chars ...]"
    return text


def _bash(command: str, timeout: int = 60) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += "\n[stderr]\n" + result.stderr
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"[Error] Command timed out after {timeout}s"
    except Exception as e:
        return f"[Error] {e}"
