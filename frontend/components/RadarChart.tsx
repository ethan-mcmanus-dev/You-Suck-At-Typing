'use client';

import { FEATURE_LABELS, normalizeFeature } from '@/lib/clusters';

interface RadarChartProps {
  userValues: (number | null | undefined)[];
  centroidValues: number[];
  size?: number;
}

const N = 7;

function angle(i: number): number {
  return (2 * Math.PI * i) / N - Math.PI / 2;
}

function toXY(i: number, r: number, cx: number, cy: number): [number, number] {
  return [cx + r * Math.cos(angle(i)), cy + r * Math.sin(angle(i))];
}

function toPolygon(values: number[], r: number, cx: number, cy: number): string {
  return values.map((v, i) => toXY(i, r * v, cx, cy).join(',')).join(' ');
}

export default function RadarChart({ userValues, centroidValues, size = 260 }: RadarChartProps) {
  const cx = size / 2;
  const cy = size / 2;
  const R = (size / 2) * 0.6;
  const labelR = (size / 2) * 0.87;

  const userNorm = userValues.map((v, i) => normalizeFeature(v, i));
  const centNorm = centroidValues.map((v, i) => normalizeFeature(v, i));

  const rings = [0.25, 0.5, 0.75, 1.0];

  return (
    <svg width={size} height={size} className="overflow-visible">
      {/* Grid rings */}
      {rings.map((ring) => (
        <polygon
          key={ring}
          points={Array.from({ length: N }, (_, i) => {
            const [x, y] = toXY(i, R * ring, cx, cy);
            return `${x},${y}`;
          }).join(' ')}
          fill="none"
          stroke={ring === 1.0 ? '#3f3f3f' : '#262626'}
          strokeWidth="1"
        />
      ))}

      {/* Axis lines */}
      {Array.from({ length: N }, (_, i) => {
        const [x, y] = toXY(i, R, cx, cy);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="#2a2a2a" strokeWidth="1" />;
      })}

      {/* Cluster centroid polygon */}
      <polygon
        points={toPolygon(centNorm, R, cx, cy)}
        fill="none"
        stroke="#525252"
        strokeWidth="1.5"
        strokeDasharray="5,3"
      />

      {/* User polygon */}
      <polygon
        points={toPolygon(userNorm, R, cx, cy)}
        fill="rgba(229,229,229,0.07)"
        stroke="#d4d4d4"
        strokeWidth="2"
        strokeLinejoin="round"
      />

      {/* Axis labels */}
      {Array.from({ length: N }, (_, i) => {
        const a = angle(i);
        const [lx, ly] = toXY(i, labelR, cx, cy);
        const anchor = Math.abs(Math.cos(a)) < 0.15 ? 'middle' : Math.cos(a) > 0 ? 'start' : 'end';
        return (
          <text
            key={i}
            x={lx}
            y={ly}
            textAnchor={anchor}
            dominantBaseline="middle"
            fontSize="10"
            fill="#737373"
            fontFamily="monospace"
          >
            {FEATURE_LABELS[i]}
          </text>
        );
      })}
    </svg>
  );
}
