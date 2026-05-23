const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface KeystrokeEvent {
  key: string;
  keydown_ms: number;
  keyup_ms: number;
}

export interface Insight {
  feature: string;
  severity: string;
  z_score: number;
  user_value: number;
  cluster_mean: number;
  message: string;
}

export interface InsightReport {
  headline: Insight | null;
  secondary: Insight[];
  positives: Insight[];
  cluster_idx: number;
  n_features_observed: number;
}

export interface SessionResult {
  session_id: string;
  cluster_idx: number | null;
  cluster_version: number;
  features: Record<string, number | null>;
  insights: InsightReport;
}

export async function submitSession(
  participantId: string,
  events: KeystrokeEvent[]
): Promise<SessionResult> {
  const res = await fetch(`${API}/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      participant_id: participantId,
      session_context: "prose",
      events,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `API error ${res.status}`);
  }
  return res.json();
}

export function warmServer(): void {
  fetch(`${API}/health`).catch(() => {});
}
