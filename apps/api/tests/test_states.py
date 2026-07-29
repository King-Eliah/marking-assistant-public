"""The state machine is the spine of the pipeline, so it is tested exhaustively.

Every illegal edge is tested, not just the legal ones — a machine that permits
an undeclared move is the same bug as one that forbids a declared move.
"""

from itertools import pairwise

import pytest

from app.core.states import (
    ALLOWED,
    HUMAN_STATES,
    MACHINE_STATES,
    TERMINAL_STATES,
    IllegalTransitionError,
    State,
    can_fail,
    is_terminal,
    transition,
)


def test_every_state_has_a_row() -> None:
    """A state absent from ALLOWED strands anything that reaches it.

    This is the defect that shipped in spec.md v1.0: QUALITY_REJECTED and FAILED
    had no keys, so a rejected script had no legal move out.
    """
    assert set(ALLOWED) == set(State)


def test_every_target_is_a_known_state() -> None:
    for source, targets in ALLOWED.items():
        for target in targets:
            assert target in State, f"{source} -> {target} is not a State"


@pytest.mark.parametrize(
    ("source", "target"),
    sorted((s, t) for s, ts in ALLOWED.items() for t in ts),
)
def test_declared_transitions_are_permitted(source: State, target: State) -> None:
    assert transition(source, target) == target


@pytest.mark.parametrize(
    ("source", "target"),
    sorted((s, t) for s in State for t in State if t not in ALLOWED[s]),
)
def test_undeclared_transitions_raise(source: State, target: State) -> None:
    with pytest.raises(IllegalTransitionError):
        transition(source, target)


def test_illegal_transition_names_the_legal_moves() -> None:
    """The error has to be actionable — a bare 'illegal transition' is not."""
    with pytest.raises(IllegalTransitionError, match="PREPROCESSING"):
        transition(State.RECEIVED, State.SCORING)


def test_quality_rejected_can_retake() -> None:
    """The v1.0 diagram promised a retake arrow the table could not implement."""
    assert transition(State.QUALITY_REJECTED, State.PREPROCESSING) == State.PREPROCESSING


def test_terminal_states_have_no_exit() -> None:
    for state in TERMINAL_STATES:
        assert ALLOWED[state] == frozenset()
        assert is_terminal(state)


def test_finalised_is_terminal() -> None:
    """I4: corrections create a new attempt, they never reopen a finalised one."""
    for target in State:
        with pytest.raises(IllegalTransitionError):
            transition(State.FINALISED, target)


def test_only_machine_states_can_fail() -> None:
    """FAILED means a worker exhausted its retries; human states have no worker."""
    for state in MACHINE_STATES:
        assert State.FAILED in ALLOWED[state]
        assert can_fail(state)
    for state in HUMAN_STATES:
        assert State.FAILED not in ALLOWED[state]
        assert not can_fail(state)


def test_machine_and_human_states_are_disjoint_and_total() -> None:
    assert MACHINE_STATES.isdisjoint(HUMAN_STATES)
    assert MACHINE_STATES | HUMAN_STATES | TERMINAL_STATES | {State.QUALITY_REJECTED} == set(State)


def test_every_state_is_reachable_from_received() -> None:
    """An unreachable state is dead code that will rot."""
    seen = {State.RECEIVED}
    frontier = [State.RECEIVED]
    while frontier:
        for target in ALLOWED[frontier.pop()]:
            if target not in seen:
                seen.add(target)
                frontier.append(target)
    assert seen == set(State)


def test_finalised_is_reachable_without_a_failure() -> None:
    """The happy path must exist end to end."""
    path = [
        State.RECEIVED,
        State.PREPROCESSING,
        State.OCR_RUNNING,
        State.OCR_AGREED,
        State.SEGMENTING,
        State.UNDERSTANDING,
        State.SCORING,
        State.AWAITING_REVIEW,
        State.REVIEWED,
        State.FINALISED,
    ]
    for source, target in pairwise(path):
        assert transition(source, target) == target
