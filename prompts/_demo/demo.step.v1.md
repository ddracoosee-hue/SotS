---
id: _demo/demo.step
version: 1
variables:
  - goal
  - scratchpad
output_model: AgentAction
---
Goal: $goal

$scratchpad

Respond with your next step as JSON: either {"type": "tool", "tool": "<name>",
"args": {...}, "thought": "<= 60 words", "final": null} or {"type": "final",
"tool": null, "args": null, "thought": "<= 60 words>", "final": {...}}.
