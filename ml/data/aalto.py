"""
Aalto 136M Keystroke Dataset parser.

Yields RawSession objects from the per-participant file format. All
Aalto-specific field names are confined to this module; nothing downstream
sees them.

Actual on-disk format (tab-separated, one file per participant):
  Keystrokes/files/{PARTICIPANT_ID}_keystrokes.txt

Columns (confirmed from real data):
  PARTICIPANT_ID  — integer participant identifier
  TEST_SECTION_ID — integer session identifier (one per sentence, ~15 per participant)
  SENTENCE        — the target sentence shown to the participant
  USER_INPUT      — what the participant actually typed
  KEYSTROKE_ID    — unique keystroke identifier
  PRESS_TIME      — keydown timestamp in milliseconds from epoch
  RELEASE_TIME    — keyup timestamp in milliseconds from epoch
  LETTER          — the key typed: lowercase letter, uppercase when shifted,
                    or a special-key name (SHIFT, BKSP, ALT, CTRL, etc.)
  KEYCODE         — numeric keycode (unused — LETTER is sufficient)

One row = one keystroke. Rows within a file are ordered by PRESS_TIME.

Usage:
    from ml.data.aalto import AaltoSessions
    for session in AaltoSessions("Keystrokes/files"):
        features = compute_features(session.events)
"""

import csv
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from .protocol import RawSession
from features import KeystrokeEvent


_COL_PARTICIPANT = "PARTICIPANT_ID"
_COL_SESSION     = "TEST_SECTION_ID"
_COL_PRESS       = "PRESS_TIME"
_COL_RELEASE     = "RELEASE_TIME"
_COL_LETTER      = "LETTER"

# Special key names found in the actual Aalto files that don't lowercase
# cleanly to our labeler's expected names.
_LETTER_MAP: dict[str, str] = {
    "BKSP":      "backspace",
    "ARW_LEFT":  "arrowleft",
    "ARW_RIGHT": "arrowright",
    "ARW_UP":    "arrowup",
    "ARW_DOWN":  "arrowdown",
    "CAPS_LOCK": "capslock",
    "NUM_LK":    "numlock",
}


def _normalize_letter(letter: str) -> str:
    """Normalize an Aalto LETTER value to a canonical key label.

    Single characters (letters, digits, punctuation) are lowercased.
    Multi-character special key names are mapped via _LETTER_MAP, or
    lowercased directly if not in the map (SHIFT→shift, CTRL→ctrl, etc.).
    """
    if letter in _LETTER_MAP:
        return _LETTER_MAP[letter]
    return letter.lower()


@dataclass
class _SessionBuffer:
    participant_id: str
    session_id: str
    events: list[KeystrokeEvent] = field(default_factory=list)

    def to_raw_session(self) -> RawSession:
        return RawSession(
            participant_id=self.participant_id,
            session_context="prose",
            events=sorted(self.events, key=lambda e: e.keydown_ms),
        )


class AaltoSessions:
    """Streaming iterator over the Aalto 136M dataset (per-participant files).

    Iterates over every {PARTICIPANT_ID}_keystrokes.txt file in the given
    directory, yielding one RawSession per TEST_SECTION_ID. Sessions with
    fewer than min_keystrokes events are silently skipped.

    Args:
        directory:      Path to the directory containing the .txt files
                        (e.g. "Keystrokes/files").
        min_keystrokes: Minimum keystroke count per session after filtering.
        encoding:       File encoding; Aalto uses UTF-8.
    """

    def __init__(
        self,
        directory: str | os.PathLike,
        min_keystrokes: int = 20,
        encoding: str = "utf-8",
    ) -> None:
        self._dir = Path(directory)
        self._min_keystrokes = min_keystrokes
        self._encoding = encoding

    def _files(self) -> list[Path]:
        return sorted(self._dir.glob("*_keystrokes.txt"))

    def __iter__(self) -> Iterator[RawSession]:
        for filepath in self._files():
            pid = filepath.stem.replace("_keystrokes", "")
            all_events: list[KeystrokeEvent] = []

            csv.field_size_limit(min(sys.maxsize, 10_000_000))
            with filepath.open(encoding=self._encoding, errors="replace", newline="") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                for row in reader:
                    try:
                        press   = float(row[_COL_PRESS])
                        release = float(row[_COL_RELEASE])
                    except (ValueError, KeyError, TypeError):
                        continue
                    if release < press:
                        continue
                    key = _normalize_letter(row[_COL_LETTER])
                    all_events.append(
                        KeystrokeEvent(key=key, keydown_ms=press, keyup_ms=release)
                    )

            if len(all_events) < self._min_keystrokes:
                continue

            yield RawSession(
                participant_id=pid,
                session_context="prose",
                events=sorted(all_events, key=lambda e: e.keydown_ms),
            )

    def __len__(self) -> int:
        """Number of participant files (fast proxy for session count)."""
        return len(self._files())
