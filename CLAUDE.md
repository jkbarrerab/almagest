# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Almagest is an open-source CLI research agent for NASA ADS, powered by Claude or any
OpenAI-compatible local LLM. Users run slash-command workflows (e.g. `almagest source "NGC 1068"`)
that launch agentic loops with tool use, then write structured Markdown reports to `outputs/`.

## Commands

```bash
# Setup
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in ADS_API_TOKEN and ANTHROPIC_API_KEY

# Lint
ruff check src/

# Verify config
almagest config-check

# Run a workflow
almagest deepresearch "dark matter halos"
almagest source "NGC 1068" --topic "integral field spectroscopy"
almagest watch add "AGN feedback" && almagest watch run --digest
```

There is currently no test suite; `pytest` finds no project tests.

## Repository layout

```
src/almagest/
  cli.py              # Click CLI entry point — all commands live here
  config.py           # Env-var configuration (loads .env from cwd, then ~/.almagest/.env)
  ads_client.py       # NASA ADS REST API wrapper (search, get_paper, export_bibtex, …)
  tools.py            # Tool schemas (JSON for LLM) + dispatch + implementation functions
  agent.py            # Agentic tool-use loop (Agent) and multi-agent runner (MultiAgent)
  output.py           # write_output() — saves .md + .provenance.md sidecar
  llm/
    __init__.py       # get_llm() factory
    base.py           # BaseLLM, Message, ToolCall, LLMResponse dataclasses
    claude.py         # ClaudeLLM via anthropic SDK
    local.py          # LocalLLM via openai SDK (Ollama, LM Studio, vLLM)
  workflows/          # One module per workflow, each exposes run(...)
agents/               # System prompt Markdown files for each agent role
  researcher.md       # Systematic ADS search strategy
  reviewer.md         # Peer review criteria and scoring
  verifier.md         # Reproducibility and audit logic
  writer.md           # Draft and report writing conventions
docs/
  index.html          # Single-file landing page (self-contained, no build step)
AGENTS.md             # Shared conventions: citation format, claim labeling, slug format
SETUP.md              # Credential setup instructions
EXAMPLES.md           # Usage examples for all workflows
.env.example          # Template for environment variables
```

## Environment variables

See `.env.example` for the full list. Key ones:

| Variable | Default | Notes |
|----------|---------|-------|
| `ADS_API_TOKEN` | — | Required. Get at ui.adsabs.harvard.edu/user/settings/token |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=claude` |
| `LLM_PROVIDER` | `claude` | `claude` or `local` |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Any Anthropic model ID |
| `LOCAL_LLM_BASE_URL` | `http://localhost:11434/v1` | Ollama / LM Studio / vLLM |
| `LOCAL_LLM_MODEL` | `llama3.2` | Model name on the local server |
| `OUTPUT_DIR` | `./outputs` | Where reports are saved |
| `WEB_SEARCH_PROVIDER` | `none` | Set to `tavily` to enable `web_search` tool |
| `TAVILY_API_KEY` | — | Required when `WEB_SEARCH_PROVIDER=tavily` |

## How to add a new workflow

1. **`src/almagest/workflows/<name>.py`** — create a `run(...)` function.
   - Accept `console: Console` and `extra_context: str = ""` as standard params.
   - Instantiate `Agent(llm, TOOLS, system=_SYSTEM, name="...")`.
   - Call `write_output(slug=..., artifact_type=..., content=result, workflow="/name")`.

2. **`src/almagest/cli.py`** — add a Click command decorated with `@with_context_options`.
   - Import and call the workflow's `run()`.
   - Use `resolve_context(extra_context, context_file)` to merge `--context` / `--context-file`.

3. **`src/almagest/tools.py`** — if the workflow needs new tools, add:
   - A schema dict in `ADS_TOOLS`, `WEB_TOOLS`, or `FILE_TOOLS`.
   - A dispatch case in `execute_tool()`.
   - An implementation function `_tool_name(...)`.

4. **`EXAMPLES.md`** — add a section with usage examples.
5. **`docs/index.html`** — add a workflow card in the `.workflow-grid` div and update "Ten" in
   the section title, eyebrow, and meta description.

## Key design patterns

### Agent tool-use loop (`agent.py`)
`Agent.run(task, console, extra_context)` runs a loop (max 30 iterations):
- Sends messages to the LLM with tool schemas.
- If LLM returns tool calls, dispatches via `tools.execute_tool()`, appends results, loops.
- When LLM returns a text-only response, that is the final output.
- `extra_context` is prepended to the task prompt.

`MultiAgent.run_parallel` runs multiple `Agent` instances sequentially (no true concurrency yet).

### Tool groups (`tools.py`)
Three composable lists: `ADS_TOOLS`, `WEB_TOOLS`, `FILE_TOOLS`. `ALL_TOOLS = ADS_TOOLS + WEB_TOOLS + FILE_TOOLS`.
Workflows pick the subset they need. The `bash` tool in `FILE_TOOLS` runs arbitrary shell commands.

### ADS client (`ads_client.py`)
- `search(query, limit, sort)` — core search using full ADS Solr syntax.
- `search_object(name, topic, limit, sort)` — uses `object:"name"` (SIMBAD/NED resolution).
  **Important**: ADS does not support combining `object:` with other field searches in one query.
  When `topic` is given, the function fetches up to 200 papers and filters client-side.
- `search_position(ra, dec, radius_deg, topic, limit, sort)` — cone search, same constraint.

### LLM abstraction (`llm/`)
`get_llm()` returns a `ClaudeLLM` or `LocalLLM` based on `LLM_PROVIDER`.
Both expose the same `chat(messages, tools)` interface.
`LocalLLM` tries native function calling first, falls back to JSON block extraction from text.

### Output (`output.py`)
`write_output(slug, artifact_type, content, sources, workflow)` writes:
- `outputs/<slug>-<artifact_type>.md` — the report.
- `outputs/<slug>-<artifact_type>.provenance.md` — sidecar with timestamp, workflow, and sources.

Slug format: `slugify(topic)` — lowercase, hyphens, max 60 chars.

## Output conventions (from `AGENTS.md`)

All generated documents must follow these conventions:

**Inline citations**: **(Author et al. YEAR, `bibcode`)**
Example: (Navarro et al. 1997, `1997ApJ...490..493N`)

**Full bibliography** as a BibTeX block at the end of every document.

**Claim labels**:
| Label | Meaning |
|-------|---------|
| (no label) | Directly supported by cited paper |
| [INFERRED] | Logical inference from cited evidence |
| [UNVERIFIED] | Could not confirm against source |
| [SPECULATIVE] | Author's extrapolation, not from literature |

## Code style

- Python 3.11+, type hints throughout.
- Line length 100 (ruff).
- No docstrings on trivial functions; comment only non-obvious logic.
- Do not add error handling for cases that cannot happen; trust httpx `.raise_for_status()`.
- Keep tool implementation functions (`_tool_name`) as thin wrappers over `ads_client` functions.
