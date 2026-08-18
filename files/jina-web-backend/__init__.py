"""Jina Reader web extract plugin — bundled, auto-loaded.

Wraps https://r.jina.ai as a ``web_extract`` backend. Jina Reader is a
public, free-tier service that converts arbitrary URLs to clean markdown
with no JavaScript rendering required. No API key is required for
moderate use; setting ``JINA_API_KEY`` raises the quota.

Extract-only by design — Jina Reader does not provide a search endpoint,
so :py:meth:`supports_search` returns ``False`` and the provider will
register itself only for ``extract`` dispatch.
"""

from __future__ import annotations

from plugins.web.jina.provider import JinaWebSearchProvider


def register(ctx) -> None:
    """Register the Jina provider with the plugin context."""
    ctx.register_web_search_provider(JinaWebSearchProvider())
