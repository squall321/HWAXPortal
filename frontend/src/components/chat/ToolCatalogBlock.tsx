// 도구 카탈로그 카드 — '/도구' 검색 응답(SSE tools)을 선택 UI 로 렌더. AI 추천을 그대로 쓰지 않고
// 사용자가 직접 변경/추가해 확정하면 대화의 지정 도구(pinnedTools)로 저장돼 이후 발화에 실린다.
import { useMemo, useState } from 'react';
import { useChat } from '../../state/ChatContext';
import type { ToolCatalog } from '../../types/chat';

const MAX_PINNED = 12;
const LIST_LIMIT = 30;

export function ToolCatalogBlock({ catalog }: { catalog: ToolCatalog }) {
  const { pinnedTools, setPinnedTools } = useChat();
  // 초안 선택 — 현재 지정 도구에서 시작(카드 재방문 시에도 상태 일치). 확정 전엔 저장 안 함.
  const [draft, setDraft] = useState<Set<string>>(() => new Set(pinnedTools));
  const [query, setQuery] = useState('');
  const [applied, setApplied] = useState(false);

  const toggle = (name: string) =>
    setDraft((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else if (next.size < MAX_PINNED) next.add(name);
      setApplied(false);
      return next;
    });

  const byName = useMemo(() => new Map(catalog.all.map((t) => [t.name, t])), [catalog.all]);
  const recNames = useMemo(() => new Set(catalog.recommended.map((t) => t.name)), [catalog.recommended]);

  // 검색 목록 — 검색어 없으면 추천 제외 전체(이름순), 있으면 이름/설명 부분일치.
  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    const pool = catalog.all.filter((t) => !recNames.has(t.name));
    if (!q) return pool.slice(0, LIST_LIMIT);
    return catalog.all
      .filter((t) => `${t.name} ${t.desc}`.toLowerCase().includes(q))
      .slice(0, LIST_LIMIT);
  }, [query, catalog.all, recNames]);

  const draftList = useMemo(() => [...draft], [draft]);
  const dirty = useMemo(() => {
    const cur = new Set(pinnedTools);
    return draft.size !== cur.size || draftList.some((n) => !cur.has(n));
  }, [draft, pinnedTools, draftList]);

  const apply = () => {
    setPinnedTools(draftList);
    setApplied(true);
  };

  return (
    <div className="tc-card">
      <div className="tc-head">
        <span className="tc-title">도구 선택</span>
        <span className="tc-badge">전체 {catalog.all.length}개</span>
        {catalog.query && <span className="tc-query">“{catalog.query}”</span>}
      </div>
      <p className="tc-note">
        추천은 참고일 뿐입니다 — 직접 확인하고 변경/추가한 뒤 적용하면 이 대화에서 그 도구를 우선 사용합니다.
      </p>

      {catalog.recommended.length > 0 && (
        <div className="tc-sec">
          <div className="tc-sec-title">질의 관련 추천</div>
          <ul className="tc-list">
            {catalog.recommended.map((t) => (
              <li key={t.name}>
                <label className="tc-item">
                  <input type="checkbox" checked={draft.has(t.name)} onChange={() => toggle(t.name)} />
                  <span className="tc-name">{t.name}</span>
                  <span className="tc-desc">{t.desc}</span>
                </label>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="tc-sec">
        <div className="tc-sec-title">직접 검색·추가</div>
        <input
          className="tc-search"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="이름·설명으로 검색 (예: warpage, voc, laminate, sed)"
          aria-label="도구 검색"
        />
        <ul className="tc-list tc-scroll">
          {results.length === 0 ? (
            <li className="tc-empty">일치하는 도구가 없습니다.</li>
          ) : (
            results.map((t) => (
              <li key={t.name}>
                <label className="tc-item">
                  <input type="checkbox" checked={draft.has(t.name)} onChange={() => toggle(t.name)} />
                  <span className="tc-name">{t.name}</span>
                  <span className="tc-desc">{t.desc}</span>
                </label>
              </li>
            ))
          )}
        </ul>
      </div>

      <div className="tc-foot">
        <span className="tc-count">
          선택 {draft.size}/{MAX_PINNED}
          {draft.size > 0 && (
            <span className="tc-chips">
              {draftList.map((n) => (
                <span key={n} className="tc-chip" title={byName.get(n)?.desc || n}>
                  {n}
                  <button type="button" className="tc-chip-x" onClick={() => toggle(n)} aria-label={`${n} 제외`}>
                    ×
                  </button>
                </span>
              ))}
            </span>
          )}
        </span>
        <span className="tc-actions">
          {draft.size > 0 && (
            <button type="button" className="tc-clear" onClick={() => { setDraft(new Set()); setApplied(false); }}>
              전체 해제
            </button>
          )}
          <button type="button" className="tc-apply" disabled={!dirty && !applied} onClick={apply}>
            {applied && !dirty ? '적용됨 ✓' : draft.size > 0 ? `이 도구 우선 사용 (${draft.size})` : '지정 해제 적용'}
          </button>
        </span>
      </div>
    </div>
  );
}
