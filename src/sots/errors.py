"""SotS exception hierarchy (P00 T00.040).

Every SotS-specific failure derives from :class:`SotsError` so callers can
catch one base type. Each subclass documents the phase that raises it.
"""

from __future__ import annotations


class SotsError(Exception):
    """Base class for every SotS-specific error."""


class ConfigError(SotsError):
    """Configuration is missing, unreadable, or fails validation (P00)."""


class ProviderNotConfiguredError(SotsError):
    """An LLM provider was requested without credentials or model (P01/P02)."""


class BudgetExceededError(SotsError):
    """A run hit its token or cost budget and must stop (P01)."""


class ValidationFailedError(SotsError):
    """A model output failed schema or contract validation (P01+)."""


class WriterDisabledError(SotsError):
    """Prose generation was attempted; the writer is disabled until P11 (P00/P11)."""


class GateFailedError(SotsError):
    """A pipeline gate rejected the unit (P04+)."""


class InvariantBrokenError(SotsError):
    """An internal invariant was violated; this is always a bug (any phase)."""


class KillSwitchError(SotsError):
    """The operator kill switch stopped the run (P01)."""


class ToolNotAllowedError(SotsError):
    """An agent attempted a tool outside its allow-list (P01)."""


class LoopDetectedError(SotsError):
    """An agent looped without progress and was halted (P01+)."""


class AdultsOnlyViolation(SotsError):
    """A persona or panel member under 18 was detected (P00/P09)."""


class ToolTimeoutError(SotsError):
    """A tool call exceeded its F01 timeout (P03)."""


class CircuitOpenError(SotsError):
    """A call was refused because the F03 circuit is open (P03)."""


class CheckpointCorruptError(SotsError):
    """A checkpoint hash mismatch forced a restart from scratch (P03)."""


class ReplayMismatchError(SotsError):
    """A replayed call did not match the recording (P03)."""


class CanaryFailedError(SotsError):
    """The F19 canary run failed; the full run is aborted (P03)."""
