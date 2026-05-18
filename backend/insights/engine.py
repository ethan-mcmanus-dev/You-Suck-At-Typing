"""
Z-score deviation engine for biomechanical typing insights.

Takes a FeatureVector and a ClusterModel (plus the assigned cluster index)
and returns a ranked list of Insight objects. Insights are generated only
for features where the user's value deviates more than INSIGHT_THRESHOLD
standard deviations from their cluster's mean.

Thresholds:
  |z| > HEADLINE_THRESHOLD  → severity "headline" (the lead finding)
  |z| > INSIGHT_THRESHOLD   → severity "secondary" (supporting detail)
  z < -INSIGHT_THRESHOLD    → severity "positive" (a genuine strength)

The engine is pure Python with no I/O — callers persist results however
they like (DB, JSON, etc.).
"""

from dataclasses import dataclass, field
from typing import Literal

from features import FeatureVector

# Populated at import time from the shared ClusterModel type
# (imported inline to avoid circular imports at module level)

INSIGHT_THRESHOLD = 1.5
HEADLINE_THRESHOLD = 2.0

Severity = Literal["headline", "secondary", "positive"]

_CLUSTER_FEATURE_NAMES = [
    "mean_dwell_sfb",
    "mean_flight_sfb",
    "mean_flight_roll_in",
    "mean_flight_roll_out",
    "mean_flight_alternation",
    "mean_flight_scissor",
    "mean_flight_lateral",
]


@dataclass
class Insight:
    """A single actionable insight for one biomechanical feature.

    feature:   the name of the feature this insight refers to
    severity:  "headline" | "secondary" | "positive"
    z_score:   how many standard deviations from the cluster mean
    user_value: the user's raw measured value (ms or fraction)
    cluster_mean: the cluster's mean for this feature
    message:   the formatted human-readable insight string
    """

    feature: str
    severity: Severity
    z_score: float
    user_value: float
    cluster_mean: float
    message: str


@dataclass
class InsightReport:
    """All insights generated for a single session.

    headline:    the single highest-severity finding (may be None if no
                 feature crosses HEADLINE_THRESHOLD)
    secondary:   all other insights above INSIGHT_THRESHOLD, sorted by
                 |z_score| descending
    positives:   strengths (z < -INSIGHT_THRESHOLD), sorted by z_score ascending
    cluster_idx: which cluster the session was assigned to
    n_features_observed: how many of the 7 features had data
    """

    headline: Insight | None
    secondary: list[Insight] = field(default_factory=list)
    positives: list[Insight] = field(default_factory=list)
    cluster_idx: int = 0
    n_features_observed: int = 0


def compute_insights(
    fv: FeatureVector,
    model,  # ClusterModel — typed as Any to avoid circular import
    cluster_idx: int,
) -> InsightReport:
    """Generate insights by comparing fv to its assigned cluster.

    Args:
        fv:          FeatureVector from features.compute_features()
        model:       ClusterModel from ml.clustering.fit
        cluster_idx: index returned by ml.clustering.fit.assign_cluster()

    Returns:
        InsightReport with ranked insights.
    """
    from .templates import TEMPLATES

    centroid = model.centroids[cluster_idx]
    stds = model.stds[cluster_idx]

    all_insights: list[Insight] = []
    n_observed = 0

    for j, feat_name in enumerate(_CLUSTER_FEATURE_NAMES):
        user_val: float | None = getattr(fv, feat_name)
        if user_val is None:
            continue

        n_observed += 1
        cluster_mean = centroid[j]
        cluster_std = max(stds[j], 1e-6)
        z = (user_val - cluster_mean) / cluster_std

        if abs(z) < INSIGHT_THRESHOLD:
            continue

        tmpl = TEMPLATES.get(feat_name)
        if tmpl is None:
            continue

        delta = abs(user_val - cluster_mean)

        if z > HEADLINE_THRESHOLD:
            severity: Severity = "headline"
            message = tmpl.headline.format(value=user_val, delta=delta)
        elif z > INSIGHT_THRESHOLD:
            severity = "secondary"
            message = tmpl.secondary.format(value=user_val, delta=delta)
        else:
            severity = "positive"
            message = tmpl.positive.format(value=user_val, delta=delta)

        all_insights.append(
            Insight(
                feature=feat_name,
                severity=severity,
                z_score=z,
                user_value=user_val,
                cluster_mean=cluster_mean,
                message=message,
            )
        )

    # Split and rank
    headlines = [i for i in all_insights if i.severity == "headline"]
    secondary = [i for i in all_insights if i.severity == "secondary"]
    positives = [i for i in all_insights if i.severity == "positive"]

    # Pick the single most extreme headline; demote the rest to secondary
    lead: Insight | None = None
    if headlines:
        headlines.sort(key=lambda i: i.z_score, reverse=True)
        lead = headlines[0]
        secondary = headlines[1:] + secondary

    secondary.sort(key=lambda i: abs(i.z_score), reverse=True)
    positives.sort(key=lambda i: i.z_score)

    return InsightReport(
        headline=lead,
        secondary=secondary,
        positives=positives,
        cluster_idx=cluster_idx,
        n_features_observed=n_observed,
    )
