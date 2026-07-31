"""`make evaluate` — spec.md §12, M1's acceptance test.

Exits non-zero when a gate fails, so this can be a CI step rather than a
number someone remembers to look at.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.evaluation.golden import GoldenSetError, load
from app.evaluation.metrics import Normalisation
from app.evaluation.report import (
    CER_GATE_TIER1,
    QWK_GATE,
    render,
    score_marking,
    score_transcriptions,
)

DEFAULT_GOLDEN_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "golden"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="evaluate",
        description="Measure the pipeline against the golden set.",
    )
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN_DIR)
    parser.add_argument(
        "--predictions",
        type=Path,
        default=None,
        help="JSON with {'transcriptions': {key: text}, 'marks': {key: mark}}",
    )
    parser.add_argument("--case-sensitive", action="store_true")
    parser.add_argument("--strip-punctuation", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero unless every gate passes",
    )
    args = parser.parse_args(argv)

    try:
        golden = load(args.golden)
    except GoldenSetError as exc:
        print(f"golden set is malformed: {exc}", file=sys.stderr)
        return 2

    predictions: dict[str, Any] = {"transcriptions": {}, "marks": {}}
    if args.predictions is not None:
        predictions = json.loads(args.predictions.read_text(encoding="utf-8"))

    normalisation = Normalisation(
        lowercase=not args.case_sensitive,
        strip_punctuation=args.strip_punctuation,
    )

    transcription = score_transcriptions(
        golden,
        {str(k): str(v) for k, v in predictions.get("transcriptions", {}).items()},
        normalisation,
    )
    marking = score_marking(
        golden,
        {str(k): float(v) for k, v in predictions.get("marks", {}).items()},
    )

    print(render(golden, transcription, marking))

    if not args.strict:
        return 0

    # An empty golden set fails --strict deliberately. Reporting success
    # against no data is the failure mode this whole milestone exists to
    # prevent.
    if not golden.transcriptions and not golden.marks:
        return 1
    if transcription.lines_measured and transcription.cer.rate > CER_GATE_TIER1:
        return 1
    if marking is not None and marking.qwk_system_vs_truth < QWK_GATE:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
