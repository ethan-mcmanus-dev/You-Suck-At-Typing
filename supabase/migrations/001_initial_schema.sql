-- 001_initial_schema.sql
-- Run this in the Supabase SQL editor (Dashboard → SQL Editor → New query).

-- ============================================================
-- sessions
-- One row per typing session submitted by a user.
-- participant_id is either a device_id UUID (anonymous) or a
-- Supabase auth user id (authenticated). Both are UUIDs.
-- ============================================================
create table if not exists sessions (
  id               uuid primary key default gen_random_uuid(),
  participant_id   uuid not null,
  session_context  text not null default 'prose',  -- 'prose' | 'code'
  cluster_idx      smallint,                        -- null until aggregation completes
  cluster_version  smallint not null default 1,     -- bumped on re-cluster
  created_at       timestamptz not null default now()
);

create index if not exists sessions_participant_id_idx on sessions(participant_id);
create index if not exists sessions_created_at_idx on sessions(created_at desc);

-- ============================================================
-- session_features
-- The computed 7-feature vector for a session.
-- One-to-one with sessions. Written by the aggregation job.
-- Raw keystrokes are NEVER stored — features only.
-- ============================================================
create table if not exists session_features (
  id                       uuid primary key default gen_random_uuid(),
  session_id               uuid not null references sessions(id) on delete cascade,
  mean_dwell_sfb           real,
  mean_flight_sfb          real,
  mean_flight_roll_in      real,
  mean_flight_roll_out     real,
  mean_flight_alternation  real,
  mean_flight_scissor      real,
  mean_flight_lateral      real,
  redirect_rate            real,
  rollover_rate            real,
  n_keystrokes             integer not null,
  n_bigrams_labeled        integer not null,
  created_at               timestamptz not null default now()
);

create unique index if not exists session_features_session_id_idx on session_features(session_id);

-- ============================================================
-- insights
-- The generated insight report for a session.
-- headline, secondary, and positives stored as JSONB arrays.
-- One-to-one with sessions. Written by the aggregation job.
-- ============================================================
create table if not exists insights (
  id                    uuid primary key default gen_random_uuid(),
  session_id            uuid not null references sessions(id) on delete cascade,
  headline              jsonb,       -- single Insight object or null
  secondary             jsonb not null default '[]',
  positives             jsonb not null default '[]',
  n_features_observed   smallint not null default 0,
  created_at            timestamptz not null default now()
);

create unique index if not exists insights_session_id_idx on insights(session_id);

-- ============================================================
-- Row Level Security
-- participant_id on sessions is compared to the requesting
-- user's auth.uid(). The FastAPI service role bypasses RLS.
-- ============================================================
alter table sessions        enable row level security;
alter table session_features enable row level security;
alter table insights        enable row level security;

-- Sessions: owners can read their own rows
create policy "sessions_select_own" on sessions
  for select using (participant_id = auth.uid());

-- Sessions: insert allowed for any authenticated request
-- (device_id anonymous users are given a Supabase anon auth session)
create policy "sessions_insert_own" on sessions
  for insert with check (participant_id = auth.uid());

-- session_features: readable if the parent session belongs to the user
create policy "features_select_own" on session_features
  for select using (
    exists (
      select 1 from sessions s
      where s.id = session_id
      and s.participant_id = auth.uid()
    )
  );

-- insights: readable if the parent session belongs to the user
create policy "insights_select_own" on insights
  for select using (
    exists (
      select 1 from sessions s
      where s.id = session_id
      and s.participant_id = auth.uid()
    )
  );

-- Service role (used by FastAPI) bypasses RLS automatically.
-- No additional policies needed for service-role writes.
