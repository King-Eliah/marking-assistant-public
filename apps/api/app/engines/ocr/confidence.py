"""Per-line confidence — spec.md §2.3 step 4.

    line_conf = min( mean(word_conf), 1 - 2 * stdev(word_conf) )

The spread penalty is the interesting half. A plain mean lets one badly-read
word hide inside a confident line, and a single wrong keyword can flip a mark:
"deadlock" read as "deadline" changes the answer entirely while barely moving
an average. Taking the minimum of the mean and a variance penalty means one
uncertain word drags the whole line down, which is exactly the behaviour that
routes it to a second read instead of into a score.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from app.engines.ocr.contracts import OcrWord

#: Multiplier on the standard deviation. Two is deliberately aggressive: the
#: cost of a needless second read is fractions of a cent, and the cost of a
#: missed misread is a wrong mark on a student's record.
SPREAD_PENALTY: float = 2.0


def line_confidence(words: Sequence[OcrWord]) -> float:
    """Confidence for one reconstructed line.

    An empty line is 0.0, not 1.0. "Nothing was read" must never present as
    "read perfectly" — that would let a blank region pass as a confident empty
    answer.
    """
    if not words:
        return 0.0

    scores = [w.confidence for w in words]
    mean = statistics.fmean(scores)

    if len(scores) == 1:
        return max(0.0, min(1.0, mean))

    spread = statistics.stdev(scores)
    return max(0.0, min(1.0, min(mean, 1.0 - SPREAD_PENALTY * spread)))


def page_confidence(line_scores: Sequence[float]) -> float:
    """Confidence for a whole page.

    The mean of its lines, and again 0.0 when there are none. Deliberately not
    the minimum: one unreadable line on an otherwise clean page should route
    that line for transcription, not condemn the page.
    """
    if not line_scores:
        return 0.0
    return max(0.0, min(1.0, statistics.fmean(line_scores)))
