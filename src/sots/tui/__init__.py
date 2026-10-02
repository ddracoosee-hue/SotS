"""Terminal UI shell (12 §3.1; D builds the App in P-classify/W1).

Screen registry: each lane registers its screens as `"name":
"module:Class"` in its anchor block. D's shell resolves them lazily so lanes
never edit the shell itself.
"""

from __future__ import annotations

SCREENS: dict[str, str] = {
    # >>> lane-A
    # <<< lane-A
    # >>> lane-B
    # <<< lane-B
    # >>> lane-C
    # <<< lane-C
    # >>> lane-D
    # <<< lane-D
}
