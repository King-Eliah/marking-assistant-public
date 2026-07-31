"""The `make evaluate` report — spec.md §12, M1's acceptance test.

    *"`make evaluate` prints CER/WER/QWK against the golden set."*

Written to be pasted into a dissertation without editing. That means every
number carries what it was measured over and how the text was normalised: a
CER quoted alone is not a reproducible claim, and it is exactly what a viva
will press on.

It also states plainly when there is nothing to measure. A harness that prints
an encouraging zero against an empty golden set is worse than one that refuses
to run.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.evaluation.golden import GoldenSet
from app.evaluation.metrics import (
    ErrorRate,
    Normalisation,
    character_error_rate,
    corpus_error_rate,
    quadratic_weighted_kappa,
    word_error_rate,
)

#: The milestone gates from spec.md §12, so the report can say whether they
#: are met rather than leaving the reader to compare against another document.
CER_GATE_TIER1 = 0.08
CER_GATE_TIER2 = 0.06
QWK_GATE = 0.70


@dataclass(frozen=True, slots=True)
class TranscriptionScore:
    cer: ErrorRate
    wer: ErrorRate
    lines_measured: int
    lines_skipped_illegible: int
    lines_missing: int
    normalisation: Normalisation


@dataclass(frozen=True, slots=True)
class MarkingScore:
    qwk_system_vs_truth: float
    qwk_marker_vs_marker: float
    answers_measured: int

    @property
    def system_matches_human_agreement(self) -> bool:
        """The comparison that actually matters — spec.md §8.4.

        Not "is the system accurate" but "does the system agree with a marker
        about as well as two markers agree with each other". Human markers do
        not agree perfectly, and holding a machine to a standard no human meets
        is the wrong bar.
        """
        return self.qwk_system_vs_truth >= self.qwk_marker_vs_marker


def score_transcriptions(
    golden: GoldenSet,
    predicted: Mapping[str, str],
    normalisation: Normalisation | None = None,
) -> TranscriptionScore:
    """CER and WER over every legible line with a prediction.

    A line the system produced nothing for is counted as missing rather than
    scored as an empty string. Scoring it as empty would report a 100% error
    for that line, which is technically true and buries the real signal: the
    pipeline never reached it at all.
    """
    norm = normalisation or Normalisation()
    cers: list[ErrorRate] = []
    wers: list[ErrorRate] = []
    missing = 0

    for record in golden.legible_transcriptions:
        hypothesis = predicted.get(record.key)
        if hypothesis is None:
            missing += 1
            continue
        cers.append(character_error_rate(record.text, hypothesis, norm))
        wers.append(word_error_rate(record.text, hypothesis, norm))

    return TranscriptionScore(
        cer=corpus_error_rate(cers),
        wer=corpus_error_rate(wers),
        lines_measured=len(cers),
        lines_skipped_illegible=len(golden.transcriptions) - len(golden.legible_transcriptions),
        lines_missing=missing,
        normalisation=norm,
    )


def score_marking(golden: GoldenSet, predicted: Mapping[str, float]) -> MarkingScore | None:
    """Agreement between the system and ground truth, and between the two
    human markers, on the same answers.

    Both are computed over the identical subset so the comparison is fair. A
    system scored on easy answers and humans on all of them would be a
    meaningless pairing.
    """
    truth: list[float] = []
    system: list[float] = []
    marker_a: list[float] = []
    marker_b: list[float] = []
    scale = 0.0

    for record in golden.marks:
        key = f"{record.booklet_id}:{record.question_number}"
        if key not in predicted:
            continue
        truth.append(record.truth)
        system.append(predicted[key])
        marker_a.append(record.marker_a)
        marker_b.append(record.marker_b)
        scale = max(scale, record.max_marks)

    if not truth:
        return None

    return MarkingScore(
        qwk_system_vs_truth=quadratic_weighted_kappa(
            truth, system, min_rating=0, max_rating=scale, step=0.5
        ),
        qwk_marker_vs_marker=quadratic_weighted_kappa(
            marker_a, marker_b, min_rating=0, max_rating=scale, step=0.5
        ),
        answers_measured=len(truth),
    )


def render(
    golden: GoldenSet,
    transcription: TranscriptionScore | None,
    marking: MarkingScore | None,
    *,
    providers: Sequence[str] = (),
) -> str:
    """The report. Plain text, paste-able, self-describing."""
    out: list[str] = []
    out.append("=" * 70)
    out.append("EVALUATION AGAINST THE GOLDEN SET")
    out.append("=" * 70)
    out.append(golden.summary())
    if providers:
        out.append(f"providers: {', '.join(providers)}")
    out.append("")

    if not golden.transcriptions and not golden.marks:
        out.append("The golden set is empty. No accuracy claim can be made.")
        out.append("")
        out.append("Populate apps/api/evaluation/golden/ before quoting any number.")
        out.append("See docs/TASKS.md for what the set needs to contain.")
        return "\n".join(out)

    if transcription is not None and transcription.lines_measured:
        t = transcription
        out.append("TRANSCRIPTION")
        out.append(f"  normalisation      {t.normalisation.describe()}")
        out.append(f"  lines measured     {t.lines_measured}")
        if t.lines_skipped_illegible:
            out.append(f"  illegible, skipped {t.lines_skipped_illegible}")
        if t.lines_missing:
            out.append(f"  no prediction      {t.lines_missing}  <- pipeline never reached these")
        out.append(
            f"  CER                {t.cer.rate:.4f}   "
            f"({t.cer.errors} errors over {t.cer.reference_length} characters)"
        )
        out.append(
            f"  WER                {t.wer.rate:.4f}   "
            f"({t.wer.errors} errors over {t.wer.reference_length} words)"
        )
        for label, gate in (("Tier 1", CER_GATE_TIER1), ("Tier 2", CER_GATE_TIER2)):
            out.append(f"  gate {label}        CER <= {gate:.2f}   {_verdict(t.cer.rate, gate)}")
        out.append("")
    else:
        out.append("TRANSCRIPTION")
        out.append("  no predictions supplied — nothing measured")
        out.append("")

    if marking is not None:
        m = marking
        out.append("MARKING")
        out.append(f"  answers measured   {m.answers_measured}")
        out.append(f"  QWK system vs truth    {m.qwk_system_vs_truth:+.4f}")
        out.append(
            f"  QWK marker vs marker   {m.qwk_marker_vs_marker:+.4f}   <- the human baseline"
        )
        out.append(
            f"  gate               QWK >= {QWK_GATE:.2f}   "
            f"{_verdict(-m.qwk_system_vs_truth, -QWK_GATE)}"
        )
        verdict = (
            "system agrees with a marker at least as well as two markers agree"
            if m.system_matches_human_agreement
            else "system agrees LESS well than two humans do"
        )
        out.append(f"  comparison         {verdict}")
        out.append("")
    else:
        out.append("MARKING")
        out.append("  no dual-marked answers with predictions — nothing measured")
        out.append("")

    out.append("=" * 70)
    return "\n".join(out)


def _verdict(value: float, threshold: float) -> str:
    return "PASS" if value <= threshold else "FAIL"
