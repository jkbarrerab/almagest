# Workflow Examples

All commands assume `almagest` is on your PATH.
If not, prefix each command with `.venv/bin/`.

---

## Extra context — available on all workflows

Every workflow accepts `--context` (inline text) and `--context-file` (path to
a `.txt` or `.md` file) to pass additional instructions, literature, or notes
to the agent. The context is injected into the agent's prompt before it starts.

```bash
# Inline text
almagest <workflow> <args> --context "Focus on low-redshift galaxies only"

# From a file (write your notes in any text or markdown file)
almagest <workflow> <args> --context-file my_notes.md
```

---

## `/deepresearch` — Multi-agent investigation

Spawns a planner, multiple researchers, and a synthesizer to produce a
comprehensive research brief. Best for broad topics where you want
a thorough overview with sourced claims.

```bash
# Broad topic survey
almagest deepresearch "dark matter halo formation at high redshift"

# Focused technical question
almagest deepresearch "mechanisms of AGN feedback quenching star formation"

# Instrumentation / observational
almagest deepresearch "JWST constraints on galaxy formation at z > 10"

# Theory-driven
almagest deepresearch "modified gravity alternatives to dark energy"

# With extra context — steer the investigation
almagest deepresearch "AGN feedback quenching" \
  --context "Focus on low-mass galaxies (M* < 10^10 Msun) and observational evidence only"

almagest deepresearch "AGN feedback quenching" --context-file research_notes.md
```

Output: `outputs/<slug>-deep-research.md` + provenance sidecar

---

## `/lit` — Literature review

Surveys the field systematically: foundational papers, key milestones,
consensus, active debates, and gaps. Ideal as background research before
starting a new project.

```bash
# Classic field survey
almagest lit "stellar feedback in dwarf galaxies"

# Emerging topic
almagest lit "fast radio bursts progenitor models"

# Methodological survey
almagest lit "integral field spectroscopy IFU surveys"

# Narrow sub-topic
almagest lit "oxygen abundance gradients in spiral galaxies"

# With extra context — include specific papers or restrict scope
almagest lit "oxygen abundance gradients" \
  --context "Include IFU surveys only. Make sure to cover:
  - 2014A&A...563A..49S (CALIFA survey)
  - 2018MNRAS.481.2299S (MaNGA gradients)"
```

Output: `outputs/<slug>-lit-review.md`

---

## `/review` — Simulated peer review

Takes an ADS bibcode, a local PDF file, or both, and produces a structured
peer review with severity-graded issues (CRITICAL / MAJOR / MINOR / COSMETIC)
and an actionable revision plan.

```bash
# Review by ADS bibcode
almagest review 2023ApJ...950...72C

# Review a local PDF (preprint, paywalled paper, your own manuscript)
almagest review --pdf ~/Downloads/my_paper.pdf

# Both: use the full PDF text + fetch ADS metadata for related-work search
almagest review 2023ApJ...950...72C --pdf ~/Downloads/same_paper.pdf

# Other bibcode examples
almagest review 1997ApJ...490..493N          # NFW profile paper
almagest review 2023Natur.616..266L          # Recent JWST paper
```

**Adding literature you consider relevant:**

```bash
# Inline — list bibcodes and why they matter
almagest review --pdf ~/Downloads/my_paper.pdf \
  --context "Please also consider the following papers in your review:
  - 2021ApJ...910...72C  (metallicity gradients in spirals, same method)
  - 2019MNRAS.484.5230R  (IFU survey methodology used as reference)
  - 2023A&A...670A..96S  (oxygen abundance calibrations, directly relevant)
  Pay special attention to whether the authors discuss systematic uncertainties
  in the abundance calibration."

# From a file — write your notes once, reuse them
almagest review --pdf ~/Downloads/my_paper.pdf --context-file review_notes.md
```

**Example `review_notes.md`:**
```markdown
## Key papers to consider

- 2021ApJ...910...72C — metallicity gradients in spirals (same method as this paper)
- 2019MNRAS.484.5230R — IFU methodology reference
- 2023A&A...670A..96S — oxygen abundance calibrations

## Specific concerns to address

- Check whether systematic errors in the abundance calibration are propagated
- Compare the sample selection to Sánchez et al. 2014
- Verify that the radial binning scheme is consistent with prior work
```

> **Tip**: Find bibcodes with the `search` command:
> ```bash
> almagest search "author:Pillepich IllustrisTNG year:2018" --limit 5
> ```

Output: `outputs/<slug>-peer-review.md`

---

## `/source` — Source literature search

Searches NASA ADS for all papers about a specific astronomical object (resolved
via SIMBAD/NED) or a sky position + radius. Optionally filter by science topic.
Produces an object overview, key papers table, discovery timeline, instrument
coverage, consensus findings, open questions, and BibTeX.

```bash
# All literature for a named object
almagest source "NGC 1068"

# Filter by science topic
almagest source "NGC 1068" --topic "integral field spectroscopy"
almagest source "M87" --topic "jet kinematics"
almagest source "Crab Nebula" --topic "pulsar wind nebula"
almagest source "3C 273" --topic "variability"

# Positional cone search (radius formats: arcmin, arcsec, deg, or plain number = arcmin)
almagest source --ra 40.669 --dec -0.014 --radius 5arcmin
almagest source --ra 40.669 --dec -0.014 --radius 0.5deg --topic "AGN"
almagest source --ra 187.706 --dec 12.391 --radius 2arcmin --topic "radio jet"

# Sort by most recent instead of most cited
almagest source "NGC 4321" --topic "HII regions" --sort "date desc"

# Extra context — restrict epoch or instruments
almagest source "NGC 1068" --topic "integral field spectroscopy" \
  --context "Focus on MUSE and SINFONI observations published after 2015.
  Pay particular attention to papers studying the AGN-driven outflow geometry."
```

Output: `outputs/<slug>-source-lit.md`

---

## `/audit` — Reproducibility audit

Checks whether any linked code repository (GitHub, Zenodo, ASCL)
matches the methods, parameters, and claims in the paper.

```bash
# Paper with GitHub repo
almagest audit 2022ApJ...935..167V

# Software paper
almagest audit 2019JOSS....4.1414F

# Simulation pipeline paper
almagest audit 2018MNRAS.473.4077P

# Focus the audit on specific claims
almagest audit 2022ApJ...935..167V \
  --context "Focus on whether the stellar mass function parameters in Table 2
  match the values hardcoded in the fitting routine."
```

Output: `outputs/<slug>-audit.md`

---

## `/replicate` — Replication plan

Generates a step-by-step plan to reproduce the key results of a paper,
including data access, software setup, and expected outputs.
Add `--execute` to actually run the first steps.

```bash
# Plan only (safe, no code runs)
almagest replicate 2020MNRAS.499..230B

# Plan + execute (clones repos, runs scripts)
almagest replicate 2020MNRAS.499..230B --execute

# Provide environment constraints
almagest replicate 2020MNRAS.499..230B \
  --context "I only have access to public SDSS data. Skip any steps requiring
  proprietary datasets. Target Python 3.11 environment."
```

Output: `outputs/<slug>-replication.md`

---

## `/compare` — Side-by-side comparison

Compares competing theories, methods, or results on a topic and produces
an agreement / conflict matrix.

```bash
# Competing cosmological models
almagest compare "NFW vs Einasto dark matter density profiles"

# Competing explanations
almagest compare "ram pressure stripping vs AGN feedback as quenching mechanism"

# Two specific papers
almagest compare "bibcode:2019ApJ...887...27G vs bibcode:2021ApJ...909...78D stellar mass function"

# Method comparison
almagest compare "photometric vs spectroscopic redshift accuracy for survey science"

# Guide the comparison dimensions
almagest compare "NFW vs Einasto dark matter profiles" \
  --context "Focus the comparison on: (1) fit quality in dwarf galaxies,
  (2) behaviour at small radii, (3) N-body simulation results post-2015."
```

Output: `outputs/<slug>-comparison.md`

---

## `/draft` — Paper-style draft

Researches a topic and produces a full paper draft (introduction, methods,
results, discussion, conclusions) with inline citations and a BibTeX bibliography.
Not submission-ready but a solid starting point.

```bash
# Standard research paper
almagest draft "the role of environment in galaxy quenching at z ~ 0.5"

# Review-style
almagest draft "a review of chemical abundance gradients in nearby galaxies"

# Observational proposal-style
almagest draft "prospects for detecting CO emission in high-z quiescent galaxies with ALMA"

# Seed the draft with your own ideas or data
almagest draft "chemical abundance gradients in nearby galaxies" \
  --context "The draft should assume we have MaNGA IFU data for 500 galaxies.
  Emphasise the comparison with CALIFA results. Target audience: ApJ."
```

Output: `outputs/<slug>-draft.md`

---

## `/autoresearch` — Autonomous research loop

Starts from a seed idea and iterates: form hypothesis → search ADS →
evaluate evidence → refine hypothesis → repeat. Stops when the evidence
converges or `--max-rounds` is reached.

```bash
# Default 5 rounds
almagest autoresearch "galaxy size evolution driven by minor mergers"

# More thorough (10 rounds)
almagest autoresearch "the origin of the stellar mass-metallicity relation" --max-rounds 10

# Quick exploration (3 rounds)
almagest autoresearch "tidally stripped stars as probes of dark matter" --max-rounds 3

# Constrain the hypothesis space
almagest autoresearch "galaxy quenching at cosmic noon" \
  --context "Restrict to observational evidence at 1.5 < z < 2.5.
  Prioritise JWST and ALMA results published after 2022."
```

Output: `outputs/<slug>-autoresearch.md`

---

## `/watch` — Recurring paper monitor

Registers a saved search and reports new papers whenever you run `watch run`.
Great for staying current on a topic without manual ADS searches.

```bash
# Add a watch (uses the topic text as the ADS query)
almagest watch add "galaxy quenching"

# Add a watch with a custom ADS query
almagest watch add "IFU metallicity gradients" \
  --query "abs:metallicity abs:gradient (bibstem:ApJ OR bibstem:MNRAS) year:2024-2025"

# Add a watch for a specific author's new papers
almagest watch add "Pillepich new papers" \
  --query "author:Pillepich,A year:2024-2025"

# List all registered watches
almagest watch list

# Check for new papers (plain list)
almagest watch run

# Check + generate an AI digest of new papers
almagest watch run --digest

# Remove a watch
almagest watch remove galaxy-quenching
```

Output: `outputs/<slug>-digest-<date>.md` (with `--digest`)

---

## `/coauthor` — Friendly co-author review

Takes an ADS bibcode, a local PDF file, or both, and writes a warm, personal
email to the authors with honest feedback — as a trusted collaborator rather
than a formal referee.

```bash
# Review by ADS bibcode
almagest coauthor 2023ApJ...950...72C

# Review a local PDF (your own draft, preprint, paywalled paper)
almagest coauthor --pdf ~/Downloads/my_draft.pdf

# Both: full PDF text + ADS metadata for related-work search
almagest coauthor 2023ApJ...950...72C --pdf ~/Downloads/same_paper.pdf

# Other bibcode examples
almagest coauthor 1997ApJ...490..493N          # NFW profile paper
almagest coauthor 2023Natur.616..266L          # Recent JWST paper
```

**Adding context — papers you consider important or specific concerns:**

```bash
almagest coauthor --pdf ~/Downloads/my_draft.pdf \
  --context "The authors are graduate students submitting their first paper.
  Be particularly encouraging. Also check whether they discuss:
  - 2021ApJ...910...72C  (same method, should be cited)
  - 2019MNRAS.484.5230R  (IFU methodology reference)"
```

Output: `outputs/<slug>-coauthor-review.md`

---

## Quick utilities

```bash
# Search ADS directly
almagest search "dark matter substructure year:2023-2025" --limit 15
almagest search "author:Schaye,J bibstem:MNRAS" --sort "date desc"

# Show full paper details by bibcode
almagest show 1997ApJ...490..493N

# Verify config
almagest config-check
```

---

## ADS query syntax reference

These work in `--query` options and the `search` command:

| Goal | Query example |
|------|--------------|
| Keyword in abstract | `abs:"stellar feedback"` |
| Author | `author:"Navarro, J"` |
| Year range | `year:2020-2025` |
| Specific journal | `bibstem:ApJ` / `bibstem:MNRAS` / `bibstem:A%26A` |
| Review articles | `doctype:review` |
| Open access only | `property:openaccess` |
| Software papers | `property:software` |
| arXiv class | `arxiv_class:astro-ph.GA` |
| Citing a paper | `citations(bibcode:1997ApJ...490..493N)` |
| Referenced by | `references(bibcode:2005ApJ...624L..85M)` |
| Combined | `abs:"quenching" author:"Peng" year:2010-2020 property:refereed` |
