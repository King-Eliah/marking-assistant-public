"""Accuracy metrics.

These are the numbers the whole write-up rests on, so the tests check known
values by hand rather than asserting that the code agrees with itself. A
metric that is subtly wrong produces a number nobody can challenge and
everybody believes.
"""

from __future__ import annotations

import pytest

from app.evaluation.metrics import (
    ErrorRate,
    Normalisation,
    character_error_rate,
    corpus_error_rate,
    edit_distance,
    overall_confidence,
    quadratic_weighted_kappa,
    word_error_rate,
)

# --- edit distance ---------------------------------------------------------


def test_identical_sequences_have_no_distance() -> None:
    assert edit_distance("deadlock", "deadlock") == 0


def test_a_substitution_costs_one() -> None:
    assert edit_distance("cat", "cut") == 1


def test_the_deadlock_deadline_case() -> None:
    """The confusion the whole system worries about.

    Three substitutions — o->i, c->n, k->e — out of eight characters, so a CER
    of 0.375 on the word. But the *meaning* is completely different, which is
    the point: a small edit distance is not a small error when the word is a
    rubric keyword. This is why lines near a rubric term are flagged for a
    second read regardless of confidence (spec.md §2.1).
    """
    assert edit_distance("deadlock", "deadline") == 3


def test_insertion_and_deletion_each_cost_one() -> None:
    assert edit_distance("cat", "cart") == 1
    assert edit_distance("cart", "cat") == 1


def test_distance_against_an_empty_sequence_is_its_length() -> None:
    assert edit_distance("", "abc") == 3
    assert edit_distance("abc", "") == 3


def test_a_known_value() -> None:
    """kitten -> sitting is the textbook example, distance 3."""
    assert edit_distance("kitten", "sitting") == 3


# --- CER -------------------------------------------------------------------


def test_a_perfect_transcript_has_zero_cer() -> None:
    assert character_error_rate("Deadlock occurs.", "Deadlock occurs.").rate == 0.0


def test_cer_is_errors_over_reference_length() -> None:
    result = character_error_rate("abcdefghij", "abcdefghXX")
    assert result.errors == 2
    assert result.reference_length == 10
    assert result.rate == pytest.approx(0.2)


def test_cer_can_exceed_one() -> None:
    """A hypothesis far longer than the reference genuinely has a rate above
    1.0. Clamping would hide a runaway OCR producing pages of noise."""
    assert character_error_rate("hi", "hello there everyone").rate > 1.0


def test_an_empty_reference_with_empty_output_is_not_an_error() -> None:
    """A blank answer transcribed as blank is correct, not a divide by zero."""
    assert character_error_rate("", "").rate == 0.0


def test_an_empty_reference_with_output_is_a_full_error() -> None:
    """OCR inventing text where the student wrote nothing is the worst kind of
    error, so it must not be reported as 0."""
    assert character_error_rate("", "hallucinated").rate == 1.0


# --- normalisation, which moves the number ---------------------------------


def test_case_is_folded_by_default() -> None:
    """Letter case is frequently ambiguous in handwriting, so counting it is
    measuring the wrong thing."""
    assert character_error_rate("Deadlock", "deadlock").rate == 0.0


def test_case_can_be_kept() -> None:
    strict = Normalisation(lowercase=False)
    assert character_error_rate("Deadlock", "deadlock", strict).errors == 1


def test_punctuation_is_kept_by_default() -> None:
    """A missing 'not' and a missing full stop are not equally serious.
    Discarding punctuation hides the difference."""
    assert character_error_rate("yes, it holds", "yes it holds").errors == 1


def test_punctuation_can_be_stripped() -> None:
    loose = Normalisation(strip_punctuation=True)
    assert character_error_rate("yes, it holds.", "yes it holds", loose).rate == 0.0


def test_whitespace_runs_do_not_count_as_errors() -> None:
    """A transcriber typing two spaces is not an OCR failure."""
    assert character_error_rate("a b", "a    b").rate == 0.0


def test_composed_and_decomposed_accents_match() -> None:
    assert character_error_rate("café", "café").rate == 0.0


def test_the_normalisation_describes_itself() -> None:
    """A CER quoted without saying how text was normalised is not a
    reproducible measurement."""
    assert "lowercased" in Normalisation().describe()
    assert "punctuation kept" in Normalisation().describe()


# --- WER -------------------------------------------------------------------


def test_wer_counts_whole_words() -> None:
    result = word_error_rate("the cat sat on the mat", "the dog sat on the mat")
    assert result.errors == 1
    assert result.reference_length == 6


def test_wer_is_harsher_than_cer_for_a_one_letter_slip() -> None:
    """One wrong character ruins one whole word. That is the right emphasis
    here: a word is the unit a marking point is matched against."""
    cer = character_error_rate("mutual exclusion", "mutual exclusiom")
    wer = word_error_rate("mutual exclusion", "mutual exclusiom")
    assert wer.rate > cer.rate


# --- corpus aggregation ----------------------------------------------------


def test_a_corpus_pools_counts_rather_than_averaging_rates() -> None:
    """Averaging per-line rates weights a three-character line the same as a
    forty-word one, which flatters a system that fails on long lines."""
    short_bad = ErrorRate(errors=2, reference_length=4)  # 50%
    long_good = ErrorRate(errors=2, reference_length=196)  # ~1%

    pooled = corpus_error_rate([short_bad, long_good])
    naive_mean = (short_bad.rate + long_good.rate) / 2

    assert pooled.rate == pytest.approx(4 / 200)
    assert pooled.rate < naive_mean / 5


def test_an_empty_corpus_does_not_divide_by_zero() -> None:
    assert corpus_error_rate([]).rate == 0.0


# --- QWK -------------------------------------------------------------------


def test_identical_marks_are_perfect_agreement() -> None:
    marks = [0, 1, 2, 3, 4, 5, 4, 3, 2, 1]
    assert quadratic_weighted_kappa(marks, marks) == pytest.approx(1.0)


def test_a_one_mark_disagreement_is_penalised_gently() -> None:
    """Quadratic weighting is why QWK is the right measure for marks: being
    one out is nearly agreement, being five out is not."""
    a = [0, 2, 4, 6, 8, 10, 4, 6, 2, 8]
    close = [1, 3, 5, 7, 9, 10, 5, 7, 3, 9]
    far = [10, 8, 6, 4, 2, 0, 8, 2, 10, 0]

    assert quadratic_weighted_kappa(a, close) > quadratic_weighted_kappa(a, far)
    assert quadratic_weighted_kappa(a, close) > 0.8


def test_reversed_marks_score_below_chance() -> None:
    a = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert quadratic_weighted_kappa(a, list(reversed(a))) < 0.0


def test_the_scale_can_be_declared() -> None:
    """A question out of 10 where both markers only used 4-6 still has a 0-10
    scale. Inferring it from the data would make agreement look better than it
    is."""
    a, b = [4, 5, 6], [5, 6, 4]
    inferred = quadratic_weighted_kappa(a, b)
    declared = quadratic_weighted_kappa(a, b, min_rating=0, max_rating=10)
    assert declared != inferred


def test_mismatched_lengths_are_refused() -> None:
    with pytest.raises(ValueError, match="same length"):
        quadratic_weighted_kappa([1, 2, 3], [1, 2])


def test_an_empty_set_is_refused() -> None:
    """Reporting agreement over no data would be a number with nothing behind
    it."""
    with pytest.raises(ValueError, match="empty"):
        quadratic_weighted_kappa([], [])


def test_half_marks_are_supported() -> None:
    """Rubrics award half marks, so the scale cannot assume integers."""
    a = [0.0, 0.5, 1.0, 1.5, 2.0]
    assert quadratic_weighted_kappa(a, a, step=0.5) == pytest.approx(1.0)


# --- overall confidence ----------------------------------------------------


def test_overall_confidence_is_the_minimum_not_the_mean() -> None:
    """spec.md §8.1. A mean lets a perfect photograph hide an unreadable
    answer; a pipeline is only as good as its weakest stage."""
    assert overall_confidence(0.99, 0.99, 0.30, 0.99) == pytest.approx(0.30)


def test_overall_confidence_needs_something_to_combine() -> None:
    with pytest.raises(ValueError, match="at least one"):
        overall_confidence()
