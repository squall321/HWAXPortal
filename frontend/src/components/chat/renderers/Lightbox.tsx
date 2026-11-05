// 챗 그림 확대 오버레이 — 이미지·구조도·html 미리보기·같은 출처 SVG(격리 iframe) 넷이 같은 조작감을 공유한다
import { useCallback, useEffect, useRef, useState } from 'react';
import { Modal } from '../../ui/Modal';
import { svgFrameStageScale } from './svgFrame';

/** 오버레이에 띄울 것. 셋 다 같은 조작(휠 확대·끌어 이동·Esc)을 탄다. */
export type LightboxItem =
  | { kind: 'img'; src: string; caption?: string }
  | { kind: 'svg'; svg: string; caption?: string }
  | { kind: 'frame'; srcDoc: string; caption?: string }
  // 같은 출처 SVG 주소 — 원래 크기(w × h)의 격리 iframe 을 배율로 맞춘다(docs/report-figures RF-36)
  | { kind: 'svgsrc'; src: string; w: number; h: number; caption?: string };

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
  // SVG iframe 의 맞춤 배율 — max-width 로는 iframe 안의 SVG 가 줄지 않아 무대 크기를 재서 변형으로 줄인다.
  const [stage, setStage] = useState({ w: 0, h: 0 });
  useEffect(() => {
    const el = stageRef.current;
    if (!el || item.kind !== 'svgsrc') return;
    const measure = () => setStage({ w: el.clientWidth - 32, h: el.clientHeight - 32 });   // 무대 안쪽 여백 1rem 씩
    measure();
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [item.kind]);

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
      if (e.key === '0') return reset();
      if (e.key === '+' || e.key === '=') return zoomBy(STEP);
      if (e.key === '-' || e.key === '_') return zoomBy(1 / STEP);
    };
    // Esc·뒤 문서 스크롤 잠금은 Modal(<dialog>)이 한다 — 여기는 확대 단축키만
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [reset, zoomBy]);

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

  return (
    <Modal onClose={onClose} label={item.caption || '그림 확대 보기'}>
      <div className="lb-overlay" onClick={onClose}>
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
          {(item.kind === 'img' || item.kind === 'svgsrc') && (
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
          {item.kind === 'svgsrc' && (
            // ⚠ sandbox 는 빈 값 그대로 — 챗 본문과 같은 격리다. 호버는 SVG 안의 CSS 라 스크립트가 필요 없다. iframe 위에서는 끌기 · 휠이 iframe 으로
            //   가므로 확대 · 이동은 단추 · 단축키 · 가장자리 끌기로 한다.
            <iframe
              className="lb-svgframe"
              sandbox=""
              src={item.src}
              referrerPolicy="no-referrer"
              title={item.caption || '그림'}
              width={item.w}
              height={item.h}
              style={fit ? { transform: `scale(${svgFrameStageScale(item.w, item.h, stage.w, stage.h)})` } : style}
            />
          )}
        </div>

        <div className="lb-hint" onClick={(e) => e.stopPropagation()}>
          휠·+/− 확대 · 끌어서 이동 · 0 맞춤 · Esc 닫기
        </div>
      </div>
    </Modal>
  );
}
