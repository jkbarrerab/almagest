"""Configuration loaded from environment / .env file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from cwd, then from home dir as fallback
load_dotenv(Path.cwd() / ".env", override=False)
load_dotenv(Path.home() / ".almagest" / ".env", override=False)


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(
            f"Missing required env var: {key}\n"
            f"Copy .env.example to .env and fill in your credentials."
        )
    return val


def ads_token() -> str:
    return _require("ADS_API_TOKEN")


def llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "claude").lower()


def claude_model() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


def anthropic_key() -> str:
    return _require("ANTHROPIC_API_KEY")


def local_llm_base_url() -> str:
    return os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")


def local_llm_model() -> str:
    return os.getenv("LOCAL_LLM_MODEL", "llama3.2")


def local_llm_api_key() -> str:
    return os.getenv("LOCAL_LLM_API_KEY", "ollama")


def output_dir() -> Path:
    d = Path(os.getenv("OUTPUT_DIR", "./outputs"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def ads_max_results() -> int:
    return int(os.getenv("ADS_MAX_RESULTS", "20"))


def web_search_provider() -> str:
    return os.getenv("WEB_SEARCH_PROVIDER", "none").lower()


def tavily_key() -> str | None:
    return os.getenv("TAVILY_API_KEY") or None
