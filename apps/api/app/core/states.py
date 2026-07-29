"""The pipeline state machine.

Every script and page stores its state. State is never inferred — see
docs/spec.md §4 and .claude/rules/api.md.

All transitions go through `transition()` and nowhere else. An illegal move
raises; it is never a silent no-op, because a silent no-op would let a script
sit in a state its owner believes it has left.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class State(StrEnum):
    """Pipeline states. The string values are what land in the database."""

    RECEIVED = "RECEIVED"
    PREPROCESSING = "PREPROCESSING"
    QUALITY_REJECTED = "QUALITY_REJECTED"
    OCR_RUNNING = "OCR_RUNNING"
    OCR_AGREED = "OCR_AGREED"
    OCR_ARBITRATING = "OCR_ARBITRATING"
    SEGMENTING = "SEGMENTING"
    NEEDS_TRANSCRIPTION = "NEEDS_TRANSCRIPTION"
    UNDERSTANDING = "UNDERSTANDING"
    SCORING = "SCORING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    MANUAL_ONLY = "MANUAL_ONLY"
    REVIEWED = "REVIEWED"
    MODERATION = "MODERATION"
    FINALISED = "FINALISED"
    FAILED = "FAILED"


#: States a worker owns. Only these can reach FAILED, because FAILED means a
#: worker exhausted its retries and the human states have no worker to exhaust.
MACHINE_STATES: Final[frozenset[State]] = frozenset(
    {
        State.RECEIVED,
        State.PREPROCESSING,
        State.OCR_RUNNING,
        State.OCR_ARBITRATING,
        State.OCR_AGREED,
        State.SEGMENTING,
        State.UNDERSTANDING,
        State.SCORING,
    }
)

#: States a human owns. Left only by a human action (I1).
HUMAN_STATES: Final[frozenset[State]] = frozenset(
    {
        State.NEEDS_TRANSCRIPTION,
        State.AWAITING_REVIEW,
        State.MANUAL_ONLY,
        State.REVIEWED,
        State.MODERATION,
    }
)

#: Terminal for the current attempt. A correction or a triage creates a new
#: attempt rather than reviving a dead one, which is what keeps the append-only
#: guarantee (I4) and the (script_id, stage, pipeline_version) idempotency key
#: intact.
TERMINAL_STATES: Final[frozenset[State]] = frozenset({State.FINALISED, State.FAILED})

ALLOWED: Final[dict[State, frozenset[State]]] = {
    State.RECEIVED: frozenset({State.PREPROCESSING, State.FAILED}),
    State.PREPROCESSING: frozenset({State.OCR_RUNNING, State.QUALITY_REJECTED, State.FAILED}),
    # a retake supplies a new image for the same page slot, so it re-enters preprocessing
    State.QUALITY_REJECTED: frozenset({State.PREPROCESSING, State.FAILED}),
    State.OCR_RUNNING: frozenset({State.OCR_AGREED, State.OCR_ARBITRATING, State.FAILED}),
    State.OCR_ARBITRATING: frozenset({State.OCR_AGREED, State.NEEDS_TRANSCRIPTION, State.FAILED}),
    State.OCR_AGREED: frozenset({State.SEGMENTING, State.FAILED}),
    State.SEGMENTING: frozenset({State.UNDERSTANDING, State.NEEDS_TRANSCRIPTION, State.FAILED}),
    State.NEEDS_TRANSCRIPTION: frozenset({State.UNDERSTANDING, State.MANUAL_ONLY}),
    State.UNDERSTANDING: frozenset({State.SCORING, State.MANUAL_ONLY, State.FAILED}),
    State.SCORING: frozenset({State.AWAITING_REVIEW, State.MANUAL_ONLY, State.FAILED}),
    State.AWAITING_REVIEW: frozenset({State.REVIEWED}),
    State.MANUAL_ONLY: frozenset({State.REVIEWED}),
    State.REVIEWED: frozenset({State.MODERATION, State.FINALISED}),
    State.MODERATION: frozenset({State.FINALISED, State.AWAITING_REVIEW}),
    State.FINALISED: frozenset(),
    State.FAILED: frozenset(),
}


class IllegalTransitionError(ValueError):
    """Raised when a move is not in `ALLOWED`."""

    def __init__(self, source: State, target: State) -> None:
        self.source = source
        self.target = target
        legal = sorted(s.value for s in ALLOWED[source])
        allowed = ", ".join(legal) if legal else "none — terminal"
        super().__init__(f"{source.value} -> {target.value} is not permitted. Allowed: {allowed}")


def transition(source: State, target: State) -> State:
    """Return `target` if the move is legal, otherwise raise.

    The single place a pipeline state changes. Callers persist the return value;
    they must not compute the next state themselves.
    """
    if target not in ALLOWED[source]:
        raise IllegalTransitionError(source, target)
    return target


def is_terminal(state: State) -> bool:
    """True when no further move exists for this attempt."""
    return state in TERMINAL_STATES


def can_fail(state: State) -> bool:
    """True when retry exhaustion may send this state to FAILED."""
    return state in MACHINE_STATES
