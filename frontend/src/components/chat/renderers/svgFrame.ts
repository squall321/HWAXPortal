// 같은 출처 SVG 그림을 격리 iframe 으로 그릴지 · 얼마나 줄일지 정하는 순수 셈(docs/report-figures RF-36)

/** 같은 출처 경로(`/…`)이고 확장자가 `.svg` 인 그림만 iframe 으로 — 바깥 출처는 페이지 CSP(`frame-src 'self'`)가 막고, 다른 꼴은 `<img>` 그대로다.
 *  `//host/…` 는 경로가 아니라 바깥 출처다. */
export function isSvgFrameSrc(src: string): boolean {
  if (typeof src !== 'string' || !src.startsWith('/') || src.startsWith('//')) return false;
  const path = src.split(/[?#]/, 1)[0];
  return /\.svg$/i.test(path);
}

/** 원래 크기(w × h)를 칼럼 폭(avail)에 맞춘다 — SVG 문서는 자기 width · height 로 그려져 iframe 에 맞춰 줄지 않으므로 iframe 을 원래 크기로 두고
 *  배율(scale)로 줄인다. 칼럼보다 wideRatio 배 넘게 넓으면 줄이지 않고 가로 스크롤(그림 `<img>` 과 같은 규칙 — 줄이면 글자가 뭉개진다). */
export function svgFrameFit(w: number, h: number, avail: number, wideRatio: number): { scale: number; wide: boolean } {
  if (!(w > 0) || !(h > 0) || !(avail > 0)) return { scale: 1, wide: false };
  if (w > avail * wideRatio) return { scale: 1, wide: true };
  return { scale: Math.min(1, avail / w), wide: false };
}

/** 확대 화면의 맞춤 — 무대(sw × sh) 안에 들어오게 줄이기만 한다(키우지 않는다). */
export function svgFrameStageScale(w: number, h: number, sw: number, sh: number): number {
  if (!(w > 0) || !(h > 0) || !(sw > 0) || !(sh > 0)) return 1;
  return Math.min(1, sw / w, sh / h);
}
