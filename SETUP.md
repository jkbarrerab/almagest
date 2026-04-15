# Setup & Credentials

## 1. Get your API keys

### NASA ADS token (required)

1. Go to [https://ui.adsabs.harvard.edu/user/settings/token](https://ui.adsabs.harvard.edu/user/settings/token)
2. Log in (or create a free account)
3. Your API token is displayed on that page — copy it

### Anthropic API key (required if using Claude)

1. Go to [https://console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
2. Click **Create Key**, give it a name (e.g. `almagest`)
3. Copy the key — it starts with `sk-ant-`

---

## 2. Configure your environment

Copy the example file and fill in your keys:

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```env
ADS_API_TOKEN=your_ads_token_here
ANTHROPIC_API_KEY=sk-ant-...
```

All other settings have sensible defaults but can be customised:

| Variable | Default | Description |
|----------|---------|-------------|
| `ADS_API_TOKEN` | — | **Required.** NASA ADS API token |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=claude` |
| `LLM_PROVIDER` | `claude` | `claude` or `local` |
| `CLAUDE_MODEL` | `claude-opus-4-6` | Any Claude model ID |
| `OUTPUT_DIR` | `./outputs` | Where research files are saved |
| `ADS_MAX_RESULTS` | `20` | Max papers per ADS search |
| `WEB_SEARCH_PROVIDER` | `none` | `none` or `tavily` |
| `TAVILY_API_KEY` | — | Required only if web search is enabled |

---

## 3. Install the package

The tool requires Python 3.11+. A virtual environment is included.

```bash
# Create virtual environment (first time only)
/opt/homebrew/bin/python3.11 -m venv .venv

# Install
.venv/bin/pip install -e .
```

---

## 4. Verify your setup

```bash
.venv/bin/almagest config-check
```

Expected output:

```
╭─ Configuration Check ─╮
  ✓ ADS_API_TOKEN: abc123...
  ✓ LLM_PROVIDER: claude
  ✓ ANTHROPIC_API_KEY: sk-ant-...
    model: claude-opus-4-6
    output dir: ./outputs

All checks passed.
```

---

## 5. (Optional) Use a local LLM instead of Claude

If you prefer to run a local model (Ollama, LM Studio, vLLM, or any
OpenAI-compatible server), update `.env`:

```env
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama3.2
LOCAL_LLM_API_KEY=ollama
```

### Ollama quick start

```bash
# Install: https://ollama.com
ollama pull llama3.2
ollama serve        # starts the server at localhost:11434
```

> **Note**: Local models without native tool-use support will fall back to a
> text-based tool-calling mode. Results may be less reliable than with Claude.

---

## 6. (Optional) Enable web search

Web search lets agents look beyond ADS for blog posts, GitHub repos,
documentation, and preprints not yet indexed.

```bash
# Get a free key at https://tavily.com
pip install tavily-python
```

```env
WEB_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=tvly-...
```

---

## 7. (Optional) Add `almagest` to your PATH

To call `almagest` from any directory without the `.venv/bin/` prefix:

```bash
# Add to ~/.zshrc or ~/.bashrc
export PATH="/Users/$(whoami)/Documents/aider_home/arxiv_skills/.venv/bin:$PATH"
```

Then reload your shell:

```bash
source ~/.zshrc
almagest --help
```
