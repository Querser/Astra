interface Point {
  x: number;
  y: number;
}

function smoothPath(pts: Point[]): string {
  if (pts.length < 2) return "";
  let d = `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(pts.length - 1, i + 2)];
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
  }
  return d;
}

function niceTicks(min: number, max: number): { lo: number; hi: number; ticks: number[] } {
  const span = Math.max(max - min, 1);
  let lo = min - span * 0.12;
  let hi = max + span * 0.12;
  const candidates = [1, 2, 5, 10, 20, 25, 50];
  let step = candidates[candidates.length - 1];
  for (const c of candidates) {
    if ((hi - lo) / c <= 5.2) {
      step = c;
      break;
    }
  }
  lo = Math.floor(lo / step) * step;
  hi = Math.ceil(hi / step) * step;
  const ticks: number[] = [];
  for (let v = lo; v <= hi + 1e-9; v += step) {
    ticks.push(Math.round(v * 100) / 100);
  }
  return { lo, hi, ticks };
}

export interface LineChartProps {
  /** Unique ID for the gradient on this page. */
  id: string;
  unit: string;
  values: number[];
  xTicks: { index: number; label: string }[];
  /** Label for each point in native tooltips. */
  pointLabels: string[];
  color: string;
  ariaLabel: string;
}

const W = 340;
const H = 168;
const PAD = { l: 36, r: 14, t: 14, b: 24 };

export function LineChart({
  id,
  unit,
  values,
  xTicks,
  pointLabels,
  color,
  ariaLabel,
}: LineChartProps) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const { lo, hi, ticks } = niceTicks(min, max);
  const n = values.length;
  const innerW = W - PAD.l - PAD.r;
  const innerH = H - PAD.t - PAD.b;
  const x = (i: number) => PAD.l + (i / (n - 1)) * innerW;
  const y = (v: number) => PAD.t + (1 - (v - lo) / (hi - lo)) * innerH;
  const baseY = PAD.t + innerH;

  const pts: Point[] = values.map((v, i) => ({ x: x(i), y: y(v) }));
  const line = smoothPath(pts);
  const area = `${line} L ${pts[n - 1].x.toFixed(1)} ${baseY.toFixed(1)} L ${pts[0].x.toFixed(1)} ${baseY.toFixed(1)} Z`;
  const last = pts[n - 1];
  const lastValue = values[n - 1];

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="chart-animated w-full"
      role="img"
      aria-label={ariaLabel}
    >
      <defs>
        <linearGradient id={`${id}-fill`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity={0.26} />
          <stop offset="1" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>

      <g className="chart-grid">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.l} y1={y(t)} x2={W - PAD.r} y2={y(t)} />
            <text x={PAD.l - 6} y={y(t) + 3} textAnchor="end">
              {String(t)}
            </text>
          </g>
        ))}
      </g>

      <g className="chart-area">
        <path d={area} fill={`url(#${id}-fill)`} />
        <path className="chart-line" d={line} stroke={color} pathLength={1} />
        {pts.map((p, i) => (
          <circle
            key={i}
            className="chart-point"
            cx={p.x}
            cy={p.y}
            r={i === n - 1 ? 3.4 : 2.1}
            fill={i === n - 1 ? color : "var(--t-bg1)"}
            stroke={color}
            strokeWidth={1.2}
          >
            <title>{`${pointLabels[i]}: ${values[i]} ${unit}`}</title>
          </circle>
        ))}
      </g>

      <text
        x={last.x - 8}
        y={last.y - 9}
        textAnchor="end"
        fontSize={10}
        fill="var(--t-text)"
        style={{ fontFamily: "var(--font-geist-mono), monospace" }}
      >
        {`${lastValue} ${unit}`}
      </text>

      <g className="chart-x">
        {xTicks.map((t) => (
          <text
            key={t.index}
            x={x(t.index)}
            y={H - 8}
            textAnchor={t.index === n - 1 ? "end" : "middle"}
          >
            {t.label}
          </text>
        ))}
      </g>
    </svg>
  );
}
