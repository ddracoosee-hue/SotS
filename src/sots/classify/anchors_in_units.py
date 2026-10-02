"""Anchor tagging for units (P04A T04A.032, 23 §5).

Thin seam over the registry matcher (T04A.003): normalized entity + keyword
matching across ALL chapters, since reuse anchors span chapters. Called by
segmentation (P05) and the block-mapper.
"""

from __future__ import annotations

from sots.foundation.anchors import AnchorRegistry


def tag_anchors(text: str, registry: AnchorRegistry) -> list[str]:
    """Anchor ids mentioned in the unit text (registry order, all chapters)."""
    return registry.match_in_text(text)
