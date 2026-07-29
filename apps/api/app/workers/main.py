"""Dramatiq worker entrypoint.

One queue per pipeline stage, never one shared queue — the stages have different
concurrency and failure characteristics. See docs/spec.md §2.3 and
.claude/rules/api.md.

Scaffold only: the broker is wired and the queues are declared, but no actor does
real work yet.
"""

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.core.config import get_settings

QUEUES = (
    "q.preprocess",  # CPU-bound, workers = cores
    "q.ocr",  # I/O-bound, high concurrency
    "q.understand",  # CPU/GPU-bound
    "q.score",  # trivial, pure function
    "q.export",  # low priority, long running
    "q.dlq",  # manual drain
)

broker = RedisBroker(url=get_settings().redis_url)  # type: ignore[no-untyped-call]
dramatiq.set_broker(broker)


@dramatiq.actor(queue_name="q.score", max_retries=0)
def ping() -> str:
    """Placeholder actor proving the broker round-trips. Delete at stage 1."""
    return "pong"
