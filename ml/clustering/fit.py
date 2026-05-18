"""
KMeans clustering pipeline for biomechanical typing profiles.

Fits k=8 clusters on the 7-feature vector matrix (rollover_rate excluded
from clustering — it's unreliable in browser environments at <5ms resolution).

The 7 features used:
  mean_dwell_sfb, mean_flight_sfb, mean_flight_roll_in, mean_flight_roll_out,
  mean_flight_alternation, mean_flight_scissor, mean_flight_lateral

redirect_rate and rollover_rate are stored in the model artifact for
informational use but are NOT included in cluster distance calculations.

Typical usage:
    from ml.data import make_synthetic_sessions
    from ml.clustering import fit_clusters

    sessions = make_synthetic_sessions(n=300)
    model = fit_clusters(sessions, artifact_path="model_artifacts/clusters_v1.json")
"""

import json
import math
import os
import random
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from data.protocol import SessionIterator, RawSession
from features import compute_features, FeatureVector


# The 7 features used for clustering distance calculations.
# Order must match _FEATURE_NAMES below and the centroid vectors.
_CLUSTER_FEATURE_NAMES: list[str] = [
    "mean_dwell_sfb",
    "mean_flight_sfb",
    "mean_flight_roll_in",
    "mean_flight_roll_out",
    "mean_flight_alternation",
    "mean_flight_scissor",
    "mean_flight_lateral",
]

_N_CLUSTERS = 8
_KMEANS_MAX_ITER = 300
_KMEANS_N_INIT = 10
_KMEANS_TOL = 1e-4


@dataclass
class ClusterModel:
    """Serializable cluster model artifact.

    centroids: list of k centroid vectors (each a list of 7 floats, in
               the order of _CLUSTER_FEATURE_NAMES).
    stds:      list of k per-feature standard deviations (same shape as
               centroids). Used for z-score deviation computation downstream.
    means:     global per-feature means used for normalization.
    scale:     global per-feature stds used for normalization.
    feature_names: the 7 feature names in vector order.
    n_sessions: number of sessions used to fit the model.
    k:          number of clusters.
    version:    monotonically increasing integer; increment when re-clustering.
    """

    centroids: list[list[float]]
    stds: list[list[float]]
    means: list[float]
    scale: list[float]
    feature_names: list[str]
    n_sessions: int
    k: int
    version: int = 1

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "ClusterModel":
        return cls(**json.loads(text))


def _extract_row(fv: FeatureVector) -> list[float] | None:
    """Extract the 7-feature row from a FeatureVector.

    Returns None if any clustering feature is missing (None), which means
    not enough bigrams of that class were observed — the session is dropped.
    """
    values = [getattr(fv, name) for name in _CLUSTER_FEATURE_NAMES]
    if any(v is None for v in values):
        return None
    return values  # type: ignore[return-value]


def _standardize(
    matrix: list[list[float]],
) -> tuple[list[list[float]], list[float], list[float]]:
    """Z-score normalize each column. Returns (normalized, means, stds)."""
    n_features = len(matrix[0])
    col_means: list[float] = []
    col_stds: list[float] = []

    for j in range(n_features):
        col = [matrix[i][j] for i in range(len(matrix))]
        mu = statistics.mean(col)
        sigma = statistics.stdev(col) if len(col) > 1 else 1.0
        if sigma == 0.0:
            sigma = 1.0
        col_means.append(mu)
        col_stds.append(sigma)

    normalized = [
        [(matrix[i][j] - col_means[j]) / col_stds[j] for j in range(n_features)]
        for i in range(len(matrix))
    ]
    return normalized, col_means, col_stds


def _euclidean(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _kmeans(
    matrix: list[list[float]],
    k: int,
    max_iter: int,
    n_init: int,
    tol: float,
    seed: int = 0,
) -> tuple[list[list[float]], list[int]]:
    """Pure-Python KMeans. Returns (centroids, labels).

    If scikit-learn is available we use it; otherwise falls back to this
    implementation so the module works without sklearn installed.
    """
    try:
        from sklearn.cluster import KMeans
        import numpy as np

        km = KMeans(n_clusters=k, max_iter=max_iter, n_init=n_init, tol=tol,
                    random_state=seed)
        arr = np.array(matrix)
        km.fit(arr)
        centroids = km.cluster_centers_.tolist()
        labels = km.labels_.tolist()
        return centroids, labels
    except ImportError:
        pass

    # Pure-Python fallback (Lloyd's algorithm, single init)
    rng = random.Random(seed)
    n = len(matrix)
    n_features = len(matrix[0])

    indices = rng.sample(range(n), k)
    centroids = [matrix[i][:] for i in indices]

    labels = [0] * n
    for _ in range(max_iter):
        new_labels = [
            min(range(k), key=lambda c, row=matrix[i]: _euclidean(row, centroids[c]))
            for i in range(n)
        ]

        if new_labels == labels:
            break
        labels = new_labels

        new_centroids: list[list[float]] = []
        for c in range(k):
            members = [matrix[i] for i in range(n) if labels[i] == c]
            if not members:
                new_centroids.append(centroids[c])
            else:
                new_centroids.append(
                    [sum(row[j] for row in members) / len(members) for j in range(n_features)]
                )

        shift = max(_euclidean(centroids[c], new_centroids[c]) for c in range(k))
        centroids = new_centroids
        if shift < tol:
            break

    return centroids, labels


def _compute_cluster_stds(
    matrix: list[list[float]],
    labels: list[int],
    centroids: list[list[float]],
    k: int,
) -> list[list[float]]:
    """Per-cluster, per-feature standard deviation in original (pre-norm) space."""
    n_features = len(matrix[0])
    stds: list[list[float]] = []
    for c in range(k):
        members = [matrix[i] for i in range(len(matrix)) if labels[i] == c]
        if len(members) < 2:
            stds.append([1.0] * n_features)
        else:
            col_stds = [
                statistics.stdev(row[j] for row in members)
                for j in range(n_features)
            ]
            stds.append([max(s, 1e-6) for s in col_stds])
    return stds


def fit_clusters(
    sessions: Sequence[RawSession] | SessionIterator,
    k: int = _N_CLUSTERS,
    artifact_path: str | os.PathLike | None = None,
    version: int = 1,
    seed: int = 42,
) -> ClusterModel:
    """Compute features for each session, normalize, and fit KMeans.

    Sessions with fewer than 100 keystrokes or with any missing clustering
    feature are silently skipped.

    Args:
        sessions:      iterable of RawSession objects
        k:             number of clusters
        artifact_path: if provided, writes the ClusterModel JSON here
        version:       cluster_version tag stored in the artifact
        seed:          random seed for KMeans

    Returns:
        ClusterModel with centroids, per-cluster stds, and normalization params.

    Raises:
        ValueError: if fewer than k sessions produce valid feature vectors.
    """
    raw_rows: list[list[float]] = []

    for session in sessions:
        try:
            fv = compute_features(session.events)
        except ValueError:
            continue
        row = _extract_row(fv)
        if row is None:
            continue
        raw_rows.append(row)

    if len(raw_rows) < k:
        raise ValueError(
            f"Only {len(raw_rows)} sessions produced complete feature vectors; "
            f"need at least k={k}."
        )

    normalized, col_means, col_stds = _standardize(raw_rows)

    centroids_norm, labels = _kmeans(
        normalized,
        k=k,
        max_iter=_KMEANS_MAX_ITER,
        n_init=_KMEANS_N_INIT,
        tol=_KMEANS_TOL,
        seed=seed,
    )

    # Denormalize centroids back to original feature space
    n_features = len(_CLUSTER_FEATURE_NAMES)
    centroids_orig = [
        [centroids_norm[c][j] * col_stds[j] + col_means[j] for j in range(n_features)]
        for c in range(k)
    ]

    cluster_stds = _compute_cluster_stds(raw_rows, labels, centroids_orig, k)

    model = ClusterModel(
        centroids=centroids_orig,
        stds=cluster_stds,
        means=col_means,
        scale=col_stds,
        feature_names=_CLUSTER_FEATURE_NAMES,
        n_sessions=len(raw_rows),
        k=k,
        version=version,
    )

    if artifact_path is not None:
        path = Path(artifact_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(model.to_json(), encoding="utf-8")

    return model


def load_model(artifact_path: str | os.PathLike) -> ClusterModel:
    """Load a ClusterModel from a JSON artifact file."""
    return ClusterModel.from_json(Path(artifact_path).read_text(encoding="utf-8"))


def assign_cluster(
    fv: FeatureVector,
    model: ClusterModel,
) -> int | None:
    """Assign a FeatureVector to the nearest cluster centroid.

    Returns the cluster index (0-based), or None if any clustering feature
    is missing.
    """
    row = _extract_row(fv)
    if row is None:
        return None

    normalized = [
        (row[j] - model.means[j]) / model.scale[j]
        for j in range(len(_CLUSTER_FEATURE_NAMES))
    ]

    # Normalize centroids for comparison
    norm_centroids = [
        [(model.centroids[c][j] - model.means[j]) / model.scale[j]
         for j in range(len(_CLUSTER_FEATURE_NAMES))]
        for c in range(model.k)
    ]

    return min(range(model.k), key=lambda c: _euclidean(normalized, norm_centroids[c]))
