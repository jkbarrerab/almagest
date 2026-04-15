# ADS Research — Agent Conventions

Shared conventions for all agents and workflows in this project.

## Output directory layout

```
outputs/
  <slug>-<type>.md              # Research artifact
  <slug>-<type>.provenance.md   # Source accounting sidecar
  <slug>-digest-<date>.md       # Watch digests
```

## Slug format

`slugify(topic)` — lowercase, hyphens, max 60 chars.
Example: "dark matter halo formation" → `dark-matter-halo-formation`

## Citation format

All inline citations: **(Author et al. YEAR, `bibcode`)**
Example: (Navarro et al. 1997, `1997ApJ...490..493N`)

Full bibliography at end of every document as a BibTeX block.

## Claim labeling

| Label | Meaning |
|-------|---------|
| (no label) | Directly supported by cited paper |
| [INFERRED] | Logical inference from cited evidence |
| [UNVERIFIED] | Could not confirm against source |
| [SPECULATIVE] | Author's extrapolation, not from literature |

## Provenance sidecars

Every output file gets a `.provenance.md` sidecar recording:
- Generation timestamp (UTC)
- Workflow that produced it
- All ADS bibcodes and URLs used as sources

## ADS query conventions

| Goal | Approach |
|------|---------|
| Best-known papers | `sort: citation_count desc` |
| Latest papers | `sort: date desc`, `year:2023-2025` |
| Review articles | add `doctype:review` |
| Specific journal | `bibstem:ApJ` / `bibstem:MNRAS` / `bibstem:A%26A` |
| Author search | `author:"Last, First"` |
| Abstract keyword | `abs:keyword` |
| Software | `property:software` |
| Open access | `property:openaccess` |

## Agent iteration limits

- Single agents: max 30 tool-use iterations
- Multi-agent parallelism: sequential (no true parallelism yet)
- autoresearch: default 5 rounds, configurable with `--max-rounds`

## File naming for drafts and papers

```
outputs/
  <topic-slug>-brief.md          # /deepresearch output
  <topic-slug>-lit-review.md     # /lit output
  <topic-slug>-peer-review.md    # /review output
  <topic-slug>-audit.md          # /audit output
  <topic-slug>-replication.md    # /replicate output
  <topic-slug>-comparison.md     # /compare output
  <topic-slug>-draft.md          # /draft output
  <topic-slug>-autoresearch.md   # /autoresearch output
```
