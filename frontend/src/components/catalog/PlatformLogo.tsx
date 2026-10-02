
const stroke = {
  fill: 'none',
  stroke: 'currentColor',
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
    case 'signalforge': // 퍼지는 신호(VOC 수집)
      return (
        <g {...stroke}>
          <circle cx="21" cy="35" r="2.5" />
          <path d="M21 27a8 8 0 0 1 8 8" />
          <path d="M21 20a15 15 0 0 1 15 15" />
          <path d="M21 13a22 22 0 0 1 22 22" opacity="0.55" />
        </g>
      );
    case 'ste': // 클러스터로 올려 보내는 잡
      return (
        <g {...stroke}>
          <path d="M28 33V17M21.5 23.5 28 17l6.5 6.5" />
          <path d="M17 32v5a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2v-5" />
        </g>
      );
    case 'hwax-risk': // 방패 + 경고
      return (
        <g {...stroke}>
          <path d="M28 14l10 4v8c0 7-4.4 11.6-10 14-5.6-2.4-10-7-10-14v-8z" />
          <path d="M28 21v7M28 33v.5" />
        </g>
      );
    case 'arp': // AI Ready 데이터(적층) + 반짝임
      return (
        <g {...stroke}>
          <ellipse cx="24" cy="20" rx="8" ry="3" />
          <path d="M16 20v12c0 1.7 3.6 3 8 3s8-1.3 8-3V20" />
          <path d="M16 26c0 1.7 3.6 3 8 3s8-1.3 8-3" opacity="0.55" />
          <path d="M39 27v8M35 31h8" />
        </g>
      );
    case 'odb-hub': // PCB 배선 + 비아
      return (
        <g {...stroke}>
          <path d="M15 21h10l5 5h6" />
          <path d="M15 35h8l5-5h8" />
          <circle cx="39" cy="26" r="2.5" />
          <circle cx="39" cy="30" r="2.5" opacity="0.55" />
        </g>
      );
    case 'knox-bridge': // 두 시스템을 잇는 고리
      return (
        <g {...stroke}>
          <rect x="14" y="24" width="15" height="8" rx="4" />
          <rect x="27" y="24" width="15" height="8" rx="4" />
        </g>
      );
    default:
      return <circle cx="28" cy="28" r="8" {...stroke} />;
  }
}

/** 앱 글리프 타일 — 앱마다 다른 그라디언트(8색) 대신 중립 바탕 + 강조색 선 하나(docs/ui-refresh PLAN §3 타일 색).
 *  색이 분류도 상태도 뜻하지 않아 화면만 소란했다. 글리프 모양이 앱을 가른다. */
export function PlatformLogo({ id, size = 44 }: { id: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 56 56" className="plogo" aria-hidden="true" style={{ color: 'var(--accent-fg)' }}>
      <rect x="1" y="1" width="54" height="54" rx="14" style={{ fill: 'var(--accent-soft)', stroke: 'var(--border)' }} />
      <Glyph id={id} />
    </svg>
  );
}
