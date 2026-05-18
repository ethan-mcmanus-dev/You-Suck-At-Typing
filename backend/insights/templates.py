"""
Insight message templates for each of the 7 biomechanical features.

Each feature has:
  headline  — shown when deviation > +2σ (the "wow" finding)
  secondary — shown when deviation is between +1.5σ and +2σ
  positive  — shown when deviation < -1.5σ (user is noticeably better than peers)

All templates use {value:.0f} for the raw measured value (in ms or %)
and {delta:.0f} for the absolute ms/% difference from the cluster mean.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class InsightTemplate:
    feature: str
    headline: str
    secondary: str
    positive: str


TEMPLATES: dict[str, InsightTemplate] = {
    "mean_dwell_sfb": InsightTemplate(
        feature="mean_dwell_sfb",
        headline=(
            "You hold same-finger keys for {value:.0f} ms on average — "
            "{delta:.0f} ms longer than typists like you. "
            "Your fingers are tensing up before they can move."
        ),
        secondary=(
            "Your dwell time on same-finger bigrams ({value:.0f} ms) is "
            "above average for your cluster. Try releasing keys sooner "
            "rather than holding through the transition."
        ),
        positive=(
            "Your dwell time on same-finger keys ({value:.0f} ms) is "
            "shorter than most typists in your group — clean, light touch."
        ),
    ),

    "mean_flight_sfb": InsightTemplate(
        feature="mean_flight_sfb",
        headline=(
            "Same-finger bigrams cost you {value:.0f} ms of flight time — "
            "{delta:.0f} ms more than your cluster. "
            "These are the sequences slowing you down the most."
        ),
        secondary=(
            "Your same-finger transition time ({value:.0f} ms) is higher "
            "than peers. Focus drill: type 'ed', 'de', 'un', 'nu' at "
            "comfortable speed until the transition feels smooth."
        ),
        positive=(
            "Your same-finger recovery ({value:.0f} ms) is faster than "
            "most. You've learned to sequence same-finger keys efficiently."
        ),
    ),

    "mean_flight_roll_in": InsightTemplate(
        feature="mean_flight_roll_in",
        headline=(
            "Inward rolls take you {value:.0f} ms — {delta:.0f} ms slower "
            "than your cluster. You're not yet capitalizing on your "
            "hand's natural inward motion."
        ),
        secondary=(
            "Your inward roll speed ({value:.0f} ms) has room to improve. "
            "Inward rolls should feel like a single wave — try 'er', 'tr', "
            "'ui' and focus on the cascading finger motion."
        ),
        positive=(
            "Your inward rolls ({value:.0f} ms) are faster than your "
            "cluster average — your finger sequencing is fluid."
        ),
    ),

    "mean_flight_roll_out": InsightTemplate(
        feature="mean_flight_roll_out",
        headline=(
            "Outward rolls cost {value:.0f} ms — {delta:.0f} ms above your "
            "cluster. Outward motion is naturally harder; yours shows "
            "more resistance than expected."
        ),
        secondary=(
            "Your outward roll time ({value:.0f} ms) is above average. "
            "Outward rolls (like 'we', 'io') are the hardest for most "
            "typists — slow deliberate practice helps more than speed drills."
        ),
        positive=(
            "Your outward rolls ({value:.0f} ms) beat your cluster — "
            "strong finger independence."
        ),
    ),

    "mean_flight_alternation": InsightTemplate(
        feature="mean_flight_alternation",
        headline=(
            "Hand alternation takes you {value:.0f} ms — {delta:.0f} ms "
            "slower than peers. You're not fully using the rhythm advantage "
            "that alternating hands provides."
        ),
        secondary=(
            "Your alternation flight time ({value:.0f} ms) is above your "
            "cluster. Cross-hand transitions should be your fastest — "
            "try relaxing your wrists during alternating sequences."
        ),
        positive=(
            "Hand alternation is a strength at {value:.0f} ms — "
            "below your cluster average."
        ),
    ),

    "mean_flight_scissor": InsightTemplate(
        feature="mean_flight_scissor",
        headline=(
            "Scissor bigrams (two-row jumps) slow you to {value:.0f} ms — "
            "{delta:.0f} ms above your cluster. These diagonal stretches "
            "are causing visible hesitation."
        ),
        secondary=(
            "Your scissor transition time ({value:.0f} ms) is higher than "
            "peers. Scissor bigrams like 'ce', 'xt' require row-skipping — "
            "consciously lifting your finger fully before the next press helps."
        ),
        positive=(
            "Scissor bigrams ({value:.0f} ms) are handled well — "
            "below cluster average. Good row-to-row control."
        ),
    ),

    "mean_flight_lateral": InsightTemplate(
        feature="mean_flight_lateral",
        headline=(
            "Lateral stretches to your pinky cost {value:.0f} ms — "
            "{delta:.0f} ms more than your cluster. "
            "Pinky reach is a consistent bottleneck."
        ),
        secondary=(
            "Your pinky-reach transitions ({value:.0f} ms) are above "
            "average. Try anchoring your hand position so the pinky "
            "extends rather than the whole hand shifting."
        ),
        positive=(
            "Your pinky lateral reach ({value:.0f} ms) is faster than "
            "most — good hand anchoring."
        ),
    ),
}
