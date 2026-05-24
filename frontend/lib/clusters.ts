// Static cluster data derived from model_artifacts/clusters_v1.json (v1, k=8, n=149570)

export const FEATURE_LABELS = [
  'SFB dwell', 'SFB flight', 'Roll in', 'Roll out',
  'Alternation', 'Scissor', 'Pinky reach',
] as const;

// Centroid values [ms] for each cluster index
export const CLUSTER_CENTROIDS: Record<number, number[]> = {
  0: [86.8, 280.2, 269.3, 269.4, 257.8, 232.5, 251.5],
  1: [115.8, 159.1, 68.9,  75.9,  62.5,  51.2,  62.7],
  2: [86.6,  132.7, 49.0,  55.6,  45.6,  36.1,  42.5],
  3: [118.0, 221.1, 146.7, 150.9, 130.7, 119.6, 136.8],
  4: [107.8, 337.8, 351.9, 350.7, 348.2, 335.0, 360.9],
  5: [86.4,  235.4, 191.7, 192.1, 170.6, 157.5, 176.3],
  6: [122.8, 281.1, 236.9, 234.3, 213.9, 196.7, 221.0],
  7: [84.5,  183.5, 115.0, 121.3, 100.1, 93.6,  109.0],
};

// Per-feature [min, max] across all cluster centroids — used for radar normalization
export const FEATURE_RANGES: [number, number][] = [
  [84.5,  122.8], // mean_dwell_sfb
  [132.7, 337.8], // mean_flight_sfb
  [49.0,  351.9], // mean_flight_roll_in
  [55.6,  350.7], // mean_flight_roll_out
  [45.6,  348.2], // mean_flight_alternation
  [36.1,  335.0], // mean_flight_scissor
  [42.5,  360.9], // mean_flight_lateral
];

export interface ClusterProfile {
  name: string;
  description: string;
  speed_rank: number; // 1 = fastest, 8 = slowest
}

export const CLUSTER_PROFILES: Record<number, ClusterProfile> = {
  2: {
    name: 'Elite',
    speed_rank: 1,
    description: 'Your fingers move on autopilot. Sub-50ms hand transitions put you in the fastest tier in the Aalto 136M keystroke dataset.',
  },
  1: {
    name: 'Speed Demon',
    speed_rank: 2,
    description: 'Very fast typist with strong rolling technique. Your hand transitions rival the top tier.',
  },
  7: {
    name: 'Capable',
    speed_rank: 3,
    description: 'Above-average speed with consistent timing. Solid muscle memory is clearly built in.',
  },
  3: {
    name: 'Steady',
    speed_rank: 4,
    description: 'Comfortable middle-tier typist. Reliable timing with clear room to accelerate.',
  },
  5: {
    name: 'Developing',
    speed_rank: 5,
    description: 'Below average pace but consistent. This is the zone where deliberate practice pays off most.',
  },
  6: {
    name: 'Deliberate',
    speed_rank: 6,
    description: 'Careful typist who commits fully to each keystroke. Heavier key presses, methodical transitions.',
  },
  0: {
    name: 'Searching',
    speed_rank: 7,
    description: 'Slow transitions with quick key release — a pattern that suggests you\'re still building positional memory for some keys.',
  },
  4: {
    name: 'Getting Started',
    speed_rank: 8,
    description: 'The slowest cluster. You may be hunt-and-pecking or very early in your typing journey.',
  },
};

// Cluster indices ordered from fastest (index 0) to slowest (index 7)
export const SPEED_ORDER = [2, 1, 7, 3, 5, 6, 0, 4];

/** Normalize a feature value to [0, 1] where 1 = fastest (best), 0 = slowest. */
export function normalizeFeature(value: number | null | undefined, featureIdx: number): number {
  if (value == null) return 0;
  const [min, max] = FEATURE_RANGES[featureIdx];
  return Math.max(0, Math.min(1, (max - value) / (max - min)));
}
