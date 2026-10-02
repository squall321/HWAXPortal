// HWAX 브랜드 마크 — 헤더·로그인·파비콘이 같은 모양(주 버튼 채움 위에 흰 H)
export function BrandMark({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--primary)" />
      <path d="M10 9v14M22 9v14M10 16h12" stroke="#fff" strokeWidth="3" strokeLinecap="round" fill="none" />
    </svg>
  );
}
