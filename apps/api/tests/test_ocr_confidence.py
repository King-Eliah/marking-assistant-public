"""Per-line confidence.

    line_conf = min( mean(word_conf), 1 - 2 * stdev(word_conf) )

The spread penalty is the whole design. A plain mean lets one badly-read word
hide inside a confident line, and in this system a single wrong keyword can
flip a mark — "deadlock" read as "deadline" changes the answer entirely while
barely moving an average.
"""

from __future__ import annotations

import pytest

from app.engines.ocr.confidence import SPREAD_PENALTY, line_confidence, page_confidence
from app.engines.ocr.contracts import BBox, OcrWord


def words(*confidences: float) -> list[OcrWord]:
    return [
        OcrWord(text=f"w{i}", confidence=c, bbox=BBox(i * 10, 0, 9, 20))
        for i, c in enumerate(confidences)
    ]


# --- the point of the formula ----------------------------------------------


def test_one_bad_word_drags_the_line_down() -> None:
    """The behaviour the spread penalty exists for.

    Six confident words and one poor one average to 0.87, which would sail past
    a 0.88 threshold on rounding. The spread penalty puts the line well below
    it, where a second read is triggered.
    """
    uniform = line_confidence(words(0.87, 0.87, 0.87, 0.87, 0.87, 0.87, 0.87))
    with_outlier = line_confidence(words(0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.20))

    assert with_outlier < uniform
    assert with_outlier < 0.5, "a badly-read word did not drag the line down"


def test_a_uniformly_confident_line_keeps_its_score() -> None:
    """No spread, no penalty. The formula must not punish a good line."""
    assert line_confidence(words(0.95, 0.95, 0.95, 0.95)) == pytest.approx(0.95)


def test_the_mean_still_caps_the_score() -> None:
    """Consistently mediocre reading is still mediocre, however consistent."""
    assert line_confidence(words(0.60, 0.60, 0.60)) == pytest.approx(0.60)


def test_the_penalty_is_two_standard_deviations() -> None:
    """Stated explicitly so a future tweak is a deliberate act. Two is
    aggressive on purpose: a needless second read costs a fraction of a cent,
    a missed misread costs a wrong mark on a student's record."""
    assert SPREAD_PENALTY == 2.0

    scores = [0.9, 0.7]
    import statistics

    expected = min(statistics.fmean(scores), 1.0 - 2.0 * statistics.stdev(scores))
    assert line_confidence(words(*scores)) == pytest.approx(expected)


# --- edges -----------------------------------------------------------------


def test_an_empty_line_is_zero_not_one() -> None:
    """ "Nothing was read" must never present as "read perfectly" — that would
    let a blank region pass as a confident empty answer."""
    assert line_confidence([]) == 0.0


def test_a_single_word_has_no_spread_to_penalise() -> None:
    assert line_confidence(words(0.75)) == pytest.approx(0.75)


def test_the_result_never_leaves_zero_to_one() -> None:
    """A wide spread drives the penalty negative; a score below zero would
    break every threshold comparison downstream."""
    assert line_confidence(words(1.0, 0.0)) == 0.0
    assert 0.0 <= line_confidence(words(0.99, 0.01, 0.99, 0.01)) <= 1.0


def test_a_word_outside_zero_to_one_is_refused() -> None:
    with pytest.raises(ValueError, match="0..1"):
        OcrWord(text="x", confidence=1.4, bbox=BBox(0, 0, 5, 5))


# --- page level ------------------------------------------------------------


def test_page_confidence_is_the_mean_of_its_lines() -> None:
    assert page_confidence([0.9, 0.8, 0.7]) == pytest.approx(0.8)


def test_one_bad_line_does_not_condemn_the_page() -> None:
    """Deliberately the mean, not the minimum. One unreadable line routes that
    line for transcription; it should not send an otherwise clean page to a
    human."""
    assert page_confidence([0.95, 0.95, 0.95, 0.10]) > 0.6


def test_a_page_with_no_lines_is_zero() -> None:
    assert page_confidence([]) == 0.0
