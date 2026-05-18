"""
Tests for the insight engine and templates.

Run from the project root:
    cd backend && python -m pytest tests/test_insights.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ml"))

from features import compute_features, FeatureVector
from insights import (
    HEADLINE_THRESHOLD,
    INSIGHT_THRESHOLD,
    TEMPLATES,
    Insight,
    InsightReport,
    compute_insights,
)
from data.synthetic import make_synthetic_sessions
from clustering.fit import ClusterModel, assign_cluster, fit_clusters


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_model_and_sessions():
    sessions = make_synthetic_sessions(n=90, seed=7)
    model = fit_clusters(sessions, k=3, seed=7)
    return model, sessions


def _fv_for_session(session):
    return compute_features(session.events)


# ---------------------------------------------------------------------------
# Template completeness
# ---------------------------------------------------------------------------


class TestTemplates:
    def test_all_seven_features_have_templates(self):
        features = [
            "mean_dwell_sfb", "mean_flight_sfb", "mean_flight_roll_in",
            "mean_flight_roll_out", "mean_flight_alternation",
            "mean_flight_scissor", "mean_flight_lateral",
        ]
        for f in features:
            assert f in TEMPLATES, f"Missing template for {f}"

    def test_headline_contains_format_slots(self):
        for name, tmpl in TEMPLATES.items():
            # Should not raise when formatted with typical values
            tmpl.headline.format(value=100.0, delta=20.0)
            tmpl.secondary.format(value=100.0, delta=20.0)
            tmpl.positive.format(value=100.0, delta=20.0)

    def test_no_empty_message_strings(self):
        for name, tmpl in TEMPLATES.items():
            assert len(tmpl.headline.strip()) > 10, f"{name} headline too short"
            assert len(tmpl.secondary.strip()) > 10, f"{name} secondary too short"
            assert len(tmpl.positive.strip()) > 10, f"{name} positive too short"

    def test_feature_field_matches_key(self):
        for name, tmpl in TEMPLATES.items():
            assert tmpl.feature == name


# ---------------------------------------------------------------------------
# compute_insights — basic contract
# ---------------------------------------------------------------------------


class TestComputeInsightsContract:
    def setup_method(self):
        self.model, self.sessions = _make_model_and_sessions()

    def test_returns_insight_report(self):
        fv = _fv_for_session(self.sessions[0])
        idx = assign_cluster(fv, self.model)
        report = compute_insights(fv, self.model, idx)
        assert isinstance(report, InsightReport)

    def test_cluster_idx_stored(self):
        fv = _fv_for_session(self.sessions[0])
        idx = assign_cluster(fv, self.model)
        report = compute_insights(fv, self.model, idx)
        assert report.cluster_idx == idx

    def test_n_features_observed_at_most_seven(self):
        fv = _fv_for_session(self.sessions[0])
        idx = assign_cluster(fv, self.model)
        report = compute_insights(fv, self.model, idx)
        assert 0 <= report.n_features_observed <= 7

    def test_headline_is_none_or_insight(self):
        fv = _fv_for_session(self.sessions[0])
        idx = assign_cluster(fv, self.model)
        report = compute_insights(fv, self.model, idx)
        assert report.headline is None or isinstance(report.headline, Insight)

    def test_secondary_is_list_of_insight(self):
        fv = _fv_for_session(self.sessions[0])
        idx = assign_cluster(fv, self.model)
        report = compute_insights(fv, self.model, idx)
        assert isinstance(report.secondary, list)
        assert all(isinstance(i, Insight) for i in report.secondary)

    def test_positives_is_list_of_insight(self):
        fv = _fv_for_session(self.sessions[0])
        idx = assign_cluster(fv, self.model)
        report = compute_insights(fv, self.model, idx)
        assert isinstance(report.positives, list)
        assert all(isinstance(i, Insight) for i in report.positives)

    def test_headline_has_highest_z_among_headlines(self):
        fv = _fv_for_session(self.sessions[0])
        idx = assign_cluster(fv, self.model)
        report = compute_insights(fv, self.model, idx)
        if report.headline and report.secondary:
            for other in report.secondary:
                if other.severity == "headline":
                    assert report.headline.z_score >= other.z_score

    def test_secondary_sorted_by_abs_z_descending(self):
        fv = _fv_for_session(self.sessions[0])
        idx = assign_cluster(fv, self.model)
        report = compute_insights(fv, self.model, idx)
        zs = [abs(i.z_score) for i in report.secondary]
        assert zs == sorted(zs, reverse=True)

    def test_positives_sorted_by_z_ascending(self):
        fv = _fv_for_session(self.sessions[0])
        idx = assign_cluster(fv, self.model)
        report = compute_insights(fv, self.model, idx)
        zs = [i.z_score for i in report.positives]
        assert zs == sorted(zs)


# ---------------------------------------------------------------------------
# compute_insights — thresholds enforced
# ---------------------------------------------------------------------------


class TestThresholds:
    def test_no_insight_below_threshold(self):
        """Every insight returned must have |z| >= INSIGHT_THRESHOLD."""
        model, sessions = _make_model_and_sessions()
        for session in sessions[:10]:
            fv = _fv_for_session(session)
            idx = assign_cluster(fv, model)
            report = compute_insights(fv, model, idx)
            all_insights = (
                ([report.headline] if report.headline else [])
                + report.secondary
                + report.positives
            )
            for ins in all_insights:
                assert abs(ins.z_score) >= INSIGHT_THRESHOLD, (
                    f"{ins.feature} z={ins.z_score:.2f} below threshold"
                )

    def test_headline_severity_requires_high_z(self):
        """Headline severity must only appear when z > HEADLINE_THRESHOLD."""
        model, sessions = _make_model_and_sessions()
        for session in sessions[:10]:
            fv = _fv_for_session(session)
            idx = assign_cluster(fv, model)
            report = compute_insights(fv, model, idx)
            if report.headline:
                assert report.headline.z_score > HEADLINE_THRESHOLD

    def test_positive_severity_has_negative_z(self):
        """Positive insights must have z < -INSIGHT_THRESHOLD."""
        model, sessions = _make_model_and_sessions()
        for session in sessions[:10]:
            fv = _fv_for_session(session)
            idx = assign_cluster(fv, model)
            report = compute_insights(fv, model, idx)
            for ins in report.positives:
                assert ins.z_score < -INSIGHT_THRESHOLD


# ---------------------------------------------------------------------------
# compute_insights — forced deviation (synthetic FeatureVector)
# ---------------------------------------------------------------------------


def _make_model_with_tight_cluster() -> tuple:
    """Return a model where cluster 0 has tight, known statistics."""
    sessions = make_synthetic_sessions(n=90, seed=99)
    model = fit_clusters(sessions, k=3, seed=99)
    return model


class TestForcedDeviation:
    def test_large_sfb_flight_triggers_headline(self):
        """Manually set sfb flight far above cluster mean to force headline."""
        model = _make_model_with_tight_cluster()
        cluster_mean = model.centroids[0][1]  # mean_flight_sfb
        cluster_std = model.stds[0][1]
        # Set sfb flight 3σ above mean — should definitely trigger headline
        extreme_val = cluster_mean + 3.5 * cluster_std

        fv = FeatureVector(
            mean_dwell_sfb=80.0,
            mean_flight_sfb=extreme_val,
            mean_flight_roll_in=100.0,
            mean_flight_roll_out=110.0,
            mean_flight_alternation=95.0,
            mean_flight_scissor=120.0,
            mean_flight_lateral=130.0,
            redirect_rate=0.1,
            rollover_rate=0.0,
            n_keystrokes=200,
            n_bigrams_labeled=180,
        )

        report = compute_insights(fv, model, cluster_idx=0)
        assert report.headline is not None
        assert report.headline.feature == "mean_flight_sfb"
        assert report.headline.severity == "headline"

    def test_all_features_at_cluster_mean_produces_no_insights(self):
        """If every feature equals the cluster mean, no insight should fire."""
        model = _make_model_with_tight_cluster()
        centroid = model.centroids[0]
        feat_names = model.feature_names

        kwargs = {name: centroid[j] for j, name in enumerate(feat_names)}
        kwargs.update(
            redirect_rate=0.1,
            rollover_rate=0.0,
            n_keystrokes=200,
            n_bigrams_labeled=180,
        )
        fv = FeatureVector(**kwargs)

        report = compute_insights(fv, model, cluster_idx=0)
        assert report.headline is None
        assert report.secondary == []
        assert report.positives == []

    def test_low_sfb_flight_triggers_positive(self):
        """Feature well below cluster mean should produce a positive insight."""
        model = _make_model_with_tight_cluster()
        cluster_mean = model.centroids[0][1]  # mean_flight_sfb
        cluster_std = model.stds[0][1]
        low_val = cluster_mean - 3.0 * cluster_std

        fv = FeatureVector(
            mean_dwell_sfb=80.0,
            mean_flight_sfb=low_val,
            mean_flight_roll_in=100.0,
            mean_flight_roll_out=110.0,
            mean_flight_alternation=95.0,
            mean_flight_scissor=120.0,
            mean_flight_lateral=130.0,
            redirect_rate=0.1,
            rollover_rate=0.0,
            n_keystrokes=200,
            n_bigrams_labeled=180,
        )

        report = compute_insights(fv, model, cluster_idx=0)
        positive_features = [i.feature for i in report.positives]
        assert "mean_flight_sfb" in positive_features

    def test_message_contains_formatted_value(self):
        """Formatted message must embed the actual numeric value."""
        model = _make_model_with_tight_cluster()
        cluster_mean = model.centroids[0][1]
        cluster_std = model.stds[0][1]
        extreme_val = cluster_mean + 3.5 * cluster_std

        fv = FeatureVector(
            mean_dwell_sfb=80.0,
            mean_flight_sfb=extreme_val,
            mean_flight_roll_in=100.0,
            mean_flight_roll_out=110.0,
            mean_flight_alternation=95.0,
            mean_flight_scissor=120.0,
            mean_flight_lateral=130.0,
            redirect_rate=0.1,
            rollover_rate=0.0,
            n_keystrokes=200,
            n_bigrams_labeled=180,
        )

        report = compute_insights(fv, model, cluster_idx=0)
        assert report.headline is not None
        expected_val_str = f"{extreme_val:.0f}"
        assert expected_val_str in report.headline.message

    def test_only_one_headline_in_report(self):
        """Even when multiple features cross headline threshold, only one headline."""
        model = _make_model_with_tight_cluster()
        centroid = model.centroids[0]
        stds = model.stds[0]

        # Push all 7 features 3σ above mean
        kwargs = {
            name: centroid[j] + 3.5 * stds[j]
            for j, name in enumerate(model.feature_names)
        }
        kwargs.update(
            redirect_rate=0.1,
            rollover_rate=0.0,
            n_keystrokes=200,
            n_bigrams_labeled=180,
        )
        fv = FeatureVector(**kwargs)

        report = compute_insights(fv, model, cluster_idx=0)
        assert report.headline is not None
        # The demoted headlines should appear in secondary
        headline_count_in_secondary = sum(
            1 for i in report.secondary if i.z_score > HEADLINE_THRESHOLD
        )
        assert headline_count_in_secondary == 6  # 7 total - 1 lead = 6 demoted


# ---------------------------------------------------------------------------
# None feature values
# ---------------------------------------------------------------------------


class TestMissingFeatures:
    def test_none_feature_excluded_from_insights(self):
        """A None feature value must not produce an insight."""
        model = _make_model_with_tight_cluster()
        cluster_mean = model.centroids[0][1]
        cluster_std = model.stds[0][1]
        extreme_val = cluster_mean + 3.5 * cluster_std

        fv = FeatureVector(
            mean_dwell_sfb=None,  # missing — no bigrams of this class
            mean_flight_sfb=extreme_val,
            mean_flight_roll_in=None,
            mean_flight_roll_out=None,
            mean_flight_alternation=None,
            mean_flight_scissor=None,
            mean_flight_lateral=None,
            redirect_rate=None,
            rollover_rate=None,
            n_keystrokes=200,
            n_bigrams_labeled=50,
        )

        report = compute_insights(fv, model, cluster_idx=0)
        all_features = (
            ([report.headline.feature] if report.headline else [])
            + [i.feature for i in report.secondary]
            + [i.feature for i in report.positives]
        )
        assert "mean_dwell_sfb" not in all_features
        assert "mean_flight_roll_in" not in all_features

    def test_n_features_observed_counts_non_none(self):
        model = _make_model_with_tight_cluster()
        fv = FeatureVector(
            mean_dwell_sfb=80.0,
            mean_flight_sfb=None,
            mean_flight_roll_in=100.0,
            mean_flight_roll_out=None,
            mean_flight_alternation=95.0,
            mean_flight_scissor=None,
            mean_flight_lateral=None,
            redirect_rate=None,
            rollover_rate=None,
            n_keystrokes=200,
            n_bigrams_labeled=50,
        )
        idx = assign_cluster(fv, model) or 0
        report = compute_insights(fv, model, cluster_idx=0)
        assert report.n_features_observed == 3
