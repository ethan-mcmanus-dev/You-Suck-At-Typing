"""
Fit the initial KMeans cluster model and write model_artifacts/clusters_v1.json.

Run from the repo root:
    python ml/scripts/fit_initial_model.py

Uses synthetic data until the Aalto dataset is available. Swap in
AaltoSessions once the CSV file is downloaded:

    from ml.data.aalto import AaltoSessions
    sessions = AaltoSessions("path/to/aalto.csv")
    model = fit_clusters(sessions, k=8, artifact_path=artifact_path, version=1)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.synthetic import make_synthetic_sessions
from clustering.fit import fit_clusters

ARTIFACT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "model_artifacts", "clusters_v1.json"
)

if __name__ == "__main__":
    print("Generating synthetic sessions...")
    sessions = make_synthetic_sessions(n=300, seed=42)
    print(f"  {len(sessions)} sessions generated")

    print("Fitting k=8 clusters...")
    model = fit_clusters(sessions, k=8, artifact_path=ARTIFACT_PATH, version=1)

    print(f"  Fit on {model.n_sessions} sessions with valid feature vectors")
    print(f"  Artifact written to: {os.path.abspath(ARTIFACT_PATH)}")
    print()
    print("Cluster centroids (mean_flight_sfb, ms):")
    sfb_idx = model.feature_names.index("mean_flight_sfb")
    for i, centroid in enumerate(model.centroids):
        print(f"  Cluster {i}: {centroid[sfb_idx]:.1f} ms sfb flight")
