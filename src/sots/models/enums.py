"""Enums from 03 §1 plus Origin (11 §3)."""

from __future__ import annotations

from enum import StrEnum


class ContentType(StrEnum):
    PERSONAL_EXPERIENCE = "personal_experience"
    PERSONAL_BELIEF = "personal_belief"
    NARRATIVE_DEVICE = "narrative_device"
    LESSON_ADVICE = "lesson_advice"
    FACTUAL_CLAIM = "factual_claim"
    MEDIA_REFERENCE = "media_reference"
    QUESTION_REFLECTION = "question_reflection"


class ClaimKind(StrEnum):
    STATISTIC = "statistic"
    LEGAL_CASE = "legal_case"
    HISTORICAL_EVENT = "historical_event"
    ACADEMIC_FINDING = "academic_finding"
    SOCIAL_MEDIA_CASE = "social_media_case"
    NEWS_EVENT = "news_event"
    QUOTE_ATTRIBUTION = "quote_attribution"
    GENERAL_FACT = "general_fact"
    SCRIPTURE_QUOTE = "scripture_quote"
    SCRIPTURE_TERM = "scripture_term"
    PATRISTIC_ATTRIBUTION = "patristic_attribution"
    EVIDENCE_GRADE = "evidence_grade"


class MediaKind(StrEnum):
    BOOK = "book"
    FILM = "film"
    TV = "tv"
    MUSIC = "music"
    GAME = "game"
    PODCAST = "podcast"
    ART = "art"
    OTHER = "other"


class Checkability(StrEnum):
    CHECKABLE = "checkable"
    PARTIAL = "partial"
    NOT_CHECKABLE = "not_checkable"


class SourceClass(StrEnum):
    PRIMARY_RECORD = "primary_record"
    ACADEMIC = "academic"
    REFERENCE = "reference"
    JOURNALISM = "journalism"
    FACT_CHECK_ORG = "fact_check_org"
    OPINION_COMMENTARY = "opinion_commentary"
    SOCIAL_MEDIA = "social_media"
    FICTIONAL_MEDIA = "fictional_media"
    AUTHOR_SUPPLEMENT = "author_supplement"


class Verdict(StrEnum):
    TRUE = "true"
    MOSTLY_TRUE = "mostly_true"
    PARTIALLY_TRUE = "partially_true"
    MISLEADING = "misleading"
    FALSE = "false"
    UNSUPPORTED = "unsupported"
    UNVERIFIABLE = "unverifiable"
    NOT_CHECKABLE = "not_checkable"
    FAILED = "failed"

    def strength(self) -> int:
        """Order index, strongest (TRUE = 0) to weakest (FAILED = 8), per 03 §1."""
        return _VERDICT_ORDER.index(self)


_VERDICT_ORDER: tuple[Verdict, ...] = (
    Verdict.TRUE,
    Verdict.MOSTLY_TRUE,
    Verdict.PARTIALLY_TRUE,
    Verdict.MISLEADING,
    Verdict.FALSE,
    Verdict.UNSUPPORTED,
    Verdict.UNVERIFIABLE,
    Verdict.NOT_CHECKABLE,
    Verdict.FAILED,
)


class Stance(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    MIXED = "mixed"
    CONTEXT = "context"


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class Origin(StrEnum):
    AUTHOR = "author"
    SOURCE = "source"
    SYSTEM = "system"
