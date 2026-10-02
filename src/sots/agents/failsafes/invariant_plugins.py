"""Lane invariant plugins (W0; OWNERSHIP_MAP § lanes).

Each lane defines its checks in `<package>/invariants.py` and imports that
module in its anchor block below. Imports are side-effect-only: importing a
lane module runs its `@register_invariant` decorators. `f20_invariants`
imports this module at its bottom so every check is registered whenever the
registry loads. The core file stays frozen; lanes never edit it.
"""

from __future__ import annotations

# >>> lane-A
from sots.ingest import invariants as ingest_invariants  # noqa: F401
from sots.segment import invariants as segment_invariants  # noqa: F401
# <<< lane-A

# >>> lane-B
# <<< lane-B

# >>> lane-C
# <<< lane-C

# >>> lane-D
# <<< lane-D
