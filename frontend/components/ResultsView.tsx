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

// Feature keys ordered to match CLUSTER_CENTROIDS arrays
const FEATURE_KEYS = [
  'mean_dwell_sfb',
  'mean_flight_sfb',
  'mean_flight_roll_in',
  'mean_flight_roll_out',
  'mean_flight_alternation',
  'mean_flight_scissor',
  'mean_flight_lateral',
] as const;

type FeatureKey = typeof FEATURE_KEYS[number];

const FEATURE_META: Record<FeatureKey, { label: string; what: string; tip: string; words: string[] }> = {
  mean_dwell_sfb: {
    label: 'Same-finger hold',
    what: 'A same-finger bigram (SFB) is when two consecutive keys are typed by the same finger — on QWERTY, "e" and "d" both use the left middle finger. This measures how long you hold the first key before releasing it.',
    tip: 'Release each key immediately — holding it down while preparing for the next same-finger key creates tension. Stay relaxed.',
    words: ['under', 'desk', 'link', 'swim', 'loin', 'kind'],
  },
  mean_flight_sfb: {
    label: 'Same-finger transitions',
    what: 'Two consecutive keys pressed by the same finger. The finger can\'t start moving to the second key until it\'s finished with the first, making these the slowest bigrams on the keyboard.',
    tip: 'Drill these specific patterns slowly until the motor path feels automatic, then build speed. There\'s no trick here — it just takes repetition.',
    words: ['under', 'edge', 'swam', 'lore', 'loin', 'kindle'],
  },
  mean_flight_roll_in: {
    label: 'Inward rolls',
    what: 'Both keys are on the same hand, and the second key is closer to your index finger than the first (moving inward). Example: "s" then "d" on the left hand. The natural curl of your fingers makes this the fastest type of hand movement.',
    tip: 'If inward rolls are slow, you may be lifting your wrist between keys. Keep your hands flat and let your fingers do the movement — don\'t pick up the whole hand.',
    words: ['last', 'fast', 'rest', 'best', 'test', 'desk'],
  },
  mean_flight_roll_out: {
    label: 'Outward rolls',
    what: 'Both keys on the same hand, but the second key is closer to your pinky (moving outward). Example: "d" then "s". Going outward is less natural than inward since your fingers prefer to curl inward.',
    tip: 'Keep the hand stable and let the finger extend outward — don\'t rotate your wrist to compensate. Practice staying relaxed on the outward extension.',
    words: ['west', 'few', 'our', 'out', 'dew', 'sew'],
  },
  mean_flight_alternation: {
    label: 'Hand alternation',
    what: 'One key typed with the left hand, the next with the right (or vice versa). Because both hands can prepare simultaneously, alternation is typically your fastest transition type.',
    tip: 'Alternating hands should feel effortless. Keep both hands hovering and ready — don\'t let one hand rest while the other works.',
    words: ['right', 'world', 'their', 'about', 'those', 'while'],
  },
  mean_flight_scissor: {
    label: 'Row jumps',
    what: 'Two adjacent fingers pressing keys that are two rows apart — like your index on the bottom row ("b") immediately followed by your middle on the top row ("r"). The fingers cross in a "scissor" motion, which is mechanically awkward.',
    tip: 'Minimize wrist movement and reach with just the finger. Build this motor pattern slowly — going fast with bad form locks in bad habits.',
    words: ['branch', 'number', 'brown', 'verb', 'urban', 'bring'],
  },
  mean_flight_lateral: {
    label: 'Pinky reach',
    what: 'Any key in the outermost columns: Q, A, Z on the left or P, ; on the right. These require the pinky to stretch significantly outward from its home position on A or ;.',
    tip: 'Keep your wrist anchored and extend the pinky only, then return immediately to home row. Avoid letting your whole hand drift toward the outer column.',
    words: ['please', 'people', 'place', 'apple', 'always', 'polar'],
  },
};

function getWeaknesses(features: Record<string, number | null>, centroid: number[]) {
  return FEATURE_KEYS
    .map((key, idx) => {
      const val = features[key] as number | null;
      if (val == null) return null;
      const delta = val - centroid[idx]; // positive = user is slower than centroid
      return { key, val, centroidVal: centroid[idx], delta };
    })
    .filter((x): x is NonNullable<typeof x> => x !== null)
    .sort((a, b) => b.delta - a.delta)
    .slice(0, 2);
}

function getStrengths(features: Record<string, number | null>, centroid: number[]) {
  return FEATURE_KEYS
    .map((key, idx) => {
      const val = features[key] as number | null;
      if (val == null) return null;
      const delta = val - centroid[idx];
      return { key, val, centroidVal: centroid[idx], delta };
    })
    .filter((x): x is NonNullable<typeof x> => x !== null && x.delta < -20)
    .sort((a, b) => a.delta - b.delta)
    .slice(0, 1);
}

function avgSpeed(features: Record<string, number | null>): number | null {
  const keys: FeatureKey[] = [
    'mean_flight_sfb', 'mean_flight_roll_in', 'mean_flight_roll_out',
    'mean_flight_alternation', 'mean_flight_scissor', 'mean_flight_lateral',
  ];
  const vals = keys.map(k => features[k]).filter((v): v is number => v != null);
  return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
}

// Precomputed cluster average speeds (ms) for the number line
const CLUSTER_AVG_SPEED: Record<number, number> = {
  0: 260, 1: 80, 2: 60, 3: 151, 4: 347, 5: 187, 6: 231, 7: 120,
};

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
    return <div className="text-center py-16 text-neutral-500 text-sm">Loading…</div>;
  }

  const n = result.n_sessions ?? 1;
  const profileReady = n >= MIN_SESSIONS_FOR_PROFILE;
  const displayCluster = result.aggregated_cluster_idx ?? result.cluster_idx;
  const profile = displayCluster != null ? CLUSTER_PROFILES[displayCluster] : null;
  const centroid = displayCluster != null ? CLUSTER_CENTROIDS[displayCluster] : null;
  const { features } = result;

  const weaknesses = centroid ? getWeaknesses(features, centroid) : [];
  const strengths = centroid ? getStrengths(features, centroid) : [];

  // Next faster cluster
  const userSpeedIdx = displayCluster != null ? SPEED_ORDER.indexOf(displayCluster) : -1;
  const nextFasterCluster = userSpeedIdx > 0 ? SPEED_ORDER[userSpeedIdx - 1] : null;
  const nextFasterProfile = nextFasterCluster != null ? CLUSTER_PROFILES[nextFasterCluster] : null;
  const nextFasterCentroid = nextFasterCluster != null ? CLUSTER_CENTROIDS[nextFasterCluster] : null;

  // Features with biggest gap between user's cluster centroid and next cluster's centroid
  const clusterGaps = (centroid && nextFasterCentroid)
    ? FEATURE_KEYS
        .map((key, idx) => ({
          key,
          gap: centroid[idx] - nextFasterCentroid[idx], // positive = next cluster is faster
        }))
        .filter(x => x.gap > 15)
        .sort((a, b) => b.gap - a.gap)
        .slice(0, 2)
    : [];

  const userSpeed = avgSpeed(features);
  const SPEED_MIN = 40, SPEED_MAX = 380;
  const toPct = (ms: number) => Math.max(0, Math.min(100, (ms - SPEED_MIN) / (SPEED_MAX - SPEED_MIN) * 100));

  const userRadarValues = FEATURE_KEYS.map(k => features[k] as number | null);

  return (
    <div className="space-y-8">

      {/* Identity */}
      <div className="space-y-1">
        {profile ? (
          <div className="flex items-baseline gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{profile.name}</h1>
            <span className="text-sm text-neutral-500">rank {profile.speed_rank} of 8</span>
          </div>
        ) : (
          <h1 className="text-2xl font-bold tracking-tight">Your Results</h1>
        )}
        <p className="text-xs text-neutral-600">
          {profileReady
            ? `Stable profile · ${n} sessions averaged`
            : `Session ${n} of ${MIN_SESSIONS_FOR_PROFILE} — ${MIN_SESSIONS_FOR_PROFILE - n} more to lock in your profile`}
        </p>
        {profile && (
          <p className="text-neutral-400 text-sm leading-relaxed max-w-lg pt-1">{profile.description}</p>
        )}
      </div>

      {/* Progress bar (pre-stable) */}
      {!profileReady && (
        <div className="flex gap-1">
          {Array.from({ length: MIN_SESSIONS_FOR_PROFILE }, (_, i) => (
            <div key={i} className={`h-1 flex-1 rounded-full ${i < n ? 'bg-neutral-300' : 'bg-neutral-800'}`} />
          ))}
        </div>
      )}

      {/* What to practice */}
      {centroid && (
        <div className="space-y-3">
          <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">What to practice</p>
          {weaknesses.map(({ key, val, centroidVal, delta }) => {
            const meta = FEATURE_META[key];
            const isBehind = delta > 10;
            return (
              <div key={key} className="rounded-xl border border-neutral-800 bg-neutral-900 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-neutral-200">{meta.label}</span>
                  <span className={`text-xs font-mono ${isBehind ? 'text-red-400/70' : 'text-emerald-400/70'}`}>
                    you {Math.round(val)}ms · avg {Math.round(centroidVal)}ms
                  </span>
                </div>
                {/* What it is */}
                <p className="text-xs text-neutral-600 leading-relaxed border-l-2 border-neutral-700 pl-3">
                  {meta.what}
                </p>
                {/* Advice */}
                <p className="text-xs text-neutral-400 leading-relaxed">{meta.tip}</p>
                <div className="flex flex-wrap gap-1.5">
                  {meta.words.map(w => (
                    <span key={w} className="font-mono text-xs bg-neutral-800 text-neutral-400 px-2 py-0.5 rounded">
                      {w}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Strengths */}
      {strengths.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">What you do well</p>
          {strengths.map(({ key, val, centroidVal }) => {
            const meta = FEATURE_META[key];
            return (
              <div key={key} className="rounded-lg border border-emerald-900/40 bg-emerald-950/20 px-4 py-3 flex items-center justify-between">
                <span className="text-sm text-neutral-300">{meta.label}</span>
                <span className="text-xs font-mono text-emerald-400">
                  {Math.round(Math.abs(val - centroidVal))}ms faster than cluster avg
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Gap to next cluster (stable profile only) */}
      {profileReady && nextFasterProfile && clusterGaps.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">
            Gap to {nextFasterProfile.name}
          </p>
          <p className="text-xs text-neutral-600">
            {nextFasterProfile.name} typists are faster mainly through:
          </p>
          {clusterGaps.map(({ key, gap }) => (
            <div key={key} className="flex items-center justify-between rounded-lg border border-neutral-800 px-4 py-2.5">
              <span className="text-sm text-neutral-400">{FEATURE_META[key].label}</span>
              <span className="text-sm font-mono text-neutral-300">~{Math.round(gap)}ms faster</span>
            </div>
          ))}
        </div>
      )}

      {/* Speed number line */}
      <div className="space-y-2">
        <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">Average transition speed</p>
        <div className="relative h-9">
          <div className="absolute top-4 left-0 right-0 h-px bg-neutral-800" />
          {SPEED_ORDER.map((idx) => {
            const spd = CLUSTER_AVG_SPEED[idx];
            const pct = toPct(spd);
            const isUser = idx === displayCluster;
            return (
              <div
                key={idx}
                className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 rounded-full ${
                  isUser ? 'w-3.5 h-3.5 bg-neutral-100 ring-2 ring-neutral-100/30' : 'w-2 h-2 bg-neutral-700'
                }`}
                style={{ left: `${pct}%` }}
                title={`${CLUSTER_PROFILES[idx].name}: ${spd}ms avg`}
              />
            );
          })}
          {userSpeed != null && (
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-amber-400/70"
              style={{ left: `${toPct(userSpeed)}%` }}
              title={`Your measured speed: ${Math.round(userSpeed)}ms`}
            />
          )}
        </div>
        <div className="flex justify-between text-xs text-neutral-700">
          <span>Fast (40ms)</span>
          {userSpeed != null && (
            <span className="text-amber-400/70">you: {Math.round(userSpeed)}ms</span>
          )}
          <span>Slow (380ms)</span>
        </div>
      </div>

      {/* Radar chart */}
      {profileReady && centroid && (
        <div className="space-y-2">
          <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">Feature profile</p>
          <div className="flex gap-4 text-xs text-neutral-600 mb-1">
            <span className="flex items-center gap-1"><span className="inline-block w-5 border-t-2 border-neutral-300" />you</span>
            <span className="flex items-center gap-1"><span className="inline-block w-5 border-t-2 border-dashed border-neutral-600" />cluster avg</span>
          </div>
          <p className="text-xs text-neutral-700">More area = relatively faster at that movement</p>
          <RadarChart userValues={userRadarValues} centroidValues={centroid} />
        </div>
      )}

      {/* Full breakdown */}
      <div className="space-y-2">
        <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">Full breakdown (ms · lower = faster)</p>
        <div className="rounded-xl border border-neutral-800 divide-y divide-neutral-800">
          {FEATURE_KEYS.map((key, idx) => {
            const val = features[key] as number | null;
            const clusterAvg = centroid ? centroid[idx] : null;
            return (
              <div key={key} className="flex justify-between items-center px-4 py-2.5">
                <span className="text-sm text-neutral-400">{FEATURE_META[key].label}</span>
                <div className="text-right">
                  <span className="text-sm font-mono text-neutral-200">
                    {val != null ? `${val.toFixed(0)} ms` : '—'}
                  </span>
                  {clusterAvg != null && val != null && (
                    <span className={`block text-xs font-mono ${val > clusterAvg ? 'text-red-500/70' : 'text-emerald-500/70'}`}>
                      avg {clusterAvg.toFixed(0)}
                    </span>
                  )}
                </div>
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
        type again
      </button>
    </div>
  );
}
