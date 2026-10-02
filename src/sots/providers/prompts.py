"""Versioned prompt template loader (P02 T02.011, R-LLM-02).

Prompts live at `prompts/<id>.v<N>.md` (`prompts/verify/skeptic.v1.md`), with
a YAML front-matter header (`id`, `version`, `variables`, `output_model`) and
a `string.Template` body (`$name` syntax only). Every declared variable must
be provided, and unknown variables are rejected, so template/render drift
fails loudly instead of silently.
"""

from __future__ import annotations

import re
import string
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from sots.errors import ConfigError

PROMPT_VERSION_RE = re.compile(r"^(.*)\.v(\d+)\.md$")


class PromptTemplate(BaseModel):
    """A parsed prompt file plus its declared contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: int
    variables: list[str]
    output_model: str
    body: str

    def render(self, variables: dict[str, str]) -> str:
        """Fill `$variables`; missing or undeclared names raise ConfigError."""
        declared = set(self.variables)
        provided = set(variables)
        missing = sorted(declared - provided)
        if missing:
            raise ConfigError(
                f"prompt {self.id}.v{self.version} missing variables: {', '.join(missing)}"
            )
        unknown = sorted(provided - declared)
        if unknown:
            raise ConfigError(
                f"prompt {self.id}.v{self.version} got undeclared variables: "
                f"{', '.join(unknown)}"
            )
        return string.Template(self.body).substitute(variables)


def available_versions(prompts_dir: str | Path, prompt_id: str) -> list[int]:
    """Sorted versions present for a prompt id (empty when none exist)."""
    root = Path(prompts_dir)
    parent = root / Path(prompt_id).parent
    stem = Path(prompt_id).name
    if not parent.is_dir():
        return []
    versions: list[int] = []
    for path in parent.glob(f"{stem}.v*.md"):
        match = PROMPT_VERSION_RE.match(path.name)
        if match and match.group(1) == stem:
            versions.append(int(match.group(2)))
    return sorted(versions)


def load_prompt(
    prompts_dir: str | Path, prompt_id: str, version: int | None = None
) -> PromptTemplate:
    """Load (and validate) a prompt file; None version picks the latest.

    Raises ConfigError when the file is missing, the header is invalid, or
    the header id/version disagree with the request.
    """
    root = Path(prompts_dir)
    wanted = version
    if wanted is None:
        found = available_versions(root, prompt_id)
        if not found:
            raise ConfigError(f"no prompt file for id {prompt_id!r} in {root}")
        wanted = found[-1]
    assert wanted is not None
    path = root / f"{prompt_id}.v{wanted}.md"
    if not path.is_file():
        raise ConfigError(f"prompt file not found: {path}")
    header, body = _split_header(path)
    try:
        data = yaml.safe_load(header) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid prompt header in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"prompt header in {path} must be a mapping")
    return _validate(path, prompt_id, wanted, data, body)


def _split_header(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ConfigError(f"prompt file {path} must start with a --- header")
    for end in range(1, len(lines)):
        if lines[end].strip() in ("---", "..."):
            return "".join(lines[1:end]), "".join(lines[end + 1 :])
    raise ConfigError(f"prompt file {path} has an unterminated --- header")


def _validate(
    path: Path, prompt_id: str, wanted: int, data: dict[str, Any], body: str
) -> PromptTemplate:
    header_id = data.get("id")
    header_version = data.get("version")
    if header_id != prompt_id:
        raise ConfigError(f"prompt {path} header id {header_id!r} != {prompt_id!r}")
    if header_version != wanted:
        raise ConfigError(f"prompt {path} header version {header_version!r} != {wanted}")
    variables = data.get("variables", [])
    output_model = data.get("output_model")
    if not isinstance(variables, list) or not all(isinstance(v, str) for v in variables):
        raise ConfigError(f"prompt {path} header 'variables' must be a string list")
    if not isinstance(output_model, str) or not output_model:
        raise ConfigError(f"prompt {path} header 'output_model' must be a string")
    if not body.strip():
        raise ConfigError(f"prompt {path} has an empty body")
    return PromptTemplate(
        id=prompt_id, version=wanted, variables=list(variables),
        output_model=output_model, body=body.strip() + "\n",
    )
