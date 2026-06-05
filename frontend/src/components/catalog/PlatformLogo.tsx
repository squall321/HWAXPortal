import type { Accent } from '../../api/systems.api';

const GRAD: Record<Accent, [string, string]> = {
  violet: ['#a78bfa', '#6d28d9'],
  cyan: ['#22d3ee', '#0891b2'],
  amber: ['#fbbf24', '#d97706'],
  emerald: ['#34d399', '#059669'],
  sky: ['#38bdf8', '#2563eb'],
  rose: ['#fb7185', '#e11d48'],
  indigo: ['#818cf8', '#4f46e5'],
};

const stroke = {
  fill: 'none',
  stroke: '#fff',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
};

function Glyph({ id }: { id: string }) {
  switch (id) {
    case 'heax-hub': // hub + spokes (AI agent network)
      return (
        <g {...stroke}>
          <circle cx="28" cy="28" r="4.5" />
          <circle cx="18" cy="18" r="2.5" />
          <circle cx="38" cy="18" r="2.5" />
          <circle cx="18" cy="38" r="2.5" />
          <circle cx="38" cy="38" r="2.5" />
          <path d="M24.7 24.7 20 20M31.3 24.7 36 20M24.7 31.3 20 36M31.3 31.3 36 36" />
        </g>
      );
    case 'ai-data-hub': // stacked database layers
      return (
        <g {...stroke}>
          <ellipse cx="28" cy="19" rx="10" ry="3.6" />
          <path d="M18 19v6c0 2 4.5 3.6 10 3.6S38 27 38 25v-6" />
          <path d="M18 25v6c0 2 4.5 3.6 10 3.6S38 33 38 31v-6" />
        </g>
      );
    case 'mx-white-paper': // document + folded corner
      return (
        <g {...stroke}>
          <path d="M20 16h10l8 8v15a1 1 0 0 1-1 1H20a1 1 0 0 1-1-1V17a1 1 0 0 1 1-1Z" />
          <path d="M30 16v8h8" />
          <path d="M23 30h9M23 35h9" />
        </g>
      );
    case 'report-archive': // bar chart on a baseline
      return (
        <g {...stroke}>
          <path d="M19 39V29M28 39V19M37 39V25" />
          <path d="M16 42h26" />
        </g>
      );
    case 'smart-twin-cluster': // twin interlocking hexes
      return (
        <g {...stroke}>
          <path d="M24 15.5l6.5 3.75v7.5L24 30.5l-6.5-3.75v-7.5z" opacity="0.55" />
          <path d="M34 25.5l6.5 3.75v7.5L34 40.5l-6.5-3.75v-7.5z" />
        </g>
      );
    case 'spdm': // lifecycle loop
      return (
        <g {...stroke}>
          <path d="M39 25a12 12 0 1 0 1.5 9" />
          <path d="M40.5 22.5V29h-6.5" />
        </g>
      );
    default:
      return <circle cx="28" cy="28" r="8" {...stroke} />;
  }
}

export function PlatformLogo({
  id,
  accent,
  size = 58,
}: {
  id: string;
  accent: Accent;
  size?: number;
}) {
  const [c1, c2] = GRAD[accent];
  const gid = `pl-${accent}`;
  return (
    <svg width={size} height={size} viewBox="0 0 56 56" className="plogo" aria-hidden="true">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={c1} />
          <stop offset="1" stopColor={c2} />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="52" height="52" rx="15" fill={`url(#${gid})`} />
      <rect x="2" y="2" width="52" height="27" rx="15" fill="#fff" opacity="0.14" />
      <Glyph id={id} />
    </svg>
  );
}
