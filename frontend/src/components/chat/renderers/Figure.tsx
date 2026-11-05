// 챗 본문 그림 — 캡션·로딩 스켈레톤·가로 스크롤 판정·눌러서 확대(라이트박스) · 같은 출처 SVG 는 격리 iframe(호버가 산다)
import { useCallback, useEffect, useRef, useState } from 'react';
import { Lightbox, type LightboxItem } from './Lightbox';
import { isSvgFrameSrc, svgFrameFit } from './svgFrame';

/** 칼럼 폭 대비 이 배수를 넘으면 '축소'가 아니라 '가로 스크롤'로 둔다.
 *  축소하면 축 라벨·범례가 뭉개져 읽을 수 없다 — 사용자가 보고한 그 증상이다. */
const WIDE_RATIO = 1.5;

/** 그림을 누를 수 있게 감싸는 공통 껍데기. 캡션·확대 아이콘·키보드 진입을 여기서 준다. */
export function FigureShell({
  caption,
  item,
  wide,
  note,
  frame,
  className = '',
  children,
}: {
  caption?: string;
  item: LightboxItem;
  wide?: boolean;
  note?: string;
  /** 안에 iframe 이 든다 — iframe 안의 누름은 바깥으로 오지 않아 확대는 모서리 아이콘으로 연다. */
  frame?: boolean;
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
          className={`md-figure-frame${frame ? ' is-frame' : ''}`}
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

/** alt 가 파일명이거나 우리가 붙인 기본 문구면 캡션으로 쓰지 않는다(잡음이 된다). */
function captionOf(alt: string): string | undefined {
  return alt && alt !== '이미지' && alt !== '생성된 그래프' && !/^[\w.-]+\.(png|jpe?g|svg|webp)$/i.test(alt) ? alt : undefined;
}

/** 도구 산출 그래프 등 `![alt](url)` 이미지. 같은 출처 SVG 는 격리 iframe 으로(docs/report-figures RF-36). */
export function Figure({ src, alt }: { src: string; alt: string }) {
  return isSvgFrameSrc(src) ? <SvgFrameFigure src={src} alt={alt} /> : <ImgFigure src={src} alt={alt} />;
}

function ImgFigure({ src, alt }: { src: string; alt: string }) {
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

  const caption = captionOf(alt);

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

/** 같은 출처 SVG — 호버(파트 이름 풍선 · 치수)가 SVG 안의 CSS 라 `<img>` 로는 죽는다. `<iframe sandbox="">` 는 스크립트도 같은 출처도 막는다(따로 출처).
 *  SVG 문서는 자기 width · height 로 그려져 iframe 에 맞춰 줄지 않으므로, 원래 크기의 iframe 을 변형(scale)으로 줄인다 — 호버 판정은 변형을 따른다. */
function SvgFrameFigure({ src, alt }: { src: string; alt: string }) {
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);
  const [err, setErr] = useState(false);
  const [avail, setAvail] = useState(0);
  const wrapRef = useRef<HTMLSpanElement>(null);

  // 원래 크기 — iframe 은 안을 들여다볼 수 없어(따로 출처) 같은 주소를 그림으로 한 번 읽어 잰다(브라우저가 캐시한다).
  useEffect(() => {
    let live = true;
    setSize(null);
    setErr(false);
    const im = new Image();
    im.onload = () => live && setSize({ w: im.naturalWidth || 300, h: im.naturalHeight || 150 });
    im.onerror = () => live && setErr(true);
    im.src = src;
    return () => {
      live = false;
    };
  }, [src]);

  // 칼럼 폭 — 껍데기(md-figure-frame)는 내용 폭에 맞추므로(display:table) 블록인 바깥 .md-figure 로 잰다. 창이 바뀌면 다시 잰다.
  useEffect(() => {
    const el = wrapRef.current?.closest('.md-figure') as HTMLElement | null;
    if (!el) return;
    const measure = () => setAvail(el.clientWidth);
    measure();
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const caption = captionOf(alt);
  if (err) {
    return <span className="md-img-err">이미지를 불러오지 못했습니다 — {alt || src}</span>;
  }
  const fit = size ? svgFrameFit(size.w, size.h, avail, WIDE_RATIO) : null;
  return (
    <FigureShell
      caption={caption}
      wide={fit?.wide}
      note={fit?.wide ? '가로로 깁니다 — 옆으로 밀거나 크게 보세요' : undefined}
      item={size ? { kind: 'svgsrc', src, w: size.w, h: size.h, caption: caption || alt } : { kind: 'img', src, caption: caption || alt }}
      frame
      className="md-figure-img md-figure-svgframe"
    >
      <span ref={wrapRef} className="md-img-scroll">
        {!(size && fit) && <span className="md-img-skel" aria-hidden="true" />}
        {size && fit && (
          <span className="md-svgframe-box" style={{ width: size.w * fit.scale, height: size.h * fit.scale }}>
            {/* ⚠ sandbox 는 빈 값 그대로 — allow-scripts · allow-same-origin 을 넣지 않는다. 호버는 SVG 안의 CSS 라 스크립트가 필요 없다. */}
            <iframe
              className="md-svgframe"
              sandbox=""
              src={src}
              referrerPolicy="no-referrer"
              loading="lazy"
              title={alt || '그림'}
              width={size.w}
              height={size.h}
              style={{ transform: `scale(${fit.scale})` }}
            />
          </span>
        )}
      </span>
    </FigureShell>
  );
}

