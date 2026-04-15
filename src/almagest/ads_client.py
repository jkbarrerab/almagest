"""NASA ADS REST API client.

Docs: https://github.com/adsabs/adsabs-dev-api
"""

from __future__ import annotations

from typing import Any

import httpx

from . import config

ADS_BASE = "https://api.adsabs.harvard.edu/v1"

# Fields returned by default on paper records
DEFAULT_FIELDS = [
    "bibcode",
    "title",
    "author",
    "year",
    "abstract",
    "citation_count",
    "read_count",
    "identifier",
    "doi",
    "pub",
    "keyword",
    "arxiv_class",
    "property",
    "data",
]


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=ADS_BASE,
        headers={"Authorization": f"Bearer {config.ads_token()}"},
        timeout=30.0,
    )


def search(
    query: str,
    limit: int = 10,
    sort: str = "citation_count desc",
    fields: list[str] | None = None,
    fl_extra: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search ADS and return a list of paper records.

    Args:
        query: ADS query string (supports full ADS syntax).
        limit: Max number of results.
        sort: Sort order, e.g. "citation_count desc", "date desc".
        fields: Override default field list.
        fl_extra: Additional fields to append to the default list.
    """
    fl = fields or DEFAULT_FIELDS
    if fl_extra:
        fl = fl + [f for f in fl_extra if f not in fl]

    with _client() as c:
        r = c.get(
            "/search/query",
            params={
                "q": query,
                "rows": min(limit, config.ads_max_results()),
                "sort": sort,
                "fl": ",".join(fl),
            },
        )
        r.raise_for_status()
        return r.json().get("response", {}).get("docs", [])


def get_paper(bibcode: str, fields: list[str] | None = None) -> dict[str, Any]:
    """Fetch a single paper by bibcode."""
    fl = fields or DEFAULT_FIELDS
    with _client() as c:
        r = c.get(
            "/search/query",
            params={
                "q": f"bibcode:{bibcode}",
                "fl": ",".join(fl),
                "rows": 1,
            },
        )
        r.raise_for_status()
        docs = r.json().get("response", {}).get("docs", [])
        if not docs:
            raise ValueError(f"No paper found for bibcode: {bibcode}")
        return docs[0]


def get_abstract(bibcode: str) -> str:
    """Return just the abstract text for a paper."""
    paper = get_paper(bibcode, fields=["bibcode", "title", "abstract", "author", "year"])
    title = paper.get("title", ["(no title)"])[0]
    authors = paper.get("author", [])
    author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
    year = paper.get("year", "")
    abstract = paper.get("abstract", "(no abstract available)")
    return f"**{title}**\n{author_str} ({year})\n\n{abstract}"


def get_citations(bibcode: str, limit: int = 20) -> list[dict[str, Any]]:
    """Return papers that cite the given bibcode."""
    with _client() as c:
        r = c.get(
            "/search/query",
            params={
                "q": f"citations(bibcode:{bibcode})",
                "fl": ",".join(DEFAULT_FIELDS),
                "rows": limit,
                "sort": "citation_count desc",
            },
        )
        r.raise_for_status()
        return r.json().get("response", {}).get("docs", [])


def get_references(bibcode: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return papers referenced by the given bibcode."""
    with _client() as c:
        r = c.get(
            "/search/query",
            params={
                "q": f"references(bibcode:{bibcode})",
                "fl": ",".join(DEFAULT_FIELDS),
                "rows": limit,
                "sort": "citation_count desc",
            },
        )
        r.raise_for_status()
        return r.json().get("response", {}).get("docs", [])


def get_metrics(bibcodes: list[str]) -> dict[str, Any]:
    """Fetch citation metrics for a list of bibcodes."""
    with _client() as c:
        r = c.post(
            "/metrics",
            json={"bibcodes": bibcodes, "types": ["basic", "citations", "indicators"]},
        )
        r.raise_for_status()
        return r.json()


def get_full_text(bibcode: str) -> str | None:
    """Attempt to retrieve full text for a paper (when available).

    Returns the text content or None if unavailable.
    """
    with _client() as c:
        r = c.get(f"/search/query", params={"q": f"bibcode:{bibcode}", "fl": "body", "rows": 1})
        r.raise_for_status()
        docs = r.json().get("response", {}).get("docs", [])
        if docs and docs[0].get("body"):
            return docs[0]["body"]
    return None


def search_object(
    name: str,
    topic: str = "",
    limit: int = 20,
    sort: str = "citation_count desc",
) -> list[dict[str, Any]]:
    """Search ADS for papers about a named astronomical object.

    Uses ADS object: field which resolves names via SIMBAD/NED.
    When a topic is given, fetches a larger result set and filters
    client-side (ADS does not support combining object: with other fields).
    Falls back to abs: text search if the object: query is rejected (e.g. name
    not found in SIMBAD/NED, or non-canonical formatting like "NGC1068").
    """
    q = f'object:"{name}"'
    # Fetch more papers upfront so post-filter still returns enough results
    fetch_limit = limit if not topic else min(200, limit * 10)
    try:
        papers = search(q, limit=fetch_limit, sort=sort)
    except httpx.HTTPStatusError:
        # ADS rejects object: queries when the name can't be resolved.
        # Fall back to abstract/title text search, combining topic inline so
        # ADS filters server-side (no client-side post-filter needed).
        fallback_q = f'abs:"{name}"' + (f' abs:"{topic}"' if topic else "")
        return search(fallback_q, limit=limit, sort=sort)

    if topic and papers:
        topic_words = topic.lower().split()

        def _matches(paper: dict) -> bool:
            text = (
                " ".join(paper.get("title") or []) + " " +
                (paper.get("abstract") or "")
            ).lower()
            return all(w in text for w in topic_words)

        papers = [p for p in papers if _matches(p)][:limit]

    return papers


def search_position(
    ra: float,
    dec: float,
    radius_deg: float,
    topic: str = "",
    limit: int = 20,
    sort: str = "citation_count desc",
) -> list[dict[str, Any]]:
    """Cone search around a sky position.

    Args:
        ra: Right Ascension in decimal degrees (0–360).
        dec: Declination in decimal degrees (−90 to +90).
        radius_deg: Search radius in degrees (ADS max = 1.0 = 60 arcmin).
        topic: Optional free-text topic filter.
        limit: Max results.
        sort: Sort order.
    """
    radius_deg = min(abs(radius_deg), 1.0)
    sign = "+" if dec >= 0 else ""
    q = f'object:"{ra:.6f} {sign}{dec:.6f}:{radius_deg:.6f}"'
    fetch_limit = limit if not topic else min(200, limit * 10)
    try:
        papers = search(q, limit=fetch_limit, sort=sort)
    except httpx.HTTPStatusError:
        # ADS position cone-search can fail with 400 when no SIMBAD/NED objects are
        # registered at those coordinates. Fall back to a topic-only search; if no
        # topic was given there is nothing meaningful to search on, so return empty.
        if not topic:
            return []
        return search(f'abs:"{topic}"', limit=limit, sort=sort)

    if topic and papers:
        topic_words = topic.lower().split()

        def _matches(paper: dict) -> bool:
            text = (
                " ".join(paper.get("title") or []) + " " +
                (paper.get("abstract") or "")
            ).lower()
            return all(w in text for w in topic_words)

        papers = [p for p in papers if _matches(p)][:limit]

    return papers


def export_bibtex(bibcodes: list[str]) -> str:
    """Export a list of bibcodes as BibTeX."""
    with _client() as c:
        r = c.post(
            "/export/bibtex",
            json={"bibcode": bibcodes},
        )
        r.raise_for_status()
        return r.json().get("export", "")


def format_paper_summary(paper: dict[str, Any]) -> str:
    """Return a concise one-line summary of a paper record."""
    bibcode = paper.get("bibcode", "?")
    title = (paper.get("title") or ["(no title)"])[0]
    authors = paper.get("author", [])
    author_str = authors[0].split(",")[0] if authors else "?"
    if len(authors) > 1:
        author_str += " et al."
    year = paper.get("year", "?")
    cites = paper.get("citation_count", 0)
    return f"[{bibcode}] {author_str} ({year}) — {title[:80]} ({cites} cites)"


def format_paper_detail(paper: dict[str, Any]) -> str:
    """Return a multi-line detailed summary of a paper record."""
    bibcode = paper.get("bibcode", "?")
    title = (paper.get("title") or ["(no title)"])[0]
    authors = paper.get("author", [])
    year = paper.get("year", "?")
    pub = paper.get("pub", "?")
    cites = paper.get("citation_count", 0)
    abstract = paper.get("abstract", "(no abstract)")
    doi = paper.get("doi", [None])[0] if paper.get("doi") else None
    identifiers = paper.get("identifier", [])
    arxiv_id = next((i for i in identifiers if i.startswith("arXiv:")), None)

    lines = [
        f"**{title}**",
        f"Authors: {', '.join(authors[:5])}" + (" et al." if len(authors) > 5 else ""),
        f"Year: {year}  |  Journal: {pub}  |  Citations: {cites}",
        f"Bibcode: {bibcode}",
    ]
    if doi:
        lines.append(f"DOI: https://doi.org/{doi}")
    if arxiv_id:
        lines.append(f"arXiv: https://arxiv.org/abs/{arxiv_id.replace('arXiv:', '')}")
    lines += ["", abstract]
    return "\n".join(lines)
