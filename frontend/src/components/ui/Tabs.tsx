// 탭 — 한 화면에 성격이 다른 묶음을 나눠 담는다(APG 탭 패턴: 화살표·Home·End 로 옮기면 바로 연다). 지금 탭의 패널 하나만 그린다(docs/ui-refresh 단계 3)
import { type KeyboardEvent, type ReactNode, useId, useRef } from 'react';
import '../../styles/ui.css';

export type TabItem<K extends string> = { key: K; label: ReactNode; count?: number };

export function Tabs<K extends string>({
  tabs,
  value,
  onChange,
  label,
  children,
}: {
  tabs: TabItem<K>[];
  value: K;
  onChange: (key: K) => void;
  label: string;
  children: ReactNode;
}) {
  const base = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const at = tabs.findIndex((t) => t.key === value);

  const onKey = (e: KeyboardEvent) => {
    const last = tabs.length - 1;
    const next =
      e.key === 'ArrowRight'
        ? (at + 1) % tabs.length
        : e.key === 'ArrowLeft'
          ? (at - 1 + tabs.length) % tabs.length
          : e.key === 'Home'
            ? 0
            : e.key === 'End'
              ? last
              : -1;
    if (next < 0) return;
    e.preventDefault();
    onChange(tabs[next].key);
    refs.current[next]?.focus();
  };

  return (
    <>
      <div className="tabs" role="tablist" aria-label={label} onKeyDown={onKey}>
        {tabs.map((t, i) => {
          const on = t.key === value;
          return (
            <button
              key={t.key}
              ref={(el) => {
                refs.current[i] = el;
              }}
              type="button"
              role="tab"
              id={`${base}-tab-${t.key}`}
              className="tab"
              aria-selected={on}
              // 그리는 패널은 지금 탭 것 하나뿐이라 그 탭만 패널을 가리킨다
              aria-controls={on ? `${base}-panel` : undefined}
              tabIndex={on ? 0 : -1}
              onClick={() => onChange(t.key)}
            >
              {t.label}
              {t.count !== undefined && <span className="tab-count">{t.count}</span>}
            </button>
          );
        })}
      </div>
      <div
        role="tabpanel"
        id={`${base}-panel`}
        aria-labelledby={`${base}-tab-${value}`}
        className="tab-panel"
      >
        {children}
      </div>
    </>
  );
}
