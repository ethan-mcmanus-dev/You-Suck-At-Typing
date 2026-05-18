"""
Aggregates a sequence of keystroke events into the 7-feature vector used
for clustering and insight generation.

Intentionally generic: no dataset-specific field names. Callers are
responsible for mapping their data source (Aalto, live session, etc.)
into a list of KeystrokeEvent before calling compute_features.
"""

from dataclasses import dataclass
from typing import Sequence
from collections import defaultdict
import statistics

from labeler import label_bigram, label_redirect, EXCLUDED_KEYS


@dataclass
class KeystrokeEvent:
    key: str
    keydown_ms: float
    keyup_ms: float


@dataclass
class FeatureVector:
    """
    7-feature biomechanical profile for a single typing session.

    Each field is a mean flight time (ms) for bigrams of that class,
    except mean_dwell_sfb which is mean dwell time (ms) for SFB keys.

    None means no bigrams of that class were observed in the session.
    redirect_rate is a fraction (0.0–1.0) of trigrams that are redirects.
    """
    mean_dwell_sfb: float | None
    mean_flight_sfb: float | None
    mean_flight_roll_in: float | None
    mean_flight_roll_out: float | None
    mean_flight_alternation: float | None
    mean_flight_scissor: float | None
    mean_flight_lateral: float | None
    redirect_rate: float | None
    # Rollover: fraction of bigrams where keydown_next < keyup_current.
    # May be unreliable in browser environments at <5ms resolution.
    rollover_rate: float | None
    n_keystrokes: int
    n_bigrams_labeled: int


_MIN_KEYSTROKES = 100
_DWELL_CAP_MS = 500.0
# Flight times above this are thinking pauses or inter-sentence gaps, not
# biomechanical transitions. 1000ms cleanly separates normal typing (< 500ms)
# from Aalto inter-sentence gaps (1800ms+) and user pause events.
_FLIGHT_CAP_MS = 1000.0


def compute_features(events: Sequence[KeystrokeEvent]) -> FeatureVector:
    """Compute the 7-feature vector from a sequence of KeystrokeEvent.

    Raises ValueError if fewer than _MIN_KEYSTROKES events are provided.

    Filtering applied before aggregation:
    - Keys in EXCLUDED_KEYS are dropped (modifiers, backspace, space, etc.)
    - Dwell times > _DWELL_CAP_MS are capped (held-key artifacts)
    - Events where keyup_ms < keydown_ms are dropped (malformed timing)
    """
    filtered = [
        e for e in events
        if e.key.lower() not in EXCLUDED_KEYS
        and e.keyup_ms >= e.keydown_ms
    ]

    if len(filtered) < _MIN_KEYSTROKES:
        raise ValueError(
            f"Session has {len(filtered)} valid keystrokes "
            f"(minimum {_MIN_KEYSTROKES} required for feature computation)."
        )

    # Cap dwell times
    capped = [
        KeystrokeEvent(
            key=e.key,
            keydown_ms=e.keydown_ms,
            keyup_ms=min(e.keyup_ms, e.keydown_ms + _DWELL_CAP_MS),
        )
        for e in filtered
    ]

    flight_by_class: dict[str, list[float]] = defaultdict(list)
    dwell_sfb: list[float] = []
    rollover_count = 0
    total_bigrams = 0
    labeled_bigrams = 0

    redirect_count = 0
    total_trigrams = 0

    for i in range(len(capped) - 1):
        curr = capped[i]
        nxt = capped[i + 1]

        cls = label_bigram(curr.key, nxt.key)
        total_bigrams += 1

        if cls == "unknown":
            continue

        flight_ms = nxt.keydown_ms - curr.keyup_ms
        if flight_ms > _FLIGHT_CAP_MS:
            continue

        labeled_bigrams += 1
        flight_by_class[cls].append(flight_ms)

        if cls == "sfb":
            dwell = curr.keyup_ms - curr.keydown_ms
            dwell_sfb.append(dwell)

        if nxt.keydown_ms < curr.keyup_ms:
            rollover_count += 1

    # Redirect rate over trigrams
    for i in range(len(capped) - 2):
        total_trigrams += 1
        if label_redirect(capped[i].key, capped[i + 1].key, capped[i + 2].key):
            redirect_count += 1

    def _mean(values: list[float]) -> float | None:
        return statistics.mean(values) if values else None

    return FeatureVector(
        mean_dwell_sfb=_mean(dwell_sfb),
        mean_flight_sfb=_mean(flight_by_class["sfb"]),
        mean_flight_roll_in=_mean(flight_by_class["roll_in"]),
        mean_flight_roll_out=_mean(flight_by_class["roll_out"]),
        mean_flight_alternation=_mean(flight_by_class["alternation"]),
        mean_flight_scissor=_mean(flight_by_class["scissor"]),
        mean_flight_lateral=_mean(flight_by_class["lateral"]),
        redirect_rate=redirect_count / total_trigrams if total_trigrams > 0 else None,
        rollover_rate=rollover_count / labeled_bigrams if labeled_bigrams > 0 else None,
        n_keystrokes=len(filtered),
        n_bigrams_labeled=labeled_bigrams,
    )
