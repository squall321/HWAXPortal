// 도구 카탈로그 카드 — '/도구' 검색 응답(SSE tools)을 선택 UI 로 렌더. AI 추천을 그대로 쓰지 않고
// 사용자가 직접 변경/추가해 확정하면 대화의 지정 도구(pinnedTools)로 저장돼 이후 발화에 실린다.
import { useMemo, useState } from 'react';
import { useChat } from '../../state/ChatContext';
import type { ToolApp, ToolCatalog } from '../../types/chat';

const MAX_PINNED = 12;
const MAX_APPS = 3;
const LIST_LIMIT = 30;

export function ToolCatalogBlock({ catalog }: { catalog: ToolCatalog }) {
  const { pinnedTools, setPinnedTools, pinnedApps, setPinnedApps } = useChat();
  // 초안 선택 — 현재 지정 도구에서 시작(카드 재방문 시에도 상태 일치). 확정 전엔 저장 안 함.
  const [draft, setDraft] = useState<Set<string>>(() => new Set(pinnedTools));
  const [appDraft, setAppDraft] = useState<Set<string>>(() => new Set(pinnedApps));
  const [query, setQuery] = useState('');
  const [group, setGroup] = useState('');   // 소유 MCP 앱 필터(계층 1단)
  const [applied, setApplied] = useState(false);

  const toggle = (name: string) =>
    setDraft((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else if (next.size < MAX_PINNED) next.add(name);
      setApplied(false);
      return next;
    });

  const toggleApp = (key: string) =>
    setAppDraft((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else if (next.size < MAX_APPS) next.add(key);
      setApplied(false);
      return next;
    });

  const byName = useMemo(() => new Map(catalog.all.map((t) => [t.name, t])), [catalog.all]);
  const recNames = useMemo(() => new Set(catalog.recommended.map((t) => t.name)), [catalog.recommended]);

  // 앱(소유 MCP) 목록 — 도구 166개를 평평하게 훑지 않고 '어느 앱의 기능인지'로 먼저 좁힌다.
  // 서버가 apps[] 를 주면 그대로 쓴다(설명이 붙는다). 구 서버 응답은 all[].group 으로 재구성.
  const apps: ToolApp[] = useMemo(() => {
    if (catalog.apps?.length) return catalog.apps;
    const m = new Map<string, ToolApp>();
    for (const t of catalog.all) {
      const k = t.group || '';
      if (!k) continue;
      const cur = m.get(k);
      if (cur) cur.tool_count += 1;
      else m.set(k, { app: k, label: t.group_label || k, tool_count: 1 });
    }
    return [...m.values()].sort((a, b) => b.tool_count - a.tool_count);
  }, [catalog.apps, catalog.all]);
  const appLabel = useMemo(() => new Map(apps.map((a) => [a.app, a.label])), [apps]);

  // 검색 목록 — 앱 필터 + 검색어(둘 다 없으면 추천 제외 전체).
  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    let pool = catalog.all;
    if (group) pool = pool.filter((t) => t.group === group);
    if (q) return pool.filter((t) => `${t.name} ${t.desc}`.toLowerCase().includes(q)).slice(0, LIST_LIMIT);
    if (!group) pool = pool.filter((t) => !recNames.has(t.name));
    return pool.slice(0, LIST_LIMIT);
  }, [query, group, catalog.all, recNames]);

  const draftList = useMemo(() => [...draft], [draft]);
  const appList = useMemo(() => [...appDraft], [appDraft]);
  const dirty = useMemo(() => {
    const cur = new Set(pinnedTools);
    const curApps = new Set(pinnedApps);
    return (
      draft.size !== cur.size || draftList.some((n) => !cur.has(n)) ||
      appDraft.size !== curApps.size || appList.some((k) => !curApps.has(k))
    );
  }, [draft, pinnedTools, draftList, appDraft, pinnedApps, appList]);

  // 앱 선택으로 실제 몇 개의 도구가 우선되는지 — 개수를 안 보여주면 앱 선택의 효과가 안 보인다.
  const appToolCount = useMemo(
    () => apps.filter((a) => appDraft.has(a.app)).reduce((n, a) => n + a.tool_count, 0),
    [apps, appDraft],
  );

  const apply = () => {
    setPinnedApps(appList);
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
        앱을 고르면 그 앱의 기능 전체를 우선 사용합니다. 특정 기능만 콕 집고 싶을 때만 아래에서 개별 선택하세요.
      </p>

      <div className="tc-sec">
        <div className="tc-sec-title">
          앱으로 선택 — 무엇을 하는 앱인지로 고른다 (최대 {MAX_APPS}개)
        </div>
        <ul className="tc-apps">
          {apps.map((a) => {
            const on = appDraft.has(a.app);
            const full = !on && appDraft.size >= MAX_APPS;
            return (
              <li key={a.app}>
                <label className={`tc-app-card${on ? ' is-on' : ''}${full ? ' is-off' : ''}`}>
                  <input type="checkbox" checked={on} disabled={full} onChange={() => toggleApp(a.app)} />
                  <span className="tc-app-body">
                    <span className="tc-app-head">
                      <span className="tc-app-name">{a.label}</span>
                      <span className="tc-app-n">기능 {a.tool_count}개</span>
                    </span>
                    {a.desc && <span className="tc-app-desc">{a.desc}</span>}
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      </div>

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
        <div className="tc-sec-title">개별 기능으로 선택 — 콕 집어야 할 때만</div>
        <select className="tc-group" value={group} onChange={(e) => setGroup(e.target.value)} aria-label="MCP 앱 선택">
          <option value="">전체 앱 ({catalog.all.length}개 도구)</option>
          {apps.map((a) => (
            <option key={a.app} value={a.app}>
              {a.label} ({a.tool_count})
            </option>
          ))}
        </select>
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
                  {!group && t.group_label && <span className="tc-app">{t.group_label}</span>}
                  <span className="tc-desc">{t.desc}</span>
                </label>
              </li>
            ))
          )}
        </ul>
      </div>

      <div className="tc-foot">
        <span className="tc-count">
          {appDraft.size > 0 && (
            <span className="tc-chips">
              {appList.map((k) => (
                <span key={k} className="tc-chip tc-chip-app" title={`${appLabel.get(k) || k} 전체`}>
                  {appLabel.get(k) || k}
                  <button type="button" className="tc-chip-x" onClick={() => toggleApp(k)} aria-label={`${appLabel.get(k) || k} 제외`}>
                    ×
                  </button>
                </span>
              ))}
            </span>
          )}
          앱 {appDraft.size}/{MAX_APPS}
          {appToolCount > 0 && ` (기능 ${appToolCount}개)`} · 개별 {draft.size}/{MAX_PINNED}
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
          {(draft.size > 0 || appDraft.size > 0) && (
            <button type="button" className="tc-clear" onClick={() => { setDraft(new Set()); setAppDraft(new Set()); setApplied(false); }}>
              전체 해제
            </button>
          )}
          <button type="button" className="tc-apply" disabled={!dirty && !applied} onClick={apply}>
            {applied && !dirty
              ? '적용됨 ✓'
              : appDraft.size > 0 || draft.size > 0
                ? `우선 사용 (기능 ${appToolCount + draft.size}개)`
                : '지정 해제 적용'}
          </button>
        </span>
      </div>
    </div>
  );
}
