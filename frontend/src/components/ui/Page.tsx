// 페이지 뼈대 — 폭 두 등급(read 880 · wide 1200)과 공통 페이지 머리. 메뉴를 누를 때마다 제목 위치·크기가 튀던 것을 하나로(docs/ui-refresh 단계 2)
import type { ReactNode } from 'react';

export function Page({ width = 'read', className = '', children }: {
  width?: 'read' | 'wide';
  className?: string;
  children: ReactNode;
}) {
  return <div className={`page-${width} ${className}`}>{children}</div>;
}

export function PageHeader({ title, desc, actions }: { title: ReactNode; desc?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="page-header">
      <div className="page-header-text">
        <h1>{title}</h1>
        {desc && <p>{desc}</p>}
      </div>
      {actions && <div className="page-header-actions">{actions}</div>}
    </header>
  );
}
