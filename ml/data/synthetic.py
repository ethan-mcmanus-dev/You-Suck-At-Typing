"""
Synthetic session generator for testing the ML pipeline without real data.

Generates plausible but fake keystroke sequences with controllable
biomechanical profiles, so clustering and insight code can be validated
before the Aalto dataset arrives.
"""

import random
from .protocol import RawSession
from features import KeystrokeEvent
from labeler.maps import FINGER_MAP

# Keys that appear in normal prose typing (excludes modifiers, numbers, symbols)
_PROSE_KEYS = [k for k in FINGER_MAP if k.isalpha() and len(k) == 1]


def _make_session(
    participant_id: str,
    n_keystrokes: int = 200,
    base_dwell_ms: float = 80.0,
    base_flight_ms: float = 100.0,
    sfb_penalty_ms: float = 40.0,
    rollover_fraction: float = 0.0,
    seed: int | None = None,
) -> RawSession:
    """Generate a single synthetic session.

    sfb_penalty_ms: added to flight time after a same-finger bigram.
    rollover_fraction: fraction of bigrams where the next keydown overlaps
    the current keyup (negative flight time). 0.0 = no rollover.
    """
    rng = random.Random(seed)
    events: list[KeystrokeEvent] = []
    t = 0.0

    keys = rng.choices(_PROSE_KEYS, k=n_keystrokes)

    for i, key in enumerate(keys):
        dwell = max(10.0, rng.gauss(base_dwell_ms, 15.0))
        keydown = t
        keyup = keydown + dwell

        # Flight time to next key depends on bigram class
        if i > 0:
            prev = keys[i - 1]
            from labeler import label_bigram
            cls = label_bigram(prev, key)
            if cls == "sfb":
                flight = rng.gauss(base_flight_ms + sfb_penalty_ms, 20.0)
            else:
                flight = rng.gauss(base_flight_ms, 20.0)

            # Rollover: next keydown starts before previous keyup
            if rng.random() < rollover_fraction:
                prev_event = events[-1]
                t = prev_event.keyup_ms - rng.uniform(1.0, 5.0)
            else:
                t = events[-1].keyup_ms + max(0.0, flight)
        else:
            t = keyup + rng.gauss(base_flight_ms, 20.0)

        events.append(KeystrokeEvent(key=key, keydown_ms=keydown, keyup_ms=keyup))

    return RawSession(
        participant_id=participant_id,
        session_context="prose",
        events=events,
    )


def make_synthetic_sessions(
    n: int = 100,
    seed: int = 42,
) -> list[RawSession]:
    """Return n synthetic sessions with varied biomechanical profiles.

    Produces three rough archetypes to give clustering something to find:
    - ~33%: high SFB rate (slow typists who don't roll)
    - ~33%: moderate SFB, some rollover (average typists)
    - ~33%: low SFB, high rollover (fast touch typists)
    """
    rng = random.Random(seed)
    sessions = []

    for i in range(n):
        archetype = i % 3
        pid = f"synthetic_{i:04d}"

        if archetype == 0:
            s = _make_session(pid, base_flight_ms=130.0, sfb_penalty_ms=60.0,
                              rollover_fraction=0.0, seed=rng.randint(0, 9999))
        elif archetype == 1:
            s = _make_session(pid, base_flight_ms=100.0, sfb_penalty_ms=35.0,
                              rollover_fraction=0.05, seed=rng.randint(0, 9999))
        else:
            s = _make_session(pid, base_flight_ms=70.0, sfb_penalty_ms=20.0,
                              rollover_fraction=0.15, seed=rng.randint(0, 9999))

        sessions.append(s)

    return sessions
