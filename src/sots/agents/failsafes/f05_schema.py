"""F05 schema guard for agent finals (P03 T03.044, 16 §5.1).

Validates the final payload against the output model, and additionally
rejects outputs that echo the prompt (verbatim head match) or smuggle in
`<observation>` tags. Failures raise ValidationFailedError for the repair
retry (R-LLM-03).
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from sots.errors import ValidationFailedError

_ECHO_HEAD_CHARS = 300
_ECHO_MIN_PROMPT = 50
_OBSERVATION_TAG = re.compile(r"<observation[\s>]", re.IGNORECASE)


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def check_output[T: BaseModel](
    model: type[T], data: Any, *, prompt_text: str = ""
) -> T:
    """Validate `data` as `model`, rejecting echoes and observation tags."""
    if isinstance(data, str):
        rendered = data
        try:
            data = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ValidationFailedError(f"final output is not JSON: {exc}") from exc
    else:
        rendered = json.dumps(data, sort_keys=True, default=str)
    if _OBSERVATION_TAG.search(rendered):
        raise ValidationFailedError("final output contains <observation> tags")
    prompt_head = _normalize(prompt_text)[:_ECHO_HEAD_CHARS]
    if len(prompt_head) >= _ECHO_MIN_PROMPT and prompt_head in _normalize(rendered):
        raise ValidationFailedError("final output echoes the prompt")
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise ValidationFailedError(f"final output failed validation: {exc}") from exc
