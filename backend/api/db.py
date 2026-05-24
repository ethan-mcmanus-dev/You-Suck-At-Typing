"""Supabase client — service role for all backend writes."""

import os
from functools import lru_cache
from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def get_device_features(participant_id: str) -> list[dict]:
    """Return all stored feature rows for a device (participant), oldest first."""
    client = get_client()
    sessions = (
        client.table("sessions")
        .select("id")
        .eq("participant_id", participant_id)
        .execute()
    )
    ids = [r["id"] for r in sessions.data]
    if not ids:
        return []
    rows = (
        client.table("session_features")
        .select("*")
        .in_("session_id", ids)
        .execute()
    )
    return rows.data
