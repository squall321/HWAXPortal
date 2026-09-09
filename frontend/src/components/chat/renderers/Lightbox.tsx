// 챗 그림 확대 오버레이 — 이미지·구조도·html 미리보기 셋이 같은 조작감을 공유한다
import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

/** 오버레이에 띄울 것. 셋 다 같은 조작(휠 확대·끌어 이동·Esc)을 탄다. */
export type LightboxItem =
  | { kind: 'img'; src: string; caption?: string }
  | { kind: 'svg'; svg: string; caption?: string }
  | { kind: 'frame'; srcDoc: string; caption?: string };

const MIN = 0.2;
const MAX = 8;
const STEP = 1.25;

/** 확대 배율을 상한 안에 가둔다 — 휠을 오래 굴려도 그림이 사라지지 않게. */
const clamp = (z: number) => Math.min(MAX, Math.max(MIN, z));

export function Lightbox({ item, onClose }: { item: LightboxItem; onClose: () => void }) {
  // fit=true 면 화면에 맞춘 상태(배율 미적용). 가로로 긴 그림은 여기서 100% 로 올려야
  // 비로소 축 라벨이 읽힌다 — 그게 이 오버레이를 만든 이유다.
  const [fit, setFit] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null);
  const stageRef = useRef<HTMLDivElement>(null);

  const reset = useCallback(() => {
    setFit(true);
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  const zoomBy = useCallback((f: number) => {
    setFit(false);
    setZoom((z) => clamp(z * f));
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') return onClose();
      if (e.key === '0') return reset();
      if (e.key === '+' || e.key === '=') return zoomBy(STEP);
      if (e.key === '-' || e.key === '_') return zoomBy(1 / STEP);
    };
    window.addEventListener('keydown', onKey);
    // 뒤 문서가 같이 스크롤되면 확대 중에 화면이 통째로 움직인다.
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose, reset, zoomBy]);

  // ⚠ React 의 onWheel 은 루트에 **passive** 로 붙어 preventDefault 가 무시된다
  //   ("Unable to preventDefault inside passive event listener" — 실측). 확대하려고 굴린 휠이
  //   뒤 문서를 스크롤시키지 않으려면 직접 non-passive 로 걸어야 한다.
  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      zoomBy(e.deltaY < 0 ? STEP : 1 / STEP);
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [zoomBy]);

  const onDown = (e: React.PointerEvent) => {
    if (fit) return; // 맞춤 상태에서는 움직일 곳이 없다
    drag.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
    (e.target as Element).setPointerCapture?.(e.pointerId);
  };
  const onMove = (e: React.PointerEvent) => {
    const d = drag.current;
    if (!d) return;
    setPan({ x: d.px + (e.clientX - d.x), y: d.py + (e.clientY - d.y) });
  };
  const onUp = () => {
    drag.current = null;
  };

  // 맞춤 상태에서는 변형을 아예 걸지 않는다 — CSS 의 max-width/height 가 맞춰 준다.
  const style = fit
    ? undefined
    : { transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: 'center center' };

  return createPortal(
    <div
      className="lb-overlay"
      role="dialog"
      aria-modal="true"
      aria-label={item.caption || '그림 확대 보기'}
      onClick={onClose}
    >
      <div className="lb-bar" onClick={(e) => e.stopPropagation()}>
        {item.caption && <span className="lb-caption">{item.caption}</span>}
        <span className="lb-spacer" />
        <button type="button" className="lb-btn" onClick={() => zoomBy(1 / STEP)} aria-label="축소">−</button>
        <button
          type="button"
          className="lb-btn lb-btn-wide"
          onClick={() => (fit ? (setFit(false), setZoom(1)) : reset())}
          title="맞춤 ↔ 원본 크기"
        >
          {fit ? '맞춤' : `${Math.round(zoom * 100)}%`}
        </button>
        <button type="button" className="lb-btn" onClick={() => zoomBy(STEP)} aria-label="확대">+</button>
        {item.kind === 'img' && (
          <a
            className="lb-btn"
            href={item.src}
            target="_blank"
            rel="noopener noreferrer"
            title="원본 새 탭에서 열기"
            onClick={(e) => e.stopPropagation()}
          >
            원본
          </a>
        )}
        <button type="button" className="lb-btn lb-close" onClick={onClose} aria-label="닫기">×</button>
      </div>

      <div
        ref={stageRef}
        className={`lb-stage${fit ? ' is-fit' : ' is-free'}`}
        onClick={(e) => e.stopPropagation()}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
      >
        {item.kind === 'img' && <img className="lb-img" src={item.src} alt={item.caption || '이미지'} style={style} />}
        {item.kind === 'svg' && (
          <div className="lb-svg" style={style} dangerouslySetInnerHTML={{ __html: item.svg }} />
        )}
        {item.kind === 'frame' && (
          // ⚠ allow-same-origin 을 절대 넣지 않는다 — 챗 본문 미리보기와 같은 격리다.
          //   크게 보여 주는 것이 격리를 낮출 이유가 되지 않는다.
          <iframe
            className="lb-frame"
            sandbox="allow-scripts"
            srcDoc={item.srcDoc}
            referrerPolicy="no-referrer"
            title={item.caption || 'HTML 미리보기'}
            style={style}
          />
        )}
      </div>

      <div className="lb-hint" onClick={(e) => e.stopPropagation()}>
        휠·+/− 확대 · 끌어서 이동 · 0 맞춤 · Esc 닫기
      </div>
    </div>,
    document.body,
  );
}
