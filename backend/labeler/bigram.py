from .maps import FINGER_MAP, ROW_MAP, HAND_MAP, EXCLUDED_KEYS, LP, LR, LM, LI, RI, RM, RR, RP

# Valid class labels returned by label_bigram and label_redirect.
BIGRAM_CLASSES = frozenset({
    "sfb", "scissor", "roll_in", "roll_out",
    "alternation", "lateral", "unknown",
})
REDIRECT = "redirect"


def label_bigram(key_a: str, key_b: str, layout: str = "qwerty") -> str:
    """Classify a keystroke bigram by its biomechanical cost class.

    Returns one of: "sfb", "scissor", "roll_in", "roll_out",
                    "alternation", "lateral", "unknown".

    "unknown" is returned when either key is a modifier, space, or
    otherwise absent from the finger map. Callers may pre-filter using
    EXCLUDED_KEYS but label_bigram is safe to call on any input.

    layout must be "qwerty" for now. Other layouts raise ValueError.
    """
    if layout != "qwerty":
        raise ValueError(f"Unsupported layout: {layout!r}. Only 'qwerty' is supported.")

    a = key_a.lower()
    b = key_b.lower()

    if a in EXCLUDED_KEYS or b in EXCLUDED_KEYS:
        return "unknown"

    finger_a = FINGER_MAP.get(a)
    finger_b = FINGER_MAP.get(b)

    if finger_a is None or finger_b is None:
        return "unknown"

    # SFB: same finger (includes same key repeated)
    if finger_a == finger_b:
        return "sfb"

    hand_a = HAND_MAP[finger_a]
    hand_b = HAND_MAP[finger_b]

    # Alternation: different hands
    if hand_a != hand_b:
        return "alternation"

    # Same hand from here — determine row positions
    row_a = ROW_MAP.get(a)
    row_b = ROW_MAP.get(b)

    if row_a is None or row_b is None:
        return "unknown"

    row_delta = abs(row_a - row_b)

    # Scissor: same hand, non-adjacent rows (skips at least one row).
    # The fingers must cross over each other — a top-row key and a
    # bottom-row key on the same hand with a gap in between.
    if row_delta >= 2:
        return "scissor"

    # Lateral stretch: pinky involved and keys are on different rows.
    # The pinky has the least dexterity and row-crossing stretches cost more.
    if (finger_a in (LP, RP) or finger_b in (LP, RP)) and row_delta >= 1:
        return "lateral"

    # Roll: same hand, adjacent rows, not an SFB, scissor, or lateral.
    # Inward = movement toward the index finger (the strong, dexterous finger).
    # Outward = movement away from the index finger.
    #
    # Left hand: fingers are LP(0)…LI(3). Inward means finger index increases.
    # Right hand: fingers are RI(6)…RP(9). Inward means finger index decreases.
    if hand_a == "L":
        roll_in = finger_a < finger_b
    else:
        roll_in = finger_a > finger_b

    return "roll_in" if roll_in else "roll_out"


def label_redirect(key_a: str, key_b: str, key_c: str, layout: str = "qwerty") -> bool:
    """Return True if the trigram (key_a, key_b, key_c) is a redirect.

    A redirect is a same-hand trigram where the roll direction reverses:
    the hand moves inward then outward (or outward then inward) within
    three consecutive keystrokes. This is costly because the hand must
    change direction mid-motion.

    Returns False if any key is unknown, if any pair is an SFB, or if
    the trigram is not entirely on one hand.
    """
    if layout != "qwerty":
        raise ValueError(f"Unsupported layout: {layout!r}. Only 'qwerty' is supported.")

    a, b, c = key_a.lower(), key_b.lower(), key_c.lower()

    for k in (a, b, c):
        if k in EXCLUDED_KEYS:
            return False

    fa = FINGER_MAP.get(a)
    fb = FINGER_MAP.get(b)
    fc = FINGER_MAP.get(c)

    if fa is None or fb is None or fc is None:
        return False

    # Must all be on the same hand
    if len({HAND_MAP[fa], HAND_MAP[fb], HAND_MAP[fc]}) != 1:
        return False

    # Any SFB in the sequence disqualifies it as a redirect
    if fa == fb or fb == fc:
        return False

    hand = HAND_MAP[fa]

    # Determine direction of each bigram
    # For left hand: inward = finger index increases (LP=0 → LI=3)
    # For right hand: inward = finger index decreases (RP=9 → RI=6)
    def _is_inward(f1: int, f2: int) -> bool:
        if hand == "L":
            return f1 < f2
        return f1 > f2

    ab_inward = _is_inward(fa, fb)
    bc_inward = _is_inward(fb, fc)

    # Redirect = direction changes between the two bigrams
    return ab_inward != bc_inward
