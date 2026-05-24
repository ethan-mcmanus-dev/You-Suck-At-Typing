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

const FEATURE_LABELS: Record<string, string> = {
  mean_dwell_sfb: 'Same-finger dwell',
  mean_flight_sfb: 'Same-finger transition',
  mean_flight_roll_in: 'Inward roll',
  mean_flight_roll_out: 'Outward roll',
  mean_flight_alternation: 'Hand alternation',
  mean_flight_scissor: 'Scissor (row jump)',
  mean_flight_lateral: 'Pinky reach',
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
        <button onClick={() => router.push('/')} className="text-neutral-400 text-xs underline underline-offset-2 hover:text-neutral-100">
          Try again
        </button>
      </div>
    );
  }

  if (!result) {
    return <div className="text-center py-16 text-neutral-500 text-sm">Loading your results…</div>;
  }

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

  const sessionLabel = result.n_sessions <= 1
    ? 'Session 1 — type more passages for a more stable result'
    : `Based on ${result.n_sessions} sessions`;

  return (
    <div className="space-y-8">

      {/* Cluster identity */}
      <div className="space-y-1">
        {profile ? (
          <>
            <div className="flex items-baseline gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{profile.name}</h1>
              <span className="text-sm text-neutral-500">rank {profile.speed_rank} of 8</span>
            </div>
            <p className="text-neutral-400 text-sm leading-relaxed max-w-lg">{profile.description}</p>
          </>
        ) : (
          <h1 className="text-2xl font-bold tracking-tight">Your Results</h1>
        )}
        <p className="text-xs text-neutral-600 pt-1">{sessionLabel}</p>
      </div>

      {/* Speed spectrum */}
      <div className="space-y-2">
        <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">Speed spectrum</p>
        <div className="flex gap-1">
          {SPEED_ORDER.map((clusterIdx) => {
            const isUser = clusterIdx === displayCluster;
            const p = CLUSTER_PROFILES[clusterIdx];
            return (
              <div
                key={clusterIdx}
                title={p.name}
                className={`flex-1 rounded py-1.5 text-center text-xs font-mono transition-colors ${
                  isUser
                    ? 'bg-neutral-100 text-neutral-900 font-semibold'
                    : 'bg-neutral-800 text-neutral-500'
                }`}
              >
                {isUser ? p.name.split(' ')[0] : ''}
              </div>
            );
          })}
        </div>
        <div className="flex justify-between text-xs text-neutral-600">
          <span>Fastest</span>
          <span>Slowest</span>
        </div>
      </div>

      {/* Radar chart + insights */}
      <div className="flex flex-col sm:flex-row gap-6 items-start">
        {centroid && (
          <div className="space-y-2 shrink-0">
            <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">Your profile</p>
            <div className="flex gap-4 text-xs text-neutral-600">
              <span className="flex items-center gap-1">
                <span className="inline-block w-5 border-t-2 border-neutral-300" /> you
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-5 border-t-2 border-dashed border-neutral-500" /> cluster avg
              </span>
            </div>
            <RadarChart userValues={userRadarValues} centroidValues={centroid} />
          </div>
        )}

        <div className="flex-1 space-y-3 min-w-0">
          {insights.headline ? (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-1">
              <div className="text-xs font-medium text-amber-400 uppercase tracking-wider">Top finding</div>
              <p className="text-neutral-100 text-sm leading-relaxed">{insights.headline.message}</p>
            </div>
          ) : (
            <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-4">
              <p className="text-neutral-400 text-sm">Your typing looks typical for your cluster. No standout patterns.</p>
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
      </div>

      {/* Feature breakdown */}
      <div className="space-y-2">
        <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">Feature breakdown (ms)</p>
        <div className="rounded-xl border border-neutral-800 divide-y divide-neutral-800">
          {Object.entries(FEATURE_LABELS).map(([key, label]) => {
            const val = features[key as keyof typeof features];
            return (
              <div key={key} className="flex justify-between items-center px-4 py-2.5">
                <span className="text-sm text-neutral-400">{label}</span>
                <span className="text-sm font-mono text-neutral-200">
                  {val != null ? `${(val as number).toFixed(0)} ms` : '—'}
                </span>
              </div>
            );
          })}
        </div>
        <p className="text-xs text-neutral-600">
          {features.n_keystrokes} keystrokes · {features.n_bigrams_labeled} labeled bigrams · cluster #{displayCluster}
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
