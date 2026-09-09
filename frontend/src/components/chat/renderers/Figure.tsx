// 챗 본문 그림 — 캡션·로딩 스켈레톤·가로 스크롤 판정·눌러서 확대(라이트박스)
import { useCallback, useRef, useState } from 'react';
import { Lightbox, type LightboxItem } from './Lightbox';

/** 칼럼 폭 대비 이 배수를 넘으면 '축소'가 아니라 '가로 스크롤'로 둔다.
 *  축소하면 축 라벨·범례가 뭉개져 읽을 수 없다 — 사용자가 보고한 그 증상이다. */
const WIDE_RATIO = 1.5;

/** 그림을 누를 수 있게 감싸는 공통 껍데기. 캡션·확대 아이콘·키보드 진입을 여기서 준다. */
export function FigureShell({
  caption,
  item,
  wide,
  note,
  className = '',
  children,
}: {
  caption?: string;
  item: LightboxItem;
  wide?: boolean;
  note?: string;
  className?: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      {/* ⚠ figure/div 가 아니라 span 이다 — 마크다운 이미지는 <p> 안에서 렌더되고, 거기에
          블록 요소를 넣으면 유효하지 않은 HTML 이 된다. 영상 플레이어(md-video-wrap)가 같은
          이유로 span 을 블록으로 세운다. 인라인 전용 표면(InlineMd, 심의 발언 버블)에서도
          이 컴포넌트가 쓰이므로 span 이어야 안전하다. */}
      <span className={`md-figure${wide ? ' is-wide' : ''} ${className}`.trim()}>
        <span
          className="md-figure-frame"
          role="button"
          tabIndex={0}
          aria-label={`${caption || '그림'} — 눌러서 크게 보기`}
          onClick={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setOpen(true);
            }
          }}
        >
          {children}
          <span className="md-figure-zoom" aria-hidden="true">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="7" />
              <path d="M21 21l-4.3-4.3M11 8v6M8 11h6" strokeLinecap="round" />
            </svg>
          </span>
        </span>
        {(caption || note) && (
          <span className="md-figure-cap">
            {caption}
            {note && <span className="md-figure-note">{note}</span>}
          </span>
        )}
      </span>
      {open && <Lightbox item={item} onClose={() => setOpen(false)} />}
    </>
  );
}

/** 도구 산출 그래프 등 `![alt](url)` 이미지. */
export function Figure({ src, alt }: { src: string; alt: string }) {
  const [state, setState] = useState<'load' | 'ok' | 'err'>('load');
  const [wide, setWide] = useState(false);
  const wrapRef = useRef<HTMLSpanElement>(null);

  // 원본이 칼럼보다 훨씬 넓은지는 **로드된 뒤에만** 안다. naturalWidth 로 재고,
  // 넘으면 축소를 포기하고 가로 스크롤로 둔다.
  const onLoad = useCallback((e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    const avail = wrapRef.current?.clientWidth || 0;
    if (avail > 0 && img.naturalWidth > avail * WIDE_RATIO) setWide(true);
    setState('ok');
  }, []);

  // alt 가 파일명이거나 우리가 붙인 기본 문구면 캡션으로 쓰지 않는다(잡음이 된다).
  const caption = alt && alt !== '이미지' && alt !== '생성된 그래프' && !/^[\w.-]+\.(png|jpe?g|svg|webp)$/i.test(alt)
    ? alt
    : undefined;

  if (state === 'err') {
    return <span className="md-img-err">이미지를 불러오지 못했습니다 — {alt || src}</span>;
  }

  return (
    <FigureShell
      caption={caption}
      wide={wide}
      note={wide ? '가로로 깁니다 — 눌러서 크게 보세요' : undefined}
      item={{ kind: 'img', src, caption: caption || alt }}
      className="md-figure-img"
    >
      <span ref={wrapRef} className="md-img-scroll">
        {state === 'load' && <span className="md-img-skel" aria-hidden="true" />}
        <img
          className="md-img"
          src={src}
          alt={alt || '이미지'}
          loading="lazy"
          onLoad={onLoad}
          onError={() => setState('err')}
        />
      </span>
    </FigureShell>
  );
}
