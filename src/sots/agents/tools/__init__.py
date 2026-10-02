"""Tool registry bootstrap: importing this package registers every tool."""

from __future__ import annotations

from sots.agents.tools import (  # noqa: F401  (registration side effects)
    compute,
    db_read,
    excerpt_verify,
    fetch_url,
    languagetool,
    parse_html,
    parse_pdf,
    parse_table,
    structured_lookups,
    web_search,
)
from sots.agents.tools.base import get_tool, registered_tools

__all__ = ["get_tool", "registered_tools"]
