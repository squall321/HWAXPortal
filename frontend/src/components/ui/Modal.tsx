// 대화상자 — 네이티브 <dialog>.showModal() 하나로: 포커스 가둠 · 뒤 화면 비활성 · Esc · 닫으면 포커스 복귀 · top layer(z-index 경쟁 없음)(docs/ui-refresh 단계 3)
//
// 마운트 = 열림이다(부르는 쪽이 조건부로 그린다). 안의 배경·카드 모양은 각 대화상자 CSS 가 그대로 그린다 —
// 이 요소는 화면 전체를 덮는 투명한 틀일 뿐이다(.modal, ui.css). 대화상자 위의 대화상자(조직도 → 심층 보기)도
// top layer 가 연 순서대로 쌓고, Esc 는 맨 위 것만 받는다(종전엔 window 리스너 둘이 함께 닫혀 캡처 단계로 막았다).
import { type ReactNode, useEffect, useLayoutEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import '../../styles/ui.css';

export function Modal({
  onClose,
  label,
  labelledBy,
  children,
}: {
  onClose: () => void;
  /** 화면 낭독기가 읽을 이름 — 제목 요소가 있으면 labelledBy 를 쓴다 */
  label?: string;
  labelledBy?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  // 레이아웃 단계에서 열고 닫는다 — 닫기를 DOM 에서 떼기 **전에** 해야 브라우저가 연 사람(버튼)에게 포커스를 돌려준다.
  useLayoutEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (!d.open) d.showModal();
    // 뒤 문서가 같이 스크롤되면 확대·목록 스크롤 중에 화면이 통째로 움직인다. 겹쳐 열면 연 순서의 반대로 되돌린다.
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
      if (d.open) d.close();
    };
  }, []);

  return createPortal(
    <dialog
      ref={ref}
      className="modal"
      aria-label={label}
      aria-labelledby={labelledBy}
      // Esc — 브라우저가 닫기 전에 부르는 쪽 상태로 닫는다(상태가 '열림' 인 채 화면만 사라지지 않게)
      onCancel={(e) => {
        e.preventDefault();
        onCloseRef.current();
      }}
      // Esc 를 연달아 누르면 Chrome 이 cancel 없이 바로 닫는다(사용자 활성화 없는 반복 닫기 요청). 그때도 상태를 맞춘다.
      onClose={() => onCloseRef.current()}
    >
      {children}
    </dialog>,
    document.body,
  );
}
