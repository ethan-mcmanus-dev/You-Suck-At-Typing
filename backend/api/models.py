"""Pydantic request and response models for the API."""

from uuid import UUID
from typing import Literal
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class KeystrokeEventIn(BaseModel):
    key: str
    keydown_ms: float
    keyup_ms: float


class SessionIn(BaseModel):
    participant_id: UUID
    session_context: Literal["prose", "code"] = "prose"
    events: list[KeystrokeEventIn]

    @field_validator("events")
    @classmethod
    def at_least_one_event(cls, v: list) -> list:
        if len(v) < 10:
            raise ValueError("Session must contain at least 10 events.")
        return v


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class FeatureVectorOut(BaseModel):
    mean_dwell_sfb: float | None
    mean_flight_sfb: float | None
    mean_flight_roll_in: float | None
    mean_flight_roll_out: float | None
    mean_flight_alternation: float | None
    mean_flight_scissor: float | None
    mean_flight_lateral: float | None
    redirect_rate: float | None
    rollover_rate: float | None
    n_keystrokes: int
    n_bigrams_labeled: int


class InsightOut(BaseModel):
    feature: str
    severity: str
    z_score: float
    user_value: float
    cluster_mean: float
    message: str


class InsightReportOut(BaseModel):
    headline: InsightOut | None
    secondary: list[InsightOut]
    positives: list[InsightOut]
    cluster_idx: int
    n_features_observed: int


class SessionOut(BaseModel):
    session_id: UUID
    cluster_idx: int | None
    cluster_version: int
    features: FeatureVectorOut
    insights: InsightReportOut
