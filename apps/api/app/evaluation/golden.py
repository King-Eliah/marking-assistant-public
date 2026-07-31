"""The golden set — spec.md §12, milestone M1.

Ground truth: what a human says is on the page, and what a human says it is
worth. Every accuracy number the project reports is measured against this and
nothing else.

Stored as JSONL, one record per line, in the repository rather than a
database. Three reasons, all of which matter for a dissertation:

- it is diffable, so a change to ground truth shows up in review rather than
  happening silently
- it is versioned with the code that was measured against it, so a number in
  the write-up can be reproduced exactly
- it needs no infrastructure to read, which means an examiner can check it

Identifiers here are booklet UUIDs, never student index numbers. The golden
set is shared and discussed; it must not carry identity.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class GoldenSetError(Exception):
    """The golden set is malformed.

    Fatal rather than skippable. A silently dropped record makes every metric
    quietly wrong, and nothing about the output would look unusual.
    """


@dataclass(frozen=True, slots=True)
class TranscriptionRecord:
    """One line of handwriting, as a human read it.

    `text` is what is actually written, including the student's own spelling
    mistakes. Correcting them here would measure the OCR against a text that
    was never on the page.
    """

    booklet_id: uuid.UUID
    page_no: int
    line_index: int
    text: str
    question_number: str | None = None
    #: Set when the writing is genuinely ambiguous to a human too. These are
    #: excluded from CER by default: measuring a machine against text a person
    #: could not read either says nothing about the machine.
    illegible: bool = False

    @property
    def key(self) -> str:
        return f"{self.booklet_id}:{self.page_no}:{self.line_index}"


@dataclass(frozen=True, slots=True)
class MarkRecord:
    """One answer, marked independently by two people.

    Two markers, not one. A single marker's marks are an opinion; two allow
    disagreement to be measured, which is the only way to know whether the
    system is worse than a human or merely different from one particular
    human.
    """

    booklet_id: uuid.UUID
    question_number: str
    max_marks: float
    marker_a: float
    marker_b: float
    #: Set when a third marker adjudicated a disagreement. That resolved value
    #: is the ground truth; the original two are kept to show the spread.
    adjudicated: float | None = None

    def __post_init__(self) -> None:
        for label, value in (("marker_a", self.marker_a), ("marker_b", self.marker_b)):
            if not 0 <= value <= self.max_marks:
                raise GoldenSetError(
                    f"{label}={value} is outside 0..{self.max_marks} for "
                    f"{self.booklet_id} {self.question_number}"
                )

    @property
    def truth(self) -> float:
        """The value to measure the system against."""
        if self.adjudicated is not None:
            return self.adjudicated
        return (self.marker_a + self.marker_b) / 2

    @property
    def markers_disagree(self) -> bool:
        return self.marker_a != self.marker_b


@dataclass(frozen=True, slots=True)
class GoldenSet:
    """Everything the evaluation harness measures against."""

    transcriptions: tuple[TranscriptionRecord, ...] = ()
    marks: tuple[MarkRecord, ...] = ()
    notes: dict[str, str] = field(default_factory=dict)

    @property
    def legible_transcriptions(self) -> tuple[TranscriptionRecord, ...]:
        return tuple(r for r in self.transcriptions if not r.illegible)

    @property
    def booklets(self) -> frozenset[uuid.UUID]:
        return frozenset(
            [r.booklet_id for r in self.transcriptions] + [m.booklet_id for m in self.marks]
        )

    def summary(self) -> str:
        illegible = len(self.transcriptions) - len(self.legible_transcriptions)
        disputed = sum(1 for m in self.marks if m.markers_disagree)
        return (
            f"{len(self.booklets)} booklets · "
            f"{len(self.transcriptions)} lines ({illegible} illegible) · "
            f"{len(self.marks)} dual-marked answers ({disputed} disagreements)"
        )


def _read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise GoldenSetError(f"{path.name} line {number}: {exc}") from exc


def load(directory: Path) -> GoldenSet:
    """Read a golden set from `transcriptions.jsonl` and `marks.jsonl`."""
    transcriptions = []
    for raw in _read_jsonl(directory / "transcriptions.jsonl"):
        try:
            transcriptions.append(
                TranscriptionRecord(
                    booklet_id=uuid.UUID(str(raw["booklet_id"])),
                    page_no=int(raw["page_no"]),
                    line_index=int(raw["line_index"]),
                    text=str(raw["text"]),
                    question_number=(
                        str(raw["question_number"]) if raw.get("question_number") else None
                    ),
                    illegible=bool(raw.get("illegible", False)),
                )
            )
        except (KeyError, ValueError) as exc:
            raise GoldenSetError(f"bad transcription record: {raw}") from exc

    marks = []
    for raw in _read_jsonl(directory / "marks.jsonl"):
        try:
            marks.append(
                MarkRecord(
                    booklet_id=uuid.UUID(str(raw["booklet_id"])),
                    question_number=str(raw["question_number"]),
                    max_marks=float(raw["max_marks"]),
                    marker_a=float(raw["marker_a"]),
                    marker_b=float(raw["marker_b"]),
                    adjudicated=(
                        float(raw["adjudicated"]) if raw.get("adjudicated") is not None else None
                    ),
                )
            )
        except (KeyError, ValueError) as exc:
            raise GoldenSetError(f"bad mark record: {raw}") from exc

    duplicates = _duplicate_keys([r.key for r in transcriptions])
    if duplicates:
        raise GoldenSetError(
            f"duplicate transcription keys: {sorted(duplicates)[:5]}. Two ground "
            f"truths for one line means the metric silently depends on ordering."
        )

    return GoldenSet(transcriptions=tuple(transcriptions), marks=tuple(marks))


def _duplicate_keys(keys: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for key in keys:
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates
