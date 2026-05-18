import pytest
from labeler import label_bigram, label_redirect


# ---------------------------------------------------------------------------
# SFB — same finger, different (or same) key
# ---------------------------------------------------------------------------

class TestSFB:
    def test_left_middle_to_left_ring(self):
        # d=LM, s=LR — wait, these are different fingers. d(LM) and e(LM) are same.
        # d=LM, e=LM
        assert label_bigram("d", "e") == "sfb"

    def test_right_index_pair(self):
        # j=RI, u=RI
        assert label_bigram("j", "u") == "sfb"

    def test_same_key_repeated(self):
        assert label_bigram("a", "a") == "sfb"

    def test_left_index_covers_t_and_r(self):
        # r=LI, t=LI — canonical left index assignment
        assert label_bigram("r", "t") == "sfb"

    def test_right_index_covers_y_and_u(self):
        # y=RI, u=RI
        assert label_bigram("y", "u") == "sfb"

    def test_sfb_reversed(self):
        # Order should not affect SFB classification
        assert label_bigram("t", "r") == "sfb"

    def test_number_row_same_finger(self):
        # 4=LI, 5=LI
        assert label_bigram("4", "5") == "sfb"

    def test_pinky_number_and_letter(self):
        # 1=LP, q=LP
        assert label_bigram("1", "q") == "sfb"

    def test_right_pinky_home_and_top(self):
        # ;=RP, p=RP
        assert label_bigram(";", "p") == "sfb"

    def test_g_and_b_same_finger(self):
        # g=LI, b=LI
        assert label_bigram("g", "b") == "sfb"


# ---------------------------------------------------------------------------
# Scissor — same hand, row gap ≥ 2
# ---------------------------------------------------------------------------

class TestScissor:
    def test_top_to_bottom_left(self):
        # q=LP row1, z=LP row3 — but same finger → sfb, not scissor
        # Use different fingers: w=LR row1, x=LR row3 — same finger again
        # Need different fingers: e=LM row1, z=LP row3
        assert label_bigram("e", "z") == "scissor"

    def test_bottom_to_top_right(self):
        # m=RI row3, u=RI row1 — same finger → sfb
        # Different fingers: m=RI row3, i=RM row1
        assert label_bigram("m", "i") == "scissor"

    def test_number_row_to_bottom_left(self):
        # 3=LM row0, c=LM row3 — same finger → sfb
        # 3=LM row0, v=LI row3 — different fingers, row gap=3
        assert label_bigram("3", "v") == "scissor"

    def test_top_to_bottom_right(self):
        # i=RM row1, comma=RM row3 — same finger → sfb
        # o=RR row1, comma=RM row3 — different finger, row gap=2
        assert label_bigram("o", ",") == "scissor"

    def test_reversed_scissor(self):
        assert label_bigram("v", "3") == "scissor"

    def test_number_row_to_bottom_right(self):
        # 8=RM row0, m=RI row3
        assert label_bigram("8", "m") == "scissor"


# ---------------------------------------------------------------------------
# Inward roll — same hand, movement toward index finger
# ---------------------------------------------------------------------------

class TestRollIn:
    def test_left_pinky_to_ring(self):
        # a=LP, s=LR, same row (home) → roll_in (LP→LR is inward)
        assert label_bigram("a", "s") == "roll_in"

    def test_left_ring_to_index(self):
        # s=LR, f=LI, same row
        assert label_bigram("s", "f") == "roll_in"

    def test_left_top_row_inward(self):
        # e=LM, r=LI
        assert label_bigram("e", "r") == "roll_in"

    def test_right_pinky_to_ring(self):
        # ;=RP, l=RR → inward (RP→RR on right hand)
        assert label_bigram(";", "l") == "roll_in"

    def test_right_ring_to_index(self):
        # l=RR, h=RI → inward
        assert label_bigram("l", "h") == "roll_in"

    def test_right_top_row_inward(self):
        # o=RR, u=RI
        assert label_bigram("o", "u") == "roll_in"


# ---------------------------------------------------------------------------
# Outward roll — same hand, movement away from index finger
# ---------------------------------------------------------------------------

class TestRollOut:
    def test_left_index_to_ring(self):
        # f=LI, s=LR → outward (LI→LR is outward on left hand)
        assert label_bigram("f", "s") == "roll_out"

    def test_left_index_to_pinky(self):
        # f=LI, a=LP → outward
        assert label_bigram("f", "a") == "roll_out"

    def test_left_top_row_outward(self):
        # r=LI, w=LR → outward
        assert label_bigram("r", "w") == "roll_out"

    def test_right_index_to_ring(self):
        # j=RI, l=RR → outward (RI→RR is outward on right hand)
        assert label_bigram("j", "l") == "roll_out"

    def test_right_index_to_pinky(self):
        # h=RI, ;=RP → outward
        assert label_bigram("h", ";") == "roll_out"

    def test_right_top_row_outward(self):
        # u=RI, o=RR → outward
        assert label_bigram("u", "o") == "roll_out"


# ---------------------------------------------------------------------------
# Alternation — different hands
# ---------------------------------------------------------------------------

class TestAlternation:
    def test_left_index_right_index(self):
        assert label_bigram("f", "j") == "alternation"

    def test_left_ring_right_ring(self):
        assert label_bigram("s", "l") == "alternation"

    def test_left_middle_right_middle(self):
        assert label_bigram("d", "k") == "alternation"

    def test_left_pinky_right_pinky(self):
        assert label_bigram("a", ";") == "alternation"

    def test_top_row_cross_hand(self):
        # t=LI, y=RI — classic alternation on top row
        assert label_bigram("t", "y") == "alternation"

    def test_number_row_cross_hand(self):
        # 4=LI, 7=RI
        assert label_bigram("4", "7") == "alternation"

    def test_reversed_alternation(self):
        assert label_bigram("j", "f") == "alternation"


# ---------------------------------------------------------------------------
# Lateral stretch — pinky involved, different rows
# ---------------------------------------------------------------------------

class TestLateral:
    def test_left_pinky_home_to_top(self):
        # a=LP row2, q=LP row1 — same finger → sfb, not lateral
        # Need different finger: a=LP row2, w=LR row1
        # But LP involved? a=LP. row_delta=1. But LR is not LP or RP.
        # Lateral requires finger_a or finger_b to be LP or RP.
        # a=LP row2, q=LP row1: same finger → sfb
        # z=LP row3, q=LP row1: same finger → sfb
        # What pairs involve LP + something different?
        # LP is involved if key is in {a,z,q,1,`}
        # Their finger is LP. For a different finger + LP + row_delta:
        # a=LP row2 and s=LR row2 → same row, so row_delta=0 → roll
        # a=LP row2 and w=LR row1 → LP involved, row_delta=1 → lateral
        assert label_bigram("a", "w") == "lateral"

    def test_right_pinky_home_to_top(self):
        # ;=RP row2, p=RP row1 → same finger → sfb
        # ;=RP row2, o=RR row1 → RP involved, row_delta=1 → lateral
        assert label_bigram(";", "o") == "lateral"

    def test_left_pinky_bottom_to_home(self):
        # z=LP row3, s=LR row2 → LP involved, row_delta=1 → lateral
        assert label_bigram("z", "s") == "lateral"

    def test_right_pinky_bottom_to_home(self):
        # /=RP row3, l=RR row2 → RP involved, row_delta=1 → lateral
        assert label_bigram("/", "l") == "lateral"

    def test_left_pinky_top_to_home(self):
        # q=LP row1, s=LR row2 → LP involved, row_delta=1 → lateral
        assert label_bigram("q", "s") == "lateral"


# ---------------------------------------------------------------------------
# Unknown — excluded keys, modifiers, unrecognised characters
# ---------------------------------------------------------------------------

class TestUnknown:
    def test_shift_excluded(self):
        assert label_bigram("Shift", "a") == "unknown"

    def test_backspace_excluded(self):
        assert label_bigram("Backspace", "a") == "unknown"

    def test_backspace_second_position(self):
        assert label_bigram("a", "Backspace") == "unknown"

    def test_space_excluded(self):
        assert label_bigram(" ", "a") == "unknown"

    def test_enter_excluded(self):
        assert label_bigram("Enter", "a") == "unknown"

    def test_unrecognised_character(self):
        assert label_bigram("€", "a") == "unknown"

    def test_both_unknown(self):
        assert label_bigram("€", "£") == "unknown"

    def test_unsupported_layout_raises(self):
        with pytest.raises(ValueError, match="Unsupported layout"):
            label_bigram("a", "b", layout="dvorak")

    def test_f1_function_key(self):
        assert label_bigram("F1", "a") == "unknown"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_t_and_b_are_sfb(self):
        # Both assigned to LI by canonical QWERTY map
        assert label_bigram("t", "b") == "sfb"

    def test_g_and_h_alternate(self):
        # g=LI, h=RI → cross-hand alternation
        assert label_bigram("g", "h") == "alternation"

    def test_case_insensitive_lowercase(self):
        assert label_bigram("F", "J") == label_bigram("f", "j")

    def test_case_insensitive_sfb(self):
        assert label_bigram("R", "T") == "sfb"

    def test_shifted_characters(self):
        # "@" maps to LR (same as "2"), "W" maps to LR → sfb
        assert label_bigram("@", "w") == "sfb"

    def test_number_to_letter_roll(self):
        # 4=LI row0, f=LI row2 → same finger → sfb
        # 4=LI row0, d=LM row2 → row_delta=2 → scissor (different finger, skip row)
        assert label_bigram("4", "d") == "scissor"

    def test_home_row_only_roll(self):
        # All home row bigrams on same hand are rolls (no row delta)
        assert label_bigram("s", "d") == "roll_in"   # LR→LM inward
        assert label_bigram("d", "s") == "roll_out"  # LM→LR outward


# ---------------------------------------------------------------------------
# Redirect (trigram)
# ---------------------------------------------------------------------------

class TestRedirect:
    def test_left_hand_redirect(self):
        # e=LM, r=LI, e=LM → inward (LM→LI) then outward (LI→LM) → redirect
        assert label_redirect("e", "r", "e") is True

    def test_right_hand_redirect(self):
        # u=RI, i=RM, u=RI → outward (RI→RM on right) then inward (RM→RI) → redirect
        # Right hand: inward means index decreasing.
        # RI=6, RM=7: RI→RM means 6→7, finger_a < finger_b... wait.
        # For right hand: inward = finger_a > finger_b.
        # RI=6→RM=7: 6 > 7? No. So RI→RM is NOT inward. It's outward.
        # RM=7→RI=6: 7 > 6? Yes. So RM→RI is inward.
        # So u(RI=6) → i(RM=7): outward. i(RM=7) → u(RI=6): inward. → direction changes → redirect
        assert label_redirect("u", "i", "u") is True

    def test_consistent_inward_not_redirect(self):
        # a=LP, s=LR, d=LM: all inward (LP→LR→LM) → no redirect
        assert label_redirect("a", "s", "d") is False

    def test_consistent_outward_not_redirect(self):
        # d=LM, s=LR, a=LP: all outward → no redirect
        assert label_redirect("d", "s", "a") is False

    def test_cross_hand_not_redirect(self):
        # f=LI, j=RI, k=RM: different hands → not a same-hand redirect
        assert label_redirect("f", "j", "k") is False

    def test_sfb_in_sequence_not_redirect(self):
        # r=LI, t=LI (sfb), e=LM → SFB present → not classified as redirect
        assert label_redirect("r", "t", "e") is False

    def test_unknown_key_not_redirect(self):
        assert label_redirect("f", "Backspace", "d") is False
