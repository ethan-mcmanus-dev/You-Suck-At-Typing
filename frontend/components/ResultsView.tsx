'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { SessionResult } from '@/lib/api';

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
    // Result is already in sessionStorage from the submit — check there first
    const cached = sessionStorage.getItem(`ysat_result_${sessionId}`);
    if (cached) {
      try {
        setResult(JSON.parse(cached));
        return;
      } catch {}
    }

    // Otherwise fetch from API
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
        <button
          onClick={() => router.push('/')}
          className="text-neutral-400 text-xs underline underline-offset-2 hover:text-neutral-100"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="text-center py-16 text-neutral-500 text-sm">
        Loading your results…
      </div>
    );
  }

  const { insights, features } = result;

  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Your Results</h1>
        <p className="text-neutral-400 text-sm">
          {features.n_keystrokes} keystrokes &middot; cluster {result.cluster_idx}
        </p>
      </div>

      {/* Headline */}
      {insights.headline ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-5 space-y-2">
          <div className="text-xs font-medium text-amber-400 uppercase tracking-wider">
            Top finding
          </div>
          <p className="text-neutral-100 leading-relaxed">
            {insights.headline.message}
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-5">
          <p className="text-neutral-400 text-sm">
            Your typing looks typical for your cluster. No standout patterns detected.
          </p>
        </div>
      )}

      {/* Secondary insights */}
      {insights.secondary.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-xs font-medium text-neutral-500 uppercase tracking-wider">
            Also notable
          </h2>
          {insights.secondary.map((ins, i) => (
            <div key={i} className="rounded-lg border border-neutral-700 bg-neutral-900 p-4">
              <p className="text-neutral-300 text-sm leading-relaxed">{ins.message}</p>
            </div>
          ))}
        </div>
      )}

      {/* Strengths */}
      {insights.positives.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-xs font-medium text-neutral-500 uppercase tracking-wider">
            Strengths
          </h2>
          {insights.positives.map((ins, i) => (
            <div key={i} className="rounded-lg border border-emerald-700/30 bg-emerald-900/10 p-4">
              <p className="text-neutral-300 text-sm leading-relaxed">{ins.message}</p>
            </div>
          ))}
        </div>
      )}

      {/* Feature breakdown */}
      <div className="space-y-3">
        <h2 className="text-xs font-medium text-neutral-500 uppercase tracking-wider">
          Feature breakdown (ms)
        </h2>
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
