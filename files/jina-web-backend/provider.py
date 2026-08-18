"""Jina Reader web extract — plugin form.

Subclasses :class:`agent.web_search_provider.WebSearchProvider` and
implements only :py:meth:`extract`. The endpoint contract is::

    GET https://r.jina.ai/<url>
    Headers:
        Accept: text/plain                       # default; ask for raw markdown
        Authorization: Bearer ***     # optional — lifts free-tier quota
        X-Return-Format: markdown                 # explicit; safe to send
        X-Timeout: <seconds>                      # server-side render budget
        X-Target-Selector: <css>                  # optional CSS scoping
        X-Remove-Selector: <css>                  # optional CSS pruning
        X-Cookie: <cookie>                        # optional authed content

The response body is plain text beginning with::

    Title: <page title>
    URL Source: <final url after redirects>
    Markdown Content:
    <markdown body...>

Reference: https://jina.ai/reader/

Config keys this provider responds to::

    web:
      extract_backend: "jina"     # explicit per-capability
      backend: "jina"             # shared fallback (default for this plugin)

Env vars::

    JINA_API_KEY=...              # optional — lifts free-tier rate limit
    JINA_TIMEOUT=30              # per-request timeout in seconds (default 30)
    JINA_BASE_URL=...             # override endpoint (default https://r.jina.ai)
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx

from agent.web_search_provider import WebSearchProvider

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://r.jina.ai"
DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 120

_TITLE_RE = re.compile(r"^Title:\s*(?P<title>.+?)\s*$", re.MULTILINE)
_URL_SRC_RE = re.compile(r"^URL Source:\s*(?P<url>\S+)\s*$", re.MULTILINE)
_MD_HEADER = "Markdown Content:"


def _jina_base_url() -> str:
    """Return the configured Jina Reader base URL."""
    try:
        from hermes_cli.config import get_env_value

        val = get_env_value("JINA_BASE_URL")
    except Exception:
        val = None
    if val is None:
        val = os.getenv("JINA_BASE_URL", "")
    return (val or DEFAULT_BASE_URL).strip().rstrip("/")


def _jina_api_key() -> str:
    """Return the configured Jina API key, or empty string for free tier."""
    try:
        from hermes_cli.config import get_env_value

        val = get_env_value("JINA_API_KEY")
    except Exception:
        val = None
    if val is None:
        val = os.getenv("JINA_API_KEY", "")
    return (val or "").strip()


def _jina_timeout() -> float:
    """Return the per-request timeout in seconds."""
    raw = ""
    try:
        from hermes_cli.config import get_env_value

        raw = get_env_value("JINA_TIMEOUT") or ""
    except Exception:
        raw = ""
    if not raw:
        raw = os.getenv("JINA_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        seconds = float(raw)
    except (TypeError, ValueError):
        seconds = float(DEFAULT_TIMEOUT_SECONDS)
    return max(1.0, min(seconds, float(MAX_TIMEOUT_SECONDS)))


def _parse_jina_response(body: str) -> Dict[str, str]:
    """Extract ``title`` and ``url`` from the Jina plain-text header block.

    The Reader response has the shape::

        Title: <title>
        URL Source: <final url>
        Published Time: ...           # optional
        Warning: ...                  # zero or more
        Markdown Content:
        <body...>

    Returns a dict with ``title``, ``url`` and ``content`` (the markdown
    body, trimmed). Missing fields default to empty string so callers can
    rely on the keys being present.
    """
    title = ""
    url = ""
    content = body

    title_match = _TITLE_RE.search(body)
    if title_match:
        title = title_match.group("title").strip()

    url_match = _URL_SRC_RE.search(body)
    if url_match:
        url = url_match.group("url").strip()

    md_idx = body.find(_MD_HEADER)
    if md_idx >= 0:
        content = body[md_idx + len(_MD_HEADER):].lstrip("\r\n")

    return {"title": title, "url": url, "content": content}


def _fetch_one(client: httpx.Client, url: str) -> Dict[str, Any]:
    """Fetch a single URL through Jina Reader and normalise the result."""
    base = _jina_base_url()
    target = f"{base}/{url}"
    headers = {
        "Accept": "text/plain",
        "X-Return-Format": "markdown",
    }
    api_key = _jina_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = client.get(target, headers=headers, follow_redirects=True)
    except httpx.HTTPError as exc:
        logger.warning("Jina extract transport error for %s: %s", url, exc)
        return {
            "url": url,
            "title": "",
            "content": "",
            "error": f"Jina extract failed: {exc}",
        }

    if resp.status_code >= 400:
        # Surface the body if it looks like a structured error (JSON); else
        # truncate to avoid dumping megabytes of HTML into the agent log.
        body_preview = resp.text[:500] if resp.text else ""
        logger.warning(
            "Jina extract HTTP %s for %s: %s",
            resp.status_code,
            url,
            body_preview[:200],
        )
        return {
            "url": url,
            "title": "",
            "content": "",
            "error": (
                f"Jina returned HTTP {resp.status_code}: "
                f"{body_preview[:200]}"
            ),
        }

    parsed = _parse_jina_response(resp.text)
    return {
        "url": parsed["url"] or url,
        "title": parsed["title"],
        "content": parsed["content"],
        "raw_content": parsed["content"],
        "metadata": {
            "sourceURL": parsed["url"] or url,
            "backend": "jina",
            "status_code": resp.status_code,
        },
    }


class JinaWebSearchProvider(WebSearchProvider):
    """Jina Reader extract-only backend."""

    @property
    def name(self) -> str:
        return "jina"

    @property
    def display_name(self) -> str:
        return "Jina Reader"

    def is_available(self) -> bool:
        """Jina Reader is always available — the free tier requires no key.

        ``JINA_API_KEY`` is optional; when set, the free-tier rate limit
        is lifted. Either way the provider is usable, so we always return
        ``True`` here. The actual reachability check happens on the first
        request via httpx.
        """
        return True

    def supports_search(self) -> bool:
        return False

    def supports_extract(self) -> bool:
        return True

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search is not supported by Jina Reader."""
        return {
            "success": False,
            "error": (
                "Jina Reader is an extract-only backend and does not "
                "support search. Use web.search_backend (e.g. ddgs, "
                "brave-free) for search queries."
            ),
        }

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        """Extract content from one or more URLs via Jina Reader.

        Sync implementation — each URL is fetched sequentially with its
        own short-lived httpx client. The dispatcher in tools/web_tools
        wraps this call in ``asyncio.to_thread`` so the event loop is
        never blocked.
        """
        if not urls:
            return []

        try:
            from tools.interrupt import is_interrupted

            if is_interrupted():
                return [
                    {"url": u, "error": "Interrupted", "title": ""} for u in urls
                ]
        except Exception:  # noqa: BLE001 — interrupt module is optional
            pass

        timeout = _jina_timeout()
        logger.info("Jina extract: %d URL(s), timeout=%.1fs", len(urls), timeout)

        results: List[Dict[str, Any]] = []
        with httpx.Client(timeout=timeout) as client:
            for url in urls:
                results.append(_fetch_one(client, url))
        return results

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Jina Reader",
            "badge": "free",
            "tag": (
                "Free extract via r.jina.ai — no API key required. "
                "Optional JINA_API_KEY lifts the free-tier rate limit."
            ),
            "env_vars": [
                {
                    "key": "JINA_API_KEY",
                    "prompt": "Jina API key (optional — lifts free-tier quota)",
                    "url": "https://jina.ai/reader/",
                },
            ],
        }
