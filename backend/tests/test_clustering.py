"""
Tests for the clustering pipeline and Aalto parser.

Run from the project root:
    cd backend && python -m pytest tests/test_clustering.py -v
"""

import io
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ml"))

from data.synthetic import make_synthetic_sessions
from data.aalto import AaltoSessions, _normalize_letter
from clustering.fit import (
    ClusterModel,
    assign_cluster,
    fit_clusters,
    load_model,
    _extract_row,
    _standardize,
)
from features import compute_features


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_aalto_dir(n_keystrokes: int = 120, n_participants: int = 1, seed: int = 7) -> str:
    """Return a temp directory path containing per-participant Aalto .txt files."""
    import random

    rng = random.Random(seed)
    keys = ["t", "h", "e", "q", "u", "i", "c", "b", "r", "o", "w", "n", "f", "a"]
    tmpdir = tempfile.mkdtemp()

    for p in range(n_participants):
        pid = 100000 + p
        lines = [
            "PARTICIPANT_ID\tTEST_SECTION_ID\tSENTENCE\tUSER_INPUT\t"
            "KEYSTROKE_ID\tPRESS_TIME\tRELEASE_TIME\tLETTER\tKEYCODE"
        ]
        t = 1000.0 + p * 200_000
        for k in range(n_keystrokes):
            key = rng.choice(keys)
            press = t
            release = press + rng.uniform(40, 100)
            lines.append(
                f"{pid}\t{pid}01\tsentence\tinput\t{k}\t{press:.1f}\t{release:.1f}\t{key}\t65"
            )
            t = release + rng.uniform(30, 80)

        filepath = os.path.join(tmpdir, f"{pid}_keystrokes.txt")
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(lines))

    return tmpdir


# ---------------------------------------------------------------------------
# _normalize_key
# ---------------------------------------------------------------------------


class TestNormalizeLetter:
    def test_lowercase_letter_unchanged(self):
        assert _normalize_letter("a") == "a"
        assert _normalize_letter("z") == "z"

    def test_uppercase_letter_lowercased(self):
        assert _normalize_letter("A") == "a"
        assert _normalize_letter("W") == "w"

    def test_shift_lowercased(self):
        assert _normalize_letter("SHIFT") == "shift"

    def test_bksp_mapped(self):
        assert _normalize_letter("BKSP") == "backspace"

    def test_arw_left_mapped(self):
        assert _normalize_letter("ARW_LEFT") == "arrowleft"

    def test_caps_lock_mapped(self):
        assert _normalize_letter("CAPS_LOCK") == "capslock"

    def test_unknown_lowercased(self):
        assert _normalize_letter("SOMEKEY") == "somekey"


# ---------------------------------------------------------------------------
# AaltoSessions
# ---------------------------------------------------------------------------


class TestAaltoSessions:
    def test_parses_expected_participant_count(self):
        import shutil
        tmpdir = _make_aalto_dir(n_keystrokes=120, n_participants=3)
        try:
            sessions = list(AaltoSessions(tmpdir, min_keystrokes=20))
            assert len(sessions) == 3
        finally:
            shutil.rmtree(tmpdir)

    def test_session_context_is_prose(self):
        import shutil
        tmpdir = _make_aalto_dir(n_keystrokes=120)
        try:
            sessions = list(AaltoSessions(tmpdir))
            assert sessions[0].session_context == "prose"
        finally:
            shutil.rmtree(tmpdir)

    def test_events_ordered_by_keydown(self):
        import shutil
        tmpdir = _make_aalto_dir(n_keystrokes=120)
        try:
            sessions = list(AaltoSessions(tmpdir))
            ev = sessions[0].events
            for i in range(len(ev) - 1):
                assert ev[i].keydown_ms <= ev[i + 1].keydown_ms
        finally:
            shutil.rmtree(tmpdir)

    def test_participant_id_stored(self):
        import shutil
        tmpdir = _make_aalto_dir(n_keystrokes=120, n_participants=2)
        try:
            sessions = list(AaltoSessions(tmpdir))
            pids = {s.participant_id for s in sessions}
            assert len(pids) == 2
        finally:
            shutil.rmtree(tmpdir)

    def test_participant_below_min_keystrokes_skipped(self):
        import shutil
        tmpdir = _make_aalto_dir(n_keystrokes=10, n_participants=1)
        try:
            sessions = list(AaltoSessions(tmpdir, min_keystrokes=50))
            assert len(sessions) == 0
        finally:
            shutil.rmtree(tmpdir)

    def test_malformed_timing_row_skipped(self):
        import shutil
        tmpdir = tempfile.mkdtemp()
        header = ("PARTICIPANT_ID\tTEST_SECTION_ID\tSENTENCE\tUSER_INPUT\t"
                  "KEYSTROKE_ID\tPRESS_TIME\tRELEASE_TIME\tLETTER\tKEYCODE")
        lines = [header, "1\t101\ts\tu\t0\tnot_a_number\t200.0\ta\t65"]
        t = 1000.0
        for k in range(30):
            press = t
            release = press + 80
            lines.append(f"1\t101\ts\tu\t{k+1}\t{press:.1f}\t{release:.1f}\tt\t84")
            t = release + 60
        filepath = os.path.join(tmpdir, "1_keystrokes.txt")
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(lines))
        try:
            sessions = list(AaltoSessions(tmpdir, min_keystrokes=20))
            assert len(sessions) == 1
            assert len(sessions[0].events) == 30
        finally:
            shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


class TestStandardize:
    def test_zero_mean_unit_std(self):
        matrix = [[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]]
        normed, means, stds = _standardize(matrix)
        for col in range(2):
            col_vals = [normed[i][col] for i in range(3)]
            import statistics
            assert abs(statistics.mean(col_vals)) < 1e-9
            assert abs(statistics.stdev(col_vals) - 1.0) < 1e-9

    def test_constant_column_uses_one_for_std(self):
        matrix = [[5.0], [5.0], [5.0]]
        normed, means, stds = _standardize(matrix)
        assert stds[0] == 1.0
        assert all(normed[i][0] == 0.0 for i in range(3))


# ---------------------------------------------------------------------------
# fit_clusters
# ---------------------------------------------------------------------------


class TestFitClusters:
    def test_returns_cluster_model(self):
        sessions = make_synthetic_sessions(n=40, seed=1)
        model = fit_clusters(sessions, k=3)
        assert isinstance(model, ClusterModel)

    def test_correct_number_of_centroids(self):
        sessions = make_synthetic_sessions(n=40, seed=2)
        model = fit_clusters(sessions, k=3)
        assert len(model.centroids) == 3

    def test_centroid_feature_count(self):
        sessions = make_synthetic_sessions(n=40, seed=3)
        model = fit_clusters(sessions, k=3)
        assert all(len(c) == 7 for c in model.centroids)

    def test_stds_shape_matches_centroids(self):
        sessions = make_synthetic_sessions(n=40, seed=4)
        model = fit_clusters(sessions, k=3)
        assert len(model.stds) == len(model.centroids)
        assert all(len(s) == 7 for s in model.stds)

    def test_n_sessions_stored(self):
        sessions = make_synthetic_sessions(n=40, seed=5)
        model = fit_clusters(sessions, k=3)
        assert model.n_sessions <= 40  # some may be filtered
        assert model.n_sessions > 0

    def test_feature_names_correct(self):
        sessions = make_synthetic_sessions(n=40, seed=6)
        model = fit_clusters(sessions, k=3)
        assert model.feature_names == [
            "mean_dwell_sfb", "mean_flight_sfb", "mean_flight_roll_in",
            "mean_flight_roll_out", "mean_flight_alternation",
            "mean_flight_scissor", "mean_flight_lateral",
        ]

    def test_raises_when_too_few_sessions(self):
        sessions = make_synthetic_sessions(n=2, seed=7)
        with pytest.raises(ValueError, match="need at least k="):
            fit_clusters(sessions, k=8)

    def test_version_stored(self):
        sessions = make_synthetic_sessions(n=40, seed=8)
        model = fit_clusters(sessions, k=3, version=5)
        assert model.version == 5

    def test_writes_artifact_json(self):
        sessions = make_synthetic_sessions(n=40, seed=9)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            fit_clusters(sessions, k=3, artifact_path=path)
            assert os.path.exists(path)
            data = json.loads(open(path).read())
            assert "centroids" in data
            assert "stds" in data
            assert "feature_names" in data
        finally:
            os.unlink(path)

    def test_creates_parent_dirs_for_artifact(self):
        sessions = make_synthetic_sessions(n=40, seed=10)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "deep", "model.json")
            fit_clusters(sessions, k=3, artifact_path=path)
            assert os.path.exists(path)


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------


class TestClusterModelSerialization:
    def test_json_round_trip(self):
        sessions = make_synthetic_sessions(n=40, seed=11)
        model = fit_clusters(sessions, k=3)
        restored = ClusterModel.from_json(model.to_json())
        assert restored.k == model.k
        assert restored.n_sessions == model.n_sessions
        assert restored.feature_names == model.feature_names
        assert restored.centroids == model.centroids

    def test_load_model_from_file(self):
        sessions = make_synthetic_sessions(n=40, seed=12)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            model = fit_clusters(sessions, k=3, artifact_path=path)
            loaded = load_model(path)
            assert loaded.k == model.k
            assert loaded.version == model.version
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# assign_cluster
# ---------------------------------------------------------------------------


class TestAssignCluster:
    def setup_method(self):
        sessions = make_synthetic_sessions(n=60, seed=13)
        self.model = fit_clusters(sessions, k=3)
        self.sessions = sessions

    def test_returns_valid_cluster_index(self):
        fv = compute_features(self.sessions[0].events)
        idx = assign_cluster(fv, self.model)
        assert idx is not None
        assert 0 <= idx < self.model.k

    def test_consistent_assignment(self):
        fv = compute_features(self.sessions[0].events)
        assert assign_cluster(fv, self.model) == assign_cluster(fv, self.model)

    def test_archetypes_assigned_to_different_clusters(self):
        # The 3 synthetic archetypes should separate into different clusters
        # (not guaranteed with random seeds, but true for the chosen seed)
        indices = set()
        for i in range(3):
            fv = compute_features(self.sessions[i].events)
            idx = assign_cluster(fv, self.model)
            indices.add(idx)
        assert len(indices) >= 2, "Expected at least 2 distinct clusters for 3 archetypes"
