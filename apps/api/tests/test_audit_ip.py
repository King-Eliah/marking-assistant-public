"""The audit write must never be the thing that fails.

`audit_log.ip` is INET, so Postgres rejects a malformed value with a DataError
that aborts the whole append. Since the address can arrive from a proxy header
in production, a caller could otherwise suppress a security event simply by
sending a value that will not parse.
"""

from __future__ import annotations

from app.core.audit_writer import _safe_ip


def test_valid_addresses_survive() -> None:
    assert _safe_ip("192.0.2.1") == "192.0.2.1"
    assert _safe_ip("::1") == "::1"
    assert _safe_ip("2001:db8::8a2e:370:7334") == "2001:db8::8a2e:370:7334"


def test_none_stays_none() -> None:
    assert _safe_ip(None) is None


def test_unparseable_values_become_none_rather_than_raising() -> None:
    """Losing one optional field beats losing the audit row."""
    for junk in ("testclient", "", "localhost", "999.999.999.999", "1.2.3.4, 5.6.7.8"):
        assert _safe_ip(junk) is None


def test_an_injection_attempt_is_discarded_not_executed() -> None:
    assert _safe_ip("127.0.0.1'; DROP TABLE audit_log; --") is None
