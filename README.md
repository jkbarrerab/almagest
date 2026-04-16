# Almagest — AI Research Agent for NASA ADS

```
   ╔═╗╦  ╔╦╗╔═╗╔═╗╔═╗╔═╗╔╦╗
   ╠═╣║  ║║║╠═╣║ ╦║╣ ╚═╗ ║
   ╩ ╩╩═╝╩ ╩╩ ╩╚═╝╚═╝╚═╝ ╩
```

**Almagest** is an open-source CLI research agent for the [NASA Astrophysics Data System (ADS)](https://ui.adsabs.harvard.edu). It runs ten research workflows — literature reviews, peer reviews, reproducibility audits, paper drafts, and more — powered by Claude or any OpenAI-compatible local LLM.

> Named after the *Almagest* — Ptolemy's 2nd-century compendium of all known astronomical knowledge.

**[Live demo →](https://jkbarrerab.github.io/almagest/)**

---

## Workflows

| Command | Description |
|---------|-------------|
| `almagest deepresearch` | Multi-agent investigation across papers, web, and code |
| `almagest lit` | Literature review with consensus mapping and gap analysis |
| `almagest source` | All literature for a named object or sky position |
| `almagest review` | Simulated peer review with severity-graded issues |
| `almagest audit` | Paper-to-code reproducibility audit |
| `almagest replicate` | Step-by-step replication plan (optional execution) |
| `almagest compare` | Side-by-side source comparison with agreement/conflict matrix |
| `almagest draft` | Paper-style draft with inline citations and BibTeX |
| `almagest autoresearch` | Autonomous hypothesis → search → refine loop |
| `almagest watch` | Recurring monitor for new papers on a topic |

Every workflow writes a structured Markdown report to `outputs/` plus a `.provenance.md` sidecar that records all ADS bibcodes and sources consulted.

---

## Installation

Requires **Python 3.11+**.

```bash
git clone https://github.com/jkbarrerab/almagest.git
cd almagest
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .
```

---

## Configuration

Copy the example env file and fill in your API keys:

```bash
cp .env.example .env
```

```env
# Required
ADS_API_TOKEN=your_ads_token_here
ANTHROPIC_API_KEY=sk-ant-...

# Optional
LLM_PROVIDER=claude          # or "local" for Ollama / LM Studio / vLLM
CLAUDE_MODEL=claude-sonnet-4-6
OUTPUT_DIR=./outputs
ADS_MAX_RESULTS=20
WEB_SEARCH_PROVIDER=none     # set to "tavily" to enable web search
TAVILY_API_KEY=tvly-...
```

**Get your keys:**
- NASA ADS token: [ui.adsabs.harvard.edu/user/settings/token](https://ui.adsabs.harvard.edu/user/settings/token) (free account)
- Anthropic API key: [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)

Verify your setup:

```bash
almagest config-check
```

---

## Quick start

```bash
# Literature review
almagest lit "AGN feedback quenching"

# All papers about an astronomical object
almagest source "NGC 1068" --topic "integral field spectroscopy"

# Positional cone search
almagest source --ra 40.669 --dec -0.014 --radius 5arcmin --topic "AGN"

# Simulated peer review of a local PDF
almagest review --pdf ~/Downloads/my_paper.pdf

# Autonomous research loop (5 rounds by default)
almagest autoresearch "galaxy quenching driven by AGN feedback"

# Monitor a topic for new papers
almagest watch add "stellar feedback dwarf galaxies"
almagest watch run --digest
```

Every command accepts `--context` (inline text) or `--context-file` (path to a `.md` or `.txt` file) to pass extra instructions to the agent:

```bash
almagest lit "oxygen abundance gradients" \
  --context "Include IFU surveys only. Focus on CALIFA and MaNGA results post-2015."

almagest review --pdf paper.pdf --context-file my_review_notes.md
```

---

## Using a local LLM (no API key required)

Switch to any OpenAI-compatible local server by changing two lines in `.env`:

```env
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama3.2
```

**Ollama quick start:**

```bash
ollama pull llama3.2
ollama serve
almagest lit "dark matter halos"
```

Models with native tool-use support (Qwen 2.5, Llama 3.1+) give the best results. All others fall back to text-based tool calling.

---

## Output format

All reports follow the same conventions:

- **Inline citations**: `(Author et al. YEAR, `bibcode`)`
- **Full BibTeX block** at the end of every document
- **Claim labels**: `[INFERRED]`, `[UNVERIFIED]`, `[SPECULATIVE]` where applicable
- **Provenance sidecar**: `outputs/<slug>-<type>.provenance.md` records timestamp, workflow, and all sources

---

## ADS query syntax

Use full ADS Solr syntax in `almagest search` and `watch add --query`:

```bash
almagest search "abs:\"stellar feedback\" author:Hopkins year:2018-2024 property:refereed" --limit 15
almagest search "doctype:review bibstem:ARA&A abs:dark matter" --sort "citation_count desc"
```

| Goal | Syntax |
|------|--------|
| Abstract keyword | `abs:"stellar feedback"` |
| Author | `author:"Navarro, J"` |
| Year range | `year:2020-2025` |
| Journal | `bibstem:ApJ` / `bibstem:MNRAS` / `bibstem:A%26A` |
| Review articles | `doctype:review` |
| Open access | `property:openaccess` |
| arXiv class | `arxiv_class:astro-ph.GA` |
| Papers citing X | `citations(bibcode:1997ApJ...490..493N)` |

---

## Architecture

```
src/almagest/
  cli.py          # Click entry point — all commands
  agent.py        # Agentic tool-use loop (max 30 iterations)
  tools.py        # ADS, web, and file tool schemas + dispatch
  ads_client.py   # NASA ADS REST API wrapper
  llm/            # ClaudeLLM and LocalLLM (OpenAI-compatible)
  workflows/      # One module per workflow
agents/           # System prompt Markdown files per agent role
```

Each workflow instantiates an `Agent` that loops: call LLM → dispatch tool calls → feed results back → repeat until the LLM returns a text-only response. Multi-agent workflows (e.g. `deepresearch`) run sub-agents sequentially via `MultiAgent`.

---

## Development

```bash
pip install -e ".[dev]"
ruff check src/        # lint
almagest config-check  # verify credentials
```

To add a new workflow see the contributing notes in `CLAUDE.md` (not included in this repo — read the source).

---

## License

MIT
