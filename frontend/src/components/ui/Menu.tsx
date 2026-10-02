// 드롭다운 메뉴(APG 메뉴 버튼 패턴) — 열면 첫 항목에 포커스, ↑↓·Home·End 로 이동, Esc 는 닫고 버튼으로 복귀,
// Tab·바깥 클릭·포커스 이탈·화면 이동이면 닫는다. 키는 이 메뉴 안에서만 처리한다(여러 메뉴가 문서 키를 가로채지 않게).
import { useEffect, useId, useRef, useState, type KeyboardEvent, type MouseEvent, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';

const ITEMS = '[role="menuitem"]';

export function Menu({
  label,
  ariaLabel,
  children,
  className = '',
  active = false,
}: {
  label: ReactNode;
  ariaLabel?: string;
  children: ReactNode;
  className?: string;
  /** 지금 화면이 이 메뉴 안의 항목이면 버튼에 '현재 위치' 표시 */
  active?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const btn = useRef<HTMLButtonElement>(null);
  const id = useId();
  const { pathname } = useLocation();

  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => {
    if (!open) return;
    root.current?.querySelector<HTMLElement>(ITEMS)?.focus();
    const onDown = (e: globalThis.MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (!open) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      setOpen(false);
      btn.current?.focus();
      return;
    }
    if (e.key === 'Tab') {
      setOpen(false); // 포커스는 기본 동작대로 다음 요소로 간다
      return;
    }
    const list = Array.from(root.current?.querySelectorAll<HTMLElement>(ITEMS) ?? []);
    if (!list.length) return;
    const at = list.indexOf(document.activeElement as HTMLElement);
    const go = { ArrowDown: (at + 1) % list.length, ArrowUp: (at - 1 + list.length) % list.length, Home: 0, End: list.length - 1 }[
      e.key as 'ArrowDown' | 'ArrowUp' | 'Home' | 'End'
    ];
    if (go === undefined) return;
    e.preventDefault();
    list[go]?.focus();
  };

  // 항목을 눌렀을 때만 닫는다 — 머리의 이름·이메일을 끌어 복사하려다 닫히지 않게
  const onPopClick = (e: MouseEvent<HTMLDivElement>) => {
    if ((e.target as Element).closest(ITEMS)) setOpen(false);
  };

  return (
    <div
      className={`menu ${className}`}
      ref={root}
      onKeyDown={onKeyDown}
      onBlur={(e) => {
        if (open && !root.current?.contains(e.relatedTarget as Node | null)) setOpen(false);
      }}
    >
      <button
        ref={btn}
        type="button"
        className={`menu-btn${active ? ' is-active' : ''}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        aria-label={ariaLabel}
        onClick={() => setOpen((o) => !o)}
      >
        {label}
      </button>
      {open && (
        <div className="menu-pop" role="menu" id={id} onClick={onPopClick}>
          {children}
        </div>
      )}
    </div>
  );
}

export function MenuSep() {
  return <div className="menu-sep" role="separator" />;
}
