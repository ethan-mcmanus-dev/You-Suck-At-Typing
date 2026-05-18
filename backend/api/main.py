"""
FastAPI application.

Startup: loads the cluster model from MODEL_ARTIFACT_PATH once into memory.
All feature computation and insight generation happen in-request — no queue,
no worker process. Fast enough for a typing session (< 200ms on warm server).
"""

import os
import sys
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Resolve sibling package paths when running from repo root via:
#   PYTHONPATH=backend:ml uvicorn backend.api.main:app
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
for _p in [os.path.join(_ROOT, "backend"), os.path.join(_ROOT, "ml")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from features import KeystrokeEvent, compute_features
from insights import compute_insights, Insight, InsightReport
from api.db import get_client
from api.models import (
    InsightOut,
    InsightReportOut,
    FeatureVectorOut,
    SessionIn,
    SessionOut,
)

# Imported here so the type annotation resolves after sys.path is patched
from clustering.fit import ClusterModel, assign_cluster, load_model


# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------


class AppState:
    model: ClusterModel


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    artifact_path = os.environ.get(
        "MODEL_ARTIFACT_PATH",
        os.path.join(_ROOT, "model_artifacts", "clusters_v1.json"),
    )
    state.model = load_model(artifact_path)
    print(
        f"Loaded cluster model v{state.model.version} "
        f"({state.model.k} clusters, {state.model.n_sessions} sessions)"
    )
    yield


app = FastAPI(title="You Suck At Typing API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insight_to_out(ins: Insight) -> InsightOut:
    return InsightOut(
        feature=ins.feature,
        severity=ins.severity,
        z_score=round(ins.z_score, 3),
        user_value=round(ins.user_value, 2),
        cluster_mean=round(ins.cluster_mean, 2),
        message=ins.message,
    )


def _report_to_out(report: InsightReport) -> InsightReportOut:
    return InsightReportOut(
        headline=_insight_to_out(report.headline) if report.headline else None,
        secondary=[_insight_to_out(i) for i in report.secondary],
        positives=[_insight_to_out(i) for i in report.positives],
        cluster_idx=report.cluster_idx,
        n_features_observed=report.n_features_observed,
    )


def _persist_session(session_id: str, body: SessionIn, cluster_idx: int, fv, report: InsightReport):
    """Write session, features, and insights to Supabase. Fire-and-forget."""
    db = get_client()

    db.table("sessions").insert({
        "id": session_id,
        "participant_id": str(body.participant_id),
        "session_context": body.session_context,
        "cluster_idx": cluster_idx,
        "cluster_version": state.model.version,
    }).execute()

    db.table("session_features").insert({
        "session_id": session_id,
        "mean_dwell_sfb": fv.mean_dwell_sfb,
        "mean_flight_sfb": fv.mean_flight_sfb,
        "mean_flight_roll_in": fv.mean_flight_roll_in,
        "mean_flight_roll_out": fv.mean_flight_roll_out,
        "mean_flight_alternation": fv.mean_flight_alternation,
        "mean_flight_scissor": fv.mean_flight_scissor,
        "mean_flight_lateral": fv.mean_flight_lateral,
        "redirect_rate": fv.redirect_rate,
        "rollover_rate": fv.rollover_rate,
        "n_keystrokes": fv.n_keystrokes,
        "n_bigrams_labeled": fv.n_bigrams_labeled,
    }).execute()

    headline_dict = asdict(report.headline) if report.headline else None
    db.table("insights").insert({
        "session_id": session_id,
        "headline": headline_dict,
        "secondary": [asdict(i) for i in report.secondary],
        "positives": [asdict(i) for i in report.positives],
        "n_features_observed": report.n_features_observed,
    }).execute()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {"status": "ok", "model_version": state.model.version}


@app.post("/session", response_model=SessionOut)
def create_session(body: SessionIn, background_tasks: BackgroundTasks):
    # Map request events to KeystrokeEvent
    events = [
        KeystrokeEvent(key=e.key, keydown_ms=e.keydown_ms, keyup_ms=e.keyup_ms)
        for e in body.events
    ]

    # Compute features — raises ValueError if < 100 valid keystrokes
    try:
        fv = compute_features(events)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Assign to cluster
    cluster_idx = assign_cluster(fv, state.model)
    if cluster_idx is None:
        raise HTTPException(
            status_code=422,
            detail="Session has too few bigrams to assign a cluster. Type more varied text.",
        )

    # Generate insights
    report = compute_insights(fv, state.model, cluster_idx)

    # Generate a stable session ID
    import uuid
    session_id = str(uuid.uuid4())

    # Persist asynchronously — user gets the response immediately
    background_tasks.add_task(
        _persist_session, session_id, body, cluster_idx, fv, report
    )

    return SessionOut(
        session_id=session_id,
        cluster_idx=cluster_idx,
        cluster_version=state.model.version,
        features=FeatureVectorOut(**{
            "mean_dwell_sfb": fv.mean_dwell_sfb,
            "mean_flight_sfb": fv.mean_flight_sfb,
            "mean_flight_roll_in": fv.mean_flight_roll_in,
            "mean_flight_roll_out": fv.mean_flight_roll_out,
            "mean_flight_alternation": fv.mean_flight_alternation,
            "mean_flight_scissor": fv.mean_flight_scissor,
            "mean_flight_lateral": fv.mean_flight_lateral,
            "redirect_rate": fv.redirect_rate,
            "rollover_rate": fv.rollover_rate,
            "n_keystrokes": fv.n_keystrokes,
            "n_bigrams_labeled": fv.n_bigrams_labeled,
        }),
        insights=_report_to_out(report),
    )


@app.get("/session/{session_id}", response_model=SessionOut)
def get_session(session_id: str):
    db = get_client()

    session_row = (
        db.table("sessions")
        .select("*")
        .eq("id", session_id)
        .maybe_single()
        .execute()
    )
    if not session_row.data:
        raise HTTPException(status_code=404, detail="Session not found.")

    features_row = (
        db.table("session_features")
        .select("*")
        .eq("session_id", session_id)
        .maybe_single()
        .execute()
    )
    insights_row = (
        db.table("insights")
        .select("*")
        .eq("session_id", session_id)
        .maybe_single()
        .execute()
    )

    if not features_row.data or not insights_row.data:
        raise HTTPException(status_code=404, detail="Session results not yet available.")

    f = features_row.data
    ins = insights_row.data

    def _row_to_insight(d: dict) -> InsightOut:
        return InsightOut(**d)

    return SessionOut(
        session_id=session_row.data["id"],
        cluster_idx=session_row.data["cluster_idx"],
        cluster_version=session_row.data["cluster_version"],
        features=FeatureVectorOut(**{k: f[k] for k in FeatureVectorOut.model_fields}),
        insights=InsightReportOut(
            headline=_row_to_insight(ins["headline"]) if ins["headline"] else None,
            secondary=[_row_to_insight(i) for i in (ins["secondary"] or [])],
            positives=[_row_to_insight(i) for i in (ins["positives"] or [])],
            cluster_idx=session_row.data["cluster_idx"] or 0,
            n_features_observed=ins["n_features_observed"],
        ),
    )
