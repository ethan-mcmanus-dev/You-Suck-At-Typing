'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { SessionResult } from '@/lib/api';
import RadarChart from '@/components/RadarChart';
import {
  CLUSTER_PROFILES,
  CLUSTER_CENTROIDS,
  SPEED_ORDER,
} from '@/lib/clusters';

const MIN_SESSIONS_FOR_PROFILE = 6;

// Plain-English feature names + what they actually mean
const FEATURE_META: { key: string; label: string; tip: string }[] = [
  { key: 'mean_dwell_sfb',        label: 'Same-finger hold',   tip: 'How long you hold a key before pressing another key on the same finger (e.g. "ed" both use left middle finger)' },
  { key: 'mean_flight_sfb',       label: 'Same-finger gap',    tip: 'Time between releasing one key and pressing the next when both use the same finger — these bigrams are inherently slow' },
  { key: 'mean_flight_roll_in',   label: 'Inward roll',        tip: 'Typing two keys on the same hand moving toward the index finger — generally your fastest movement (e.g. typing "in")' },
  { key: 'mean_flight_roll_out',  label: 'Outward roll',       tip: 'Typing two keys on the same hand moving toward the pinky — slightly slower than inward (e.g. typing "we")' },
  { key: 'mean_flight_alternation', label: 'Hand switch',      tip: 'Time to move from a key on one hand to a key on the other — usually fast and natural' },
  { key: 'mean_flight_scissor',   label: 'Row jump',           tip: 'Pressing keys that are two rows apart on adjacent fingers — mechanically awkward, tends to be slow' },
  { key: 'mean_flight_lateral',   label: 'Pinky reach',        tip: 'Reaching to the outermost columns (Q, A, Z side or P, ; side) — awkward for most typists' },
];

// Average flight speed (ms) for each cluster, precomputed from centroids
// = mean of the 6 non-SFB-dwell features
const CLUSTER_AVG_SPEED: Record<number, number> = {
  0: 260, 1: 80, 2: 60, 3: 151, 4: 347, 5: 187, 6: 231, 7: 120,
};

function avgSpeed(features: Record<string, number | null>): number | null {
  const keys = [
    'mean_flight_sfb', 'mean_flight_roll_in', 'mean_flight_roll_out',
    'mean_flight_alternation', 'mean_flight_scissor', 'mean_flight_lateral',
  ];
  const vals = keys.map(k => features[k]).filter((v): v is number => v != null);
  return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
}

export default function ResultsView({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const [result, setResult] = useState<SessionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const cached = sessionStorage.getItem(`ysat_result_${sessionId}`);
    if (cached) {
      try { setResult(JSON.parse(cached)); return; } catch {}
    }
    const api = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
    fetch(`${api}/session/${sessionId}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(setResult)
      .catch(() => setError('Could not load results. The session may still be processing — try refreshing.'));
  }, [sessionId]);

  if (error) {
    return (
      <div className="text-center space-y-4 py-16">
        <p className="text-red-400 text-sm">{error}</p>
        <button onClick={() => router.push('/')} className="text-neutral-400 text-xs underline underline-offset-2 hover:text-neutral-100">Try again</button>
      </div>
    );
  }
  if (!result) {
    return <div className="text-center py-16 text-neutral-500 text-sm">Loading your results…</div>;
  }

  const n = result.n_sessions ?? 1;
  const profileReady = n >= MIN_SESSIONS_FOR_PROFILE;
  const displayCluster = result.aggregated_cluster_idx ?? result.cluster_idx;
  const profile = displayCluster != null ? CLUSTER_PROFILES[displayCluster] : null;
  const centroid = displayCluster != null ? CLUSTER_CENTROIDS[displayCluster] : null;
  const { insights, features } = result;

  const userRadarValues = [
    features.mean_dwell_sfb,
    features.mean_flight_sfb,
    features.mean_flight_roll_in,
    features.mean_flight_roll_out,
    features.mean_flight_alternation,
    features.mean_flight_scissor,
    features.mean_flight_lateral,
  ];

  const userSpeed = avgSpeed(features);

  // Speed comparison number line: range 40–380ms
  const SPEED_MIN = 40, SPEED_MAX = 380;
  const toPct = (ms: number) => Math.max(0, Math.min(100, (ms - SPEED_MIN) / (SPEED_MAX - SPEED_MIN) * 100));

  return (
    <div className="space-y-8">

      {/* Cluster identity */}
      <div className="space-y-2">
        {profile ? (
          <>
            <div className="flex items-baseline gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{profile.name}</h1>
              <span className="text-sm text-neutral-500">#{profile.speed_rank} of 8</span>
            </div>
            <p className="text-neutral-400 text-sm leading-relaxed max-w-lg">{profile.description}</p>
          </>
        ) : (
          <h1 className="text-2xl font-bold tracking-tight">Your Results</h1>
        )}
        <p className="text-xs text-neutral-600">
          {profileReady
            ? `Averaged over ${n} sessions`
            : `Session ${n} of ${MIN_SESSIONS_FOR_PROFILE} — keep going for a stable profile`}
        </p>
      </div>

      {/* Progress indicator or full profile */}
      {!profileReady ? (
        <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-5 space-y-3">
          <p className="text-sm text-neutral-300">
            Your placement may shift until you have more data. Complete {MIN_SESSIONS_FOR_PROFILE - n} more {MIN_SESSIONS_FOR_PROFILE - n === 1 ? 'test' : 'tests'} to unlock your full profile.
          </p>
          <div className="flex gap-1">
            {Array.from({ length: MIN_SESSIONS_FOR_PROFILE }, (_, i) => (
              <div key={i} className={`h-1.5 flex-1 rounded-full ${i < n ? 'bg-neutral-300' : 'bg-neutral-700'}`} />
            ))}
          </div>
        </div>
      ) : (
        /* Speed spectrum — only shown once profile is stable */
        <div className="space-y-2">
          <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">Speed ranking</p>
          <div className="flex gap-1">
            {SPEED_ORDER.map((idx) => {
              const isUser = idx === displayCluster;
              const p = CLUSTER_PROFILES[idx];
              return (
                <div
                  key={idx}
                  title={p.name}
                  className={`flex-1 rounded py-1.5 text-center text-xs font-mono transition-colors ${
                    isUser ? 'bg-neutral-100 text-neutral-900 font-semibold' : 'bg-neutral-800 text-neutral-500'
                  }`}
                >
                  {isUser ? p.name.split(' ')[0] : ''}
                </div>
              );
            })}
          </div>
          <div className="flex justify-between text-xs text-neutral-600">
            <span>Fastest</span><span>Slowest</span>
          </div>
        </div>
      )}

      {/* Speed comparison number line — always shown */}
      <div className="space-y-2">
        <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">
          Average transition speed
        </p>
        <div className="relative h-9">
          {/* Track */}
          <div className="absolute top-4 left-0 right-0 h-px bg-neutral-700" />

          {/* Cluster dots */}
          {SPEED_ORDER.map((idx) => {
            const spd = CLUSTER_AVG_SPEED[idx];
            const pct = toPct(spd);
            const isUser = idx === displayCluster;
            return (
              <div
                key={idx}
                className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 rounded-full transition-all ${
                  isUser ? 'w-3.5 h-3.5 bg-neutral-100 ring-2 ring-neutral-100/30' : 'w-2 h-2 bg-neutral-600'
                }`}
                style={{ left: `${pct}%` }}
                title={`${CLUSTER_PROFILES[idx].name}: ${spd}ms avg`}
              />
            );
          })}

          {/* User's actual measured speed */}
          {userSpeed != null && (
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-amber-400/70"
              style={{ left: `${toPct(userSpeed)}%` }}
              title={`Your measured speed: ${Math.round(userSpeed)}ms`}
            />
          )}
        </div>
        <div className="flex justify-between text-xs text-neutral-600">
          <span>Fast (40ms)</span>
          {userSpeed != null && (
            <span className="text-amber-400/80">
              you: {Math.round(userSpeed)}ms
            </span>
          )}
          <span>Slow (380ms)</span>
        </div>
        <p className="text-xs text-neutral-700">
          Dots = cluster averages. Amber line = your measured this session. Lower ms is faster.
        </p>
      </div>

      {/* Radar chart — only after profile is stable */}
      {profileReady && centroid && (
        <div className="space-y-2">
          <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">Your feature profile</p>
          <div className="flex gap-4 text-xs text-neutral-600 mb-1">
            <span className="flex items-center gap-1"><span className="inline-block w-5 border-t-2 border-neutral-300" />you</span>
            <span className="flex items-center gap-1"><span className="inline-block w-5 border-t-2 border-dashed border-neutral-500" />cluster avg</span>
          </div>
          <p className="text-xs text-neutral-700">More area = relatively faster at that movement type</p>
          <RadarChart userValues={userRadarValues} centroidValues={centroid} />
        </div>
      )}

      {/* Insights */}
      <div className="space-y-3">
        {insights.headline ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-1">
            <div className="text-xs font-medium text-amber-400 uppercase tracking-wider">Top finding</div>
            <p className="text-neutral-100 text-sm leading-relaxed">{insights.headline.message}</p>
          </div>
        ) : (
          <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-4">
            <p className="text-neutral-400 text-sm">Your typing looks typical for your cluster. No standout patterns this session.</p>
          </div>
        )}

        {insights.secondary.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">Also notable</p>
            {insights.secondary.map((ins, i) => (
              <div key={i} className="rounded-lg border border-neutral-700 bg-neutral-900 p-3">
                <p className="text-neutral-300 text-sm leading-relaxed">{ins.message}</p>
              </div>
            ))}
          </div>
        )}

        {insights.positives.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">Strengths</p>
            {insights.positives.map((ins, i) => (
              <div key={i} className="rounded-lg border border-emerald-700/30 bg-emerald-900/10 p-3">
                <p className="text-neutral-300 text-sm leading-relaxed">{ins.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Feature breakdown with plain-English labels and tooltips */}
      <div className="space-y-2">
        <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">Breakdown (ms · lower = faster)</p>
        <div className="rounded-xl border border-neutral-800 divide-y divide-neutral-800">
          {FEATURE_META.map(({ key, label, tip }) => {
            const val = features[key as keyof typeof features] as number | null;
            return (
              <div key={key} className="flex justify-between items-center px-4 py-2.5 group">
                <div className="space-y-0.5">
                  <span className="text-sm text-neutral-400">{label}</span>
                  <p className="text-xs text-neutral-700 group-hover:text-neutral-500 transition-colors max-w-xs">{tip}</p>
                </div>
                <span className="text-sm font-mono text-neutral-200 shrink-0 ml-4">
                  {val != null ? `${val.toFixed(0)} ms` : '—'}
                </span>
              </div>
            );
          })}
        </div>
        <p className="text-xs text-neutral-700">
          {features.n_keystrokes} keystrokes · {features.n_bigrams_labeled} categorized pairs · cluster #{displayCluster}
        </p>
      </div>

      <button
        onClick={() => router.push('/')}
        className="text-sm text-neutral-400 hover:text-neutral-100 transition-colors underline underline-offset-2"
      >
        Type again
      </button>
    </div>
  );
}
