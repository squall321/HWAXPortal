// 대화 이력 사이드바 — 시간대별 그룹핑(오늘/어제/…), 새 대화·이름변경·2단계 삭제, 접기 토글
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { useChat } from '../../state/ChatContext';
import type { Conversation } from '../../types/chat';
import { IconCheck, IconPanel, IconPencil, IconPlus, IconTrash } from './icons';

const DAY = 24 * 60 * 60 * 1000;

function groupLabel(ts: number): string {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  if (ts >= startOfToday) return '오늘';
  if (ts >= startOfToday - DAY) return '어제';
  if (ts >= startOfToday - 7 * DAY) return '지난 7일';
  if (ts >= startOfToday - 30 * DAY) return '지난 30일';
  return '이전';
}

function SidebarItem({
  conv,
  active,
  onNavigate,
}: {
  conv: Conversation;
  active: boolean;
  onNavigate?: () => void;
}) {
  const { selectConversation, deleteConversation, renameConversation } = useChat();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(conv.title);
  // 2단계 삭제 — 첫 클릭으로 무장(armed), 2.5초 내 재클릭 시 삭제.
  const [armed, setArmed] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  useEffect(() => {
    if (!armed) return;
    const t = window.setTimeout(() => setArmed(false), 2500);
    return () => window.clearTimeout(t);
  }, [armed]);

  const commitRename = () => {
    renameConversation(conv.id, draft);
    setEditing(false);
  };

  const onEditKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.nativeEvent.isComposing) commitRename();
    else if (e.key === 'Escape') {
      setDraft(conv.title);
      setEditing(false);
    }
  };

  if (editing) {
    return (
      <div className={`sb-item editing${active ? ' active' : ''}`}>
        <input
          ref={inputRef}
          className="sb-rename"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onEditKey}
          onBlur={commitRename}
          aria-label="대화 이름 변경"
        />
      </div>
    );
  }

  return (
    <div
      className={`sb-item${active ? ' active' : ''}`}
      onMouseLeave={() => setArmed(false)}
      aria-current={active ? 'true' : undefined}
    >
      <button
        type="button"
        className="sb-item-title"
        onClick={() => {
          selectConversation(conv.id);
          onNavigate?.();
        }}
        title={conv.title}
      >
        {conv.title}
      </button>
      <div className="sb-item-actions">
        <button
          type="button"
          className="sb-icon"
          aria-label="이름 변경"
          title="이름 변경"
          onClick={() => {
            setDraft(conv.title);
            setEditing(true);
          }}
        >
          <IconPencil width={13} height={13} />
        </button>
        <button
          type="button"
          className={`sb-icon${armed ? ' danger' : ''}`}
          aria-label={armed ? '삭제 확인' : '삭제'}
          title={armed ? '한 번 더 누르면 삭제됩니다' : '삭제'}
          onClick={() => {
            if (armed) deleteConversation(conv.id);
            else setArmed(true);
          }}
        >
          {armed ? <IconCheck width={13} height={13} /> : <IconTrash width={13} height={13} />}
        </button>
      </div>
    </div>
  );
}

export function ChatSidebar({
  open,
  onToggle,
  onNavigate,
}: {
  open: boolean;
  onToggle: () => void;
  onNavigate?: () => void;
}) {
  const { conversations, activeId, newConversation } = useChat();

  // updatedAt 내림차순 정렬 후 시간대 라벨로 그룹핑(라벨 등장 순서 유지).
  const groups = useMemo(() => {
    const sorted = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt);
    const out: { label: string; items: Conversation[] }[] = [];
    for (const c of sorted) {
      const label = groupLabel(c.updatedAt);
      const last = out[out.length - 1];
      if (last && last.label === label) last.items.push(c);
      else out.push({ label, items: [c] });
    }
    return out;
  }, [conversations]);

  return (
    <aside className={`cx-sidebar${open ? ' open' : ''}`} aria-label="대화 이력" aria-hidden={!open}>
      <div className="sb-inner">
        <div className="sb-head">
          <span className="sb-brand">HWAX</span>
          <button
            type="button"
            className="sb-icon sb-collapse"
            onClick={onToggle}
            aria-label="사이드바 접기"
            title="사이드바 접기"
            tabIndex={open ? 0 : -1}
          >
            <IconPanel width={16} height={16} />
          </button>
        </div>

        <button
          type="button"
          className="sb-new"
          onClick={() => {
            newConversation();
            onNavigate?.();
          }}
          tabIndex={open ? 0 : -1}
        >
          <IconPlus width={15} height={15} />
          <span>새 대화</span>
        </button>

        <nav className="sb-list">
          {groups.length === 0 && <div className="sb-empty">아직 대화가 없습니다</div>}
          {groups.map((g) => (
            <div key={g.label} className="sb-group">
              <div className="sb-group-label">{g.label}</div>
              {g.items.map((c) => (
                <SidebarItem key={c.id} conv={c} active={c.id === activeId} onNavigate={onNavigate} />
              ))}
            </div>
          ))}
        </nav>

        <div className="sb-foot">대화는 이 브라우저에만 저장됩니다</div>
      </div>
    </aside>
  );
}
