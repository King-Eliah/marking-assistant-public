"""The audit chain's whole value is that tampering is detectable.

These tests are the proof of that claim, so they test the tampering cases, not
just the happy path. A chain that verifies only well-formed input proves
nothing.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.core.audit import (
    GENESIS_HASH,
    ChainBrokenError,
    canonical_payload,
    compute_row_hash,
    verify_chain,
)

TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
ACTOR = uuid.UUID("22222222-2222-2222-2222-222222222222")


def make_row(prev_hash: str, action: str, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "tenant_id": TENANT,
        "actor_id": ACTOR,
        "action": action,
        "entity_type": "course",
        "entity_id": "c-1",
        "before": None,
        "after": {"code": "CSM355"},
        "reason": None,
        "at": datetime(2026, 7, 29, 9, 41, 2, tzinfo=UTC),
    }
    row.update(overrides)
    row["prev_hash"] = prev_hash
    row["row_hash"] = compute_row_hash(prev_hash, row)
    return row


def make_chain(length: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    prev = GENESIS_HASH
    for i in range(length):
        row = make_row(prev, f"action.{i}")
        rows.append(row)
        prev = row["row_hash"]
    return rows


def test_a_valid_chain_verifies() -> None:
    verify_chain(make_chain(5))


def test_an_empty_chain_verifies() -> None:
    """No rows is a valid state, not an error."""
    verify_chain([])


def test_hashing_is_deterministic() -> None:
    """I5 in miniature: the same content must always hash the same."""
    a = make_row(GENESIS_HASH, "marks.finalise")
    b = make_row(GENESIS_HASH, "marks.finalise")
    assert a["row_hash"] == b["row_hash"]


def test_key_order_does_not_change_the_hash() -> None:
    """Otherwise a dict built in a different order raises a false alarm."""
    fields = {
        "action": "x",
        "tenant_id": TENANT,
        "at": datetime(2026, 7, 29, tzinfo=UTC),
    }
    reordered = {
        "at": datetime(2026, 7, 29, tzinfo=UTC),
        "tenant_id": TENANT,
        "action": "x",
    }
    assert canonical_payload(fields) == canonical_payload(reordered)


def test_editing_a_row_breaks_the_chain() -> None:
    """The case the whole mechanism exists for."""
    rows = make_chain(5)
    rows[2]["after"] = {"code": "TAMPERED"}

    with pytest.raises(ChainBrokenError) as caught:
        verify_chain(rows)
    assert caught.value.position == 2


def test_editing_the_reason_breaks_the_chain() -> None:
    """A marker's stated reason is evidence; it must be covered too."""
    rows = make_chain(3)
    rows[1]["reason"] = "something else entirely"

    with pytest.raises(ChainBrokenError):
        verify_chain(rows)


def test_deleting_a_row_breaks_the_chain() -> None:
    """Editing breaks row_hash; deletion breaks prev_hash. Both must be caught."""
    rows = make_chain(5)
    del rows[2]

    with pytest.raises(ChainBrokenError) as caught:
        verify_chain(rows)
    assert caught.value.position == 2


def test_reordering_rows_breaks_the_chain() -> None:
    rows = make_chain(4)
    rows[1], rows[2] = rows[2], rows[1]

    with pytest.raises(ChainBrokenError):
        verify_chain(rows)


def test_appending_a_forged_row_breaks_the_chain() -> None:
    """A row written outside append() has no valid predecessor hash."""
    rows = make_chain(3)
    forged = make_row(GENESIS_HASH, "marks.finalise")  # wrong prev_hash
    rows.append(forged)

    with pytest.raises(ChainBrokenError) as caught:
        verify_chain(rows)
    assert caught.value.position == 3


def test_recomputing_a_tampered_row_does_not_repair_it() -> None:
    """An attacker who edits content and rehashes that one row still breaks the
    chain, because the following row's prev_hash no longer matches."""
    rows = make_chain(4)
    rows[1]["after"] = {"code": "TAMPERED"}
    rows[1]["row_hash"] = compute_row_hash(rows[1]["prev_hash"], rows[1])

    with pytest.raises(ChainBrokenError) as caught:
        verify_chain(rows)
    assert caught.value.position == 2


def test_the_first_row_anchors_to_genesis() -> None:
    rows = make_chain(2)
    assert rows[0]["prev_hash"] == GENESIS_HASH

    rows[0]["prev_hash"] = "f" * 64
    with pytest.raises(ChainBrokenError) as caught:
        verify_chain(rows)
    assert caught.value.position == 0
