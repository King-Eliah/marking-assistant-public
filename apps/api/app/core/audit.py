"""Audit chain construction and verification.

Each row hashes the previous row's hash together with its own content, so any
retroactive tampering breaks the chain from that point forward. For an
examinations system this converts "we log things" into "we can prove the log
was not altered" — see docs/spec.md §5.4.

The hash covers the fields that carry meaning. It deliberately excludes the
surrogate `id`, so a chain remains verifiable if rows are ever copied into a
fresh table during a restore drill.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Final

#: The hash of the row before the first one. A chain always has an anchor, so
#: "is this the first row?" never becomes a special case at verification time.
GENESIS_HASH: Final[str] = "0" * 64

#: Fields covered by `row_hash`, in a fixed order.
HASHED_FIELDS: Final[tuple[str, ...]] = (
    "tenant_id",
    "actor_id",
    "action",
    "entity_type",
    "entity_id",
    "before",
    "after",
    "reason",
    "at",
)


def _canonical(value: Any) -> Any:
    """Reduce a value to something JSON can serialise deterministically."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        # isoformat alone is ambiguous across offsets; normalise to UTC.
        return value.astimezone(tz=None).isoformat() if value.tzinfo else value.isoformat()
    return value


def canonical_payload(fields: dict[str, Any]) -> str:
    """Serialise the hashed fields deterministically.

    `sort_keys` and a fixed separator matter more than they look: a different
    key order or a stray space produces a different hash and a false tamper
    alarm.
    """
    payload = {name: _canonical(fields.get(name)) for name in HASHED_FIELDS}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_row_hash(prev_hash: str, fields: dict[str, Any]) -> str:
    """sha256(prev_hash ‖ canonical(row))."""
    digest = hashlib.sha256()
    digest.update(prev_hash.encode("utf-8"))
    digest.update(b"\x1f")  # unit separator, so concatenation is unambiguous
    digest.update(canonical_payload(fields).encode("utf-8"))
    return digest.hexdigest()


class ChainBrokenError(Exception):
    """Raised when verification finds a row whose hash does not match.

    This is an incident, not a warning. It means either the log was altered or
    a row was written outside `append()`.
    """

    def __init__(self, position: int, expected: str, found: str) -> None:
        self.position = position
        self.expected = expected
        self.found = found
        super().__init__(
            f"audit chain broken at position {position}: "
            f"expected {expected[:12]}…, found {found[:12]}…"
        )


def verify_chain(rows: list[dict[str, Any]]) -> None:
    """Walk a chain in order and raise on the first inconsistency.

    Checks both that each `row_hash` matches its content and that each
    `prev_hash` matches the preceding row — either alone is insufficient.
    Deleting a row breaks the second check; editing one breaks the first.
    """
    expected_prev = GENESIS_HASH
    for position, row in enumerate(rows):
        if row["prev_hash"] != expected_prev:
            raise ChainBrokenError(position, expected_prev, row["prev_hash"])

        recomputed = compute_row_hash(row["prev_hash"], row)
        if recomputed != row["row_hash"]:
            raise ChainBrokenError(position, recomputed, row["row_hash"])

        expected_prev = row["row_hash"]
