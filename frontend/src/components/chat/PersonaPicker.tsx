// 대화 중 전문가 바꾸기 — 오른쪽 레일에서 여는 가벼운 선택기. 더 볼 게 필요하면 조직도로 넘긴다
import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { fetchDeliberateExperts, type RecommendedExpert } from '../../api/chat.api';
import { useChat } from '../../state/ChatContext';
import { colorOf, initialOf, shortName } from './personaColor';
import { domainLabel, domainOf, matches } from './personaCatalog';
import { usePersonaPool } from './usePersonaPool';

const LOCAL_LIMIT = 12;

export function PersonaPicker({ onClose, onExpand }: { onClose: () => void; onExpand: () => void }) {
  const { pinnedAgent, pinnedAgentName, setPinnedAgent } = useChat();
  const { pool, loading, failed } = usePersonaPool();
  const [q, setQ] = useState('');
  // 주제 추천(서버) — 이름이 안 떠오를 때 "무엇을 물을지"로 찾는 길이다.
  const [rec, setRec] = useState<{ q: string; list: RecommendedExpert[] } | null>(null);
  const [recLoading, setRecLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const hits = useMemo(
    () => (q.trim() ? pool.filter((a) => matches(a, q)).slice(0, LOCAL_LIMIT) : []),
    [pool, q],
  );

  useEffect(() => {
    inputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const recommend = async () => {
    const topic = q.trim();
    if (!topic || recLoading) return;
    setRecLoading(true);
    const r = await fetchDeliberateExperts(topic);
    setRec({ q: topic, list: (r.candidates?.length ? r.candidates : r.recommended).slice(0, 6) });
    setRecLoading(false);
  };

  const pick = (key: string, name: string) => {
    setPinnedAgent(key, name);
    onClose();
  };

  const row = (key: string, name: string, sub?: string) => (
    <li key={key}>
      <button
        type="button"
        className={`pp-row${pinnedAgent === key ? ' is-on' : ''}`}
        onClick={() => pick(key, name)}
      >
        <span className="pp-av" style={{ background: colorOf(name) }}>
          {initialOf(name)}
        </span>
        <span className="pp-row-body">
          <span className="pp-row-name" title={name}>{shortName(name)}</span>
          <span className="pp-row-sub">{sub || `${domainLabel(domainOf(key))} · ${key}`}</span>
        </span>
      </button>
    </li>
  );

  return createPortal(
    <div className="pp-backdrop" onClick={onClose}>
      <div
        className="pp-card"
        role="dialog"
        aria-modal="true"
        aria-label="전문가 고르기"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="pp-head">
          <span className="pp-title">전문가 고르기</span>
          <button type="button" className="pp-x" onClick={onClose} aria-label="닫기">
            ×
          </button>
        </div>

        {pinnedAgent && (
          <div className="pp-current">
            <span className="pp-current-k">지금</span>
            <b title={pinnedAgentName || pinnedAgent}>{shortName(pinnedAgentName || pinnedAgent)}</b>
            <button
              type="button"
              className="pp-clear"
              onClick={() => {
                setPinnedAgent(null);
                onClose();
              }}
            >
              해제
            </button>
          </div>
        )}

        <input
          ref={inputRef}
          className="pp-search"
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.nativeEvent.isComposing) {
              e.preventDefault();
              void recommend();
            }
          }}
          placeholder="이름·키워드 (Enter: 이 주제를 맡을 전문가 추천)"
          aria-label="전문가 검색"
        />

        <div className="pp-body">
          {loading && <p className="pp-empty">전문가 목록 불러오는 중…</p>}
          {failed && <p className="pp-empty">목록을 불러오지 못했습니다.</p>}

          {recLoading && <p className="pp-empty">‘{q.trim()}’ 을(를) 맡을 전문가를 찾는 중…</p>}
          {rec && rec.list.length > 0 && (
            <>
              <div className="pp-sec">‘{rec.q}’ 주제 추천</div>
              <ul className="pp-list">{rec.list.map((r) => row(r.key, r.name, r.role))}</ul>
            </>
          )}
          {rec && rec.list.length === 0 && !recLoading && (
            <p className="pp-empty">그 주제를 맡을 전문가를 찾지 못했습니다.</p>
          )}

          {q.trim() && (
            <>
              <div className="pp-sec">이름·태그 일치 {hits.length > 0 && `${hits.length}명`}</div>
              {hits.length === 0 ? (
                <p className="pp-empty">일치 없음 — Enter 로 주제 추천을 받아 보세요.</p>
              ) : (
                <ul className="pp-list">{hits.map((a) => row(a.key, a.name))}</ul>
              )}
            </>
          )}

          {!q.trim() && !rec && !loading && (
            <p className="pp-hint">
              이름이나 키워드로 찾거나, 물어볼 주제를 적고 Enter 를 눌러 추천을 받으세요.
              전체 {pool.length}명을 분야별로 훑어보려면 아래 조직도를 여세요.
            </p>
          )}
        </div>

        <button type="button" className="pp-expand" onClick={onExpand}>
          전체 조직도 열기 ⤢
        </button>
      </div>
    </div>,
    document.body,
  );
}
