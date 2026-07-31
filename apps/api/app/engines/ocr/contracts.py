"""Engine 2 contracts — spec.md §2.2.

These types are the boundary between OCR and everything downstream. They
deliberately carry no provider-specific structure: swapping Google Vision for
a self-hosted engine must not ripple past `app/engines/ocr/`.

Note what is absent. There is no field for a mark, a score, or any number that
could reach one. OCR reports what it read and how sure it is; judgement happens
in Engine 3 and arithmetic in Engine 4 (I2).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class BBox:
    """Pixel rectangle on the rectified page, top-left origin.

    Rectified, so these coordinates are comparable across photographs of the
    same booklet — which is what lets evidence highlighting point at the same
    place every time a page is viewed.
    """

    x: int
    y: int
    w: int
    h: int

    def __post_init__(self) -> None:
        if self.w <= 0 or self.h <= 0:
            raise ValueError(f"a box must have positive extent, got {self.w}x{self.h}")

    @property
    def centre_y(self) -> float:
        return self.y + self.h / 2


class LineSource(StrEnum):
    """Where a line's final text came from.

    Recorded per line rather than per page: a page is usually a mixture, and a
    marker deciding how much to trust a transcript needs to know which lines
    were arbitrated and which were read once.
    """

    TIER1 = "TIER1"
    AGREED = "AGREED"
    ARBITRATED = "ARBITRATED"
    HUMAN = "HUMAN"
    UNRESOLVED = "UNRESOLVED"


class LineFlag(StrEnum):
    """Structural facts about a line that downstream engines must respect."""

    STRUCK_THROUGH = "STRUCK_THROUGH"
    TIER2_DISAGREEMENT = "TIER2_DISAGREEMENT"
    NEEDS_HUMAN_TRANSCRIPTION = "NEEDS_HUMAN_TRANSCRIPTION"
    CONTAINS_NUMERALS = "CONTAINS_NUMERALS"
    NEAR_RUBRIC_KEYWORD = "NEAR_RUBRIC_KEYWORD"
    HIGH_CONFIDENCE_VARIANCE = "HIGH_CONFIDENCE_VARIANCE"
    INJECTION_PATTERN = "INJECTION_PATTERN"


@dataclass(frozen=True, slots=True)
class OcrWord:
    text: str
    confidence: float
    bbox: BBox

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in 0..1, got {self.confidence}")


@dataclass(frozen=True, slots=True)
class OcrLine:
    """One visual line of handwriting."""

    line_index: int
    text: str
    confidence: float
    bbox: BBox
    words: tuple[OcrWord, ...] = ()
    source: LineSource = LineSource.TIER1
    question_number: str | None = None
    flags: frozenset[LineFlag] = frozenset()

    @property
    def struck_through(self) -> bool:
        return LineFlag.STRUCK_THROUGH in self.flags

    @property
    def needs_human(self) -> bool:
        return LineFlag.NEEDS_HUMAN_TRANSCRIPTION in self.flags


@dataclass(frozen=True, slots=True)
class OcrResult:
    """Everything Engine 2 produces for one page."""

    page_id: uuid.UUID
    lines: tuple[OcrLine, ...]
    page_confidence: float
    cost_usd: float
    providers_used: tuple[str, ...]
    #: True when this came from cache. Re-running must cost nothing, and a
    #: caller that cannot tell would report spend it never incurred.
    from_cache: bool = False

    @property
    def readable_lines(self) -> tuple[OcrLine, ...]:
        """Lines usable for scoring.

        Struck-through text is excluded here rather than downstream: a student
        who crossed something out has withdrawn it, and scoring withdrawn text
        is both wrong and the kind of thing that gets noticed at appeal.
        """
        return tuple(
            line
            for line in self.lines
            if not line.struck_through and line.source is not LineSource.UNRESOLVED
        )


@dataclass(frozen=True, slots=True)
class OcrHints:
    """What the caller knows that helps the provider.

    `rubric_lexicon` is used only to *flag* lines for a second read, never to
    correct them. Rewriting a student's words toward the rubric would
    manufacture the evidence the mark is then justified by.
    """

    language: str = "en"
    rubric_lexicon: tuple[str, ...] = ()
    question_regions: tuple[tuple[str, BBox], ...] = ()
    tier2_threshold: float = 0.88
    max_tier2_lines_per_page: int = 30
    extra: dict[str, str] = field(default_factory=dict)
