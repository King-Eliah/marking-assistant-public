"""Accuracy metrics — spec.md §8.

The point of this module is stated plainly in the spec: it is what separates a
project that *claims* accuracy from one that can *prove* it. It exists before
the pipeline it measures, deliberately, so that no number is ever reported
without a way to check it.

Every function here is pure. No database, no network, no clock — the same
inputs always give the same number, which is what makes a result in a
write-up reproducible by someone else six months later.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

#: Whitespace runs collapse to a single space. Never optional: a transcriber
#: typing two spaces between sentences is not an OCR error, and counting it as
#: one would inflate every score for no reason.
_WHITESPACE: Final[re.Pattern[str]] = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class Normalisation:
    """How text is prepared before comparison.

    Made explicit and recorded with every result, because it materially moves
    the number. A CER quoted without saying whether case and punctuation were
    folded is not a reproducible measurement, and "we got 6%" is exactly the
    claim a viva will press on.

    The defaults are the conservative ones: fold case, keep punctuation.
    Lowercasing is standard for handwriting evaluation because letter case is
    frequently ambiguous in cursive. Punctuation is kept because a missing "not"
    and a missing full stop are not equally serious, and discarding punctuation
    hides the difference.
    """

    lowercase: bool = True
    strip_punctuation: bool = False
    collapse_whitespace: bool = True

    def apply(self, text: str) -> str:
        # NFKC first, so a composed and a decomposed accent do not count as an
        # error against each other.
        out = unicodedata.normalize("NFKC", text)
        if self.lowercase:
            out = out.lower()
        if self.strip_punctuation:
            out = "".join(c for c in out if not unicodedata.category(c).startswith("P"))
        if self.collapse_whitespace:
            out = _WHITESPACE.sub(" ", out)
        return out.strip()

    def describe(self) -> str:
        parts = []
        parts.append("lowercased" if self.lowercase else "case-sensitive")
        parts.append("punctuation stripped" if self.strip_punctuation else "punctuation kept")
        return ", ".join(parts)


def edit_distance(reference: Sequence[str], hypothesis: Sequence[str]) -> int:
    """Levenshtein distance over any sequence.

    Works on characters or on words, which is the only difference between CER
    and WER. Uses two rows rather than a full matrix so a long page does not
    allocate megabytes.
    """
    if not reference:
        return len(hypothesis)
    if not hypothesis:
        return len(reference)

    previous = list(range(len(hypothesis) + 1))
    for i, ref_item in enumerate(reference, start=1):
        current = [i]
        for j, hyp_item in enumerate(hypothesis, start=1):
            current.append(
                min(
                    previous[j] + 1,  # deletion
                    current[j - 1] + 1,  # insertion
                    previous[j - 1] + (ref_item != hyp_item),  # substitution
                )
            )
        previous = current
    return previous[-1]


@dataclass(frozen=True, slots=True)
class ErrorRate:
    """One error-rate measurement and the counts behind it.

    The counts are kept because the rate alone is not enough to act on. A 10%
    CER made of substitutions is a legibility problem; the same rate made of
    insertions usually means line reconstruction is merging two lines.
    """

    errors: int
    reference_length: int

    @property
    def rate(self) -> float:
        """Errors per reference unit. Can exceed 1.0 when the hypothesis is
        much longer than the reference — that is real and should not be hidden
        by clamping."""
        if self.reference_length == 0:
            return 0.0 if self.errors == 0 else 1.0
        return self.errors / self.reference_length

    @property
    def accuracy(self) -> float:
        return max(0.0, 1.0 - self.rate)


def character_error_rate(
    reference: str, hypothesis: str, normalisation: Normalisation | None = None
) -> ErrorRate:
    """CER for one transcript against its ground truth."""
    norm = normalisation or Normalisation()
    ref, hyp = norm.apply(reference), norm.apply(hypothesis)
    return ErrorRate(errors=edit_distance(ref, hyp), reference_length=len(ref))


def word_error_rate(
    reference: str, hypothesis: str, normalisation: Normalisation | None = None
) -> ErrorRate:
    """WER for one transcript against its ground truth."""
    norm = normalisation or Normalisation()
    ref = norm.apply(reference).split()
    hyp = norm.apply(hypothesis).split()
    return ErrorRate(errors=edit_distance(ref, hyp), reference_length=len(ref))


def corpus_error_rate(rates: Sequence[ErrorRate]) -> ErrorRate:
    """Aggregate over a corpus by pooling counts, not by averaging rates.

    Averaging per-line rates weights a three-character line the same as a
    forty-word one, which flatters a system that fails on long lines. Pooling
    is the standard definition and the honest one.
    """
    return ErrorRate(
        errors=sum(r.errors for r in rates),
        reference_length=sum(r.reference_length for r in rates),
    )


def quadratic_weighted_kappa(
    rater_a: Sequence[float],
    rater_b: Sequence[float],
    *,
    min_rating: float | None = None,
    max_rating: float | None = None,
    step: float = 1.0,
) -> float:
    """Agreement between two sets of marks, corrected for chance.

    The standard measure for ordinal agreement, and the right one for marks
    because the weighting is quadratic: disagreeing by one mark is a small
    penalty, disagreeing by five is a large one. Plain accuracy would treat
    those identically, and Cohen's unweighted kappa would too.

    Returns 1.0 for perfect agreement, 0.0 for agreement no better than chance,
    and can be negative when two raters disagree more than random assignment
    would.
    """
    if len(rater_a) != len(rater_b):
        raise ValueError(f"raters must be the same length, got {len(rater_a)} and {len(rater_b)}")
    if not rater_a:
        raise ValueError("cannot measure agreement over an empty set")

    lo = min_rating if min_rating is not None else min(min(rater_a), min(rater_b))
    hi = max_rating if max_rating is not None else max(max(rater_a), max(rater_b))

    if hi == lo:
        # Every mark identical. Kappa is undefined — there is no variance for
        # chance agreement to be measured against. Returning 1.0 would claim
        # perfect agreement on no evidence, so this is reported honestly as
        # "no discrimination possible".
        return 1.0 if list(rater_a) == list(rater_b) else 0.0

    buckets = int(round((hi - lo) / step)) + 1

    def index(value: float) -> int:
        return max(0, min(buckets - 1, int(round((value - lo) / step))))

    observed = [[0.0] * buckets for _ in range(buckets)]
    for a, b in zip(rater_a, rater_b, strict=True):
        observed[index(a)][index(b)] += 1

    hist_a = [0.0] * buckets
    hist_b = [0.0] * buckets
    for a, b in zip(rater_a, rater_b, strict=True):
        hist_a[index(a)] += 1
        hist_b[index(b)] += 1

    n = float(len(rater_a))
    denominator_weight = (buckets - 1) ** 2

    numerator = 0.0
    denominator = 0.0
    for i in range(buckets):
        for j in range(buckets):
            weight = ((i - j) ** 2) / denominator_weight
            expected = hist_a[i] * hist_b[j] / n
            numerator += weight * observed[i][j]
            denominator += weight * expected

    if denominator == 0:
        return 1.0 if numerator == 0 else 0.0
    return 1.0 - numerator / denominator


def overall_confidence(*confidences: float) -> float:
    """Combine the pipeline's confidences — spec.md §8.1.

    The minimum, never the mean. A mean lets a perfect photograph hide an
    unreadable answer; a pipeline is only as trustworthy as its weakest stage,
    so the minimum is the honest aggregation.
    """
    if not confidences:
        raise ValueError("at least one confidence is required")
    return min(confidences)
