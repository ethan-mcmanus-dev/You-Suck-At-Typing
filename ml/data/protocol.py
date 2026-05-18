"""
Generic session data protocol.

Any data source (Aalto CSV, live backend sessions, synthetic test data)
must produce RawSession objects. The clustering and feature code
depends only on this interface, never on source-specific field names.
"""

from dataclasses import dataclass
from typing import Iterator, Protocol
from features import KeystrokeEvent


@dataclass
class RawSession:
    participant_id: str
    session_context: str          # "prose", "code", etc.
    events: list[KeystrokeEvent]  # pre-filtered, ordered by keydown_ms


class SessionIterator(Protocol):
    """Any data source that yields RawSession objects one at a time."""

    def __iter__(self) -> Iterator[RawSession]: ...
    def __len__(self) -> int: ...
