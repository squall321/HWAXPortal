// 챗 시작 전 전문가·도구 선택 패널 — 전문가(1명)는 조직도 전창에서, 도구는 앱(≤3)·개별(≤12)로
// 고른다. 고른 전문가의 상세(역할·태그·샘플질의·보유 지식)는 UI 로 보여준다 — LLM 텍스트 나열은
// 절단되므로 탐색은 결정적 데이터로 그린다.
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  fetchAgentDetail,
  fetchDeliberateExperts,
  type AgentDetail,
  type ExpertsResponse,
  type PoolExpert,
} from '../../api/chat.api';
import { useChat } from '../../state/ChatContext';
import { useCan } from '../../auth/useCan';
import { PersonaBrowser } from './PersonaBrowser';
import { ToolAreaChips } from './ToolAreaChips';
import { inArea, toolAreasOf } from './toolAreas';

const MAX_TOOLS = 12; // 챗 pinned_tools 상한
const MAX_APPS = 3;   // 챗 pinned_apps 상한 — 앱 하나가 도구 20~30개다

export function StartPicker({ onClose }: { onClose: () => void }) {
  const { pinnedTools, setPinnedTools, pinnedApps, setPinnedApps, pinnedAgent, setPinnedAgent, setInput } = useChat();
  // 전문가 칸은 '전문가와 대화' 권한이 있어야 보인다 — 도구·앱 고르기는 누구나(docs/access-control).
  const canExperts = useCan()('feat:expert-chat');
  const [res, setRes] = useState<ExpertsResponse | null>(null);
  const [agentSel, setAgentSel] = useState<string | null>(pinnedAgent);
  const [toolSel, setToolSel] = useState<Set<string>>(() => new Set(pinnedTools));
  const [appSel, setAppSel] = useState<Set<string>>(() => new Set(pinnedApps));
  const [toolFilter, setToolFilter] = useState('');
  const [toolGroup, setToolGroup] = useState('');   // 소유 MCP 앱 필터(2단)
  const [toolArea, setToolArea] = useState<string | null>(null);   // 영역(하는 일) 필터(1단)
  const [browse, setBrowse] = useState(false);   // 조직도 전창(분야→그룹→사람)
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const selKeyRef = useRef<string | null>(pinnedAgent);

  // 열자마자 전체 풀·도구 카탈로그 로드 — 조직도와 앱 목록이 이 응답 하나로 선다.
  useEffect(() => {
    let cancelled = false;
    void fetchDeliberateExperts('전체 카탈로그 조회').then((r) => {
      if (!cancelled) setRes((cur) => cur ?? r);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const pool = useMemo(() => res?.pool ?? [], [res]);

  // 키 → 사람 이름. 지정 시 표시용 이름을 함께 실어야 칩·말풍선이 키를 안 보여 준다.
  const nameOf = (key: string) => pool.find((a) => a.key === key)?.name ?? key;

  const toolAll = useMemo(() => res?.tools?.all ?? [], [res]);
  // 앱 목록 — 서버가 주면 그대로(설명 포함), 구 서버 응답이면 도구의 group 으로 재구성.
  const toolApps = useMemo(() => {
    const given = res?.tools?.apps;
    if (given?.length) return given;
    const m = new Map<string, { app: string; label: string; desc?: string; tool_count: number }>();
    for (const t of toolAll) {
      const k = t.group || '';
      if (!k) continue;
      const c = m.get(k);
      if (c) c.tool_count += 1;
      else m.set(k, { app: k, label: t.group_label || k, tool_count: 1 });
    }
    return [...m.values()].sort((a, b) => b.tool_count - a.tool_count);
  }, [res, toolAll]);
  const toolAreas = useMemo(() => toolAreasOf(toolAll, res?.tools?.areas), [toolAll, res]);
  // 영역(1단) → 앱(2단) → 검색어. 앱 드롭다운은 고른 영역 안의 앱만 영역 안 개수로 센다.
  const toolAppsInArea = useMemo(() => {
    if (toolArea === null) return toolApps;
    const n = new Map<string, number>();
    for (const t of toolAll) if (inArea(t, toolArea) && t.group) n.set(t.group, (n.get(t.group) || 0) + 1);
    return toolApps.filter((a) => n.has(a.app)).map((a) => ({ ...a, tool_count: n.get(a.app) || 0 }));
  }, [toolApps, toolArea, toolAll]);
  // 잘린 수를 같이 돌려준다 — 영역 하나에 70개가 있는데 15개만 보이면 나머지는 없는 줄 안다.
  const { toolResults, toolHidden } = useMemo(() => {
    const q = toolFilter.trim().toLowerCase();
    let pool = toolAll.filter((t) => inArea(t, toolArea));
    if (toolGroup) pool = pool.filter((t) => t.group === toolGroup);
    if (q) pool = pool.filter((t) => `${t.name} ${t.desc}`.toLowerCase().includes(q));
    else if (!toolGroup && toolArea === null) return { toolResults: [], toolHidden: 0 };
    return { toolResults: pool.slice(0, 15), toolHidden: Math.max(0, pool.length - 15) };
  }, [toolFilter, toolGroup, toolArea, toolAll]);
  const pickToolArea = (a: string | null) => {
    setToolArea(a);
    if (toolGroup && a !== null && !toolAll.some((t) => t.group === toolGroup && inArea(t, a))) setToolGroup('');
  };

  const toggleApp = (key: string) =>
    setAppSel((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else if (next.size < MAX_APPS) next.add(key);
      return next;
    });

  const toggleTool = (name: string) =>
    setToolSel((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else if (next.size < MAX_TOOLS) next.add(name);
      return next;
    });

  // 전문가 선택 + 상세(역할·지식) 로드 — 재클릭 시 해제.
  // ⚠ 상세는 콜드에 6~11초 걸린다. 연달아 누르면 늦게 온 응답이 **다른 사람의 상세**로 화면을
  //   덮어, 라디오는 C 에 있는데 설명은 A 인 상태가 된다(감사 실측). 지금 선택과 같을 때만 반영.
  const showAgent = (key: string) => {
    setAgentSel(key);
    selKeyRef.current = key;
    setDetail(null);
    setDetailLoading(true);
    void fetchAgentDetail(key).then((d) => {
      if (selKeyRef.current !== d.key) return;
      setDetail(d);
      setDetailLoading(false);
    });
  };
  // 확정은 전문가·앱·도구를 한 번에 — 조직도 샘플 질의로 곧장 시작할 때는 방금 고른 키를 받는다
  // (setAgentSel 은 이 렌더에 반영되지 않는다).
  const applyWith = (key: string | null) => {
    setPinnedAgent(key, key ? nameOf(key) : undefined);
    setPinnedApps([...appSel]);
    setPinnedTools([...toolSel]);
    onClose();
  };
  const apply = () => applyWith(agentSel);

  // 조직도에서 고르면 여기로 돌아온다 — 담아 두고(확정은 아래 버튼), 샘플 질의를 눌렀으면 그대로 시작.
  const pickFromOrg = (a: PoolExpert, sample?: string) => {
    if (!sample) {
      showAgent(a.key);
      return;
    }
    setInput(sample);
    applyWith(a.key);
  };

  return (
    <div className="sp-card">
      <div className="sp-head">
        <span className="sp-title">전문가·도구 고르고 시작</span>
        <button type="button" className="sp-close" onClick={onClose} aria-label="닫기">
          ×
        </button>
      </div>
      <p className="sp-note">
        전문가는 조직도에서, 도구는 앱으로 고르세요. 고른 전문가의 역할·보유 지식은 아래에
        보입니다. 고르지 않고 그냥 대화해도 됩니다.
      </p>

      {res?.error && <p className="sp-warn">조회 실패({res.error}) — 다시 시도하세요.</p>}
      {!res && <p className="sp-empty">카탈로그 로딩 중…</p>}

      {res && (
        <div className="sp-cols">
          {canExperts && (
          <div className="sp-col">
            <div className="sp-sec-title">
              전문가 {pool.length > 0 && <span className="sp-dim">(전체 {pool.length}명)</span>}
            </div>
            {/* 전문가는 조직도에서만 고른다 — 여기 있던 목록(추천 10명)은 더미 질의 결과인데다
                이름이 한 줄을 넘겨, 시작 화면을 길게 만들면서 고르는 데는 도움이 안 됐다. */}
            <button type="button" className="sp-browse" onClick={() => setBrowse(true)}>
              🗂 조직도에서 고르기 <span className="sp-dim">— 분야·그룹으로 훑어보기</span>
            </button>
            {agentSel && (
              <button type="button" className="sp-clear" onClick={() => setAgentSel(null)}>
                전문가 해제
              </button>
            )}
          </div>
          )}
          <div className="sp-col">
            <div className="sp-sec-title">
              앱 (선택 {appSel.size}/{MAX_APPS}) — 앱을 고르면 그 기능 전체를 우선 사용
            </div>
            <ul className="tc-apps sp-apps">
              {toolApps.map((a) => {
                const on = appSel.has(a.app);
                const full = !on && appSel.size >= MAX_APPS;
                return (
                  <li key={a.app}>
                    <label className={`tc-app-card${on ? ' is-on' : ''}${full ? ' is-off' : ''}`} title={a.desc}>
                      <input type="checkbox" checked={on} disabled={full} onChange={() => toggleApp(a.app)} />
                      <span className="tc-app-body">
                        <span className="tc-app-head">
                          <span className="tc-app-name">{a.label}</span>
                          <span className="tc-app-n">{a.tool_count}</span>
                        </span>
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
            {/* 개별 도구는 찾아서 고른다 — 늘 펼쳐 두던 '추천 8개'도 더미 질의 결과였다. */}
            <div className="sp-sec-title">개별 도구 (선택 {toolSel.size}/{MAX_TOOLS}) — 영역·앱·검색으로 찾기</div>
            <ToolAreaChips areas={toolAreas} value={toolArea} onChange={pickToolArea} />
            <select className="sp-domain" value={toolGroup} onChange={(e) => setToolGroup(e.target.value)} aria-label="MCP 앱 선택">
              <option value="">
                앱 선택… ({toolArea === null ? `전체 ${toolAll.length}` : `이 영역 ${toolAppsInArea.reduce((n, a) => n + a.tool_count, 0)}`}개)
              </option>
              {toolAppsInArea.map((a) => (
                <option key={a.app} value={a.app}>{a.label} ({a.tool_count})</option>
              ))}
            </select>
            <input
              className="sp-search sp-search-sm"
              type="text"
              value={toolFilter}
              onChange={(e) => setToolFilter(e.target.value)}
              placeholder={`전체 ${toolAll.length}개 도구 검색`}
              aria-label="도구 검색"
            />
            {(toolFilter.trim() || toolGroup || toolArea !== null) && (
              <ul className="sp-list sp-scroll">
                {toolResults.length === 0 ? (
                  <li className="sp-empty">일치 없음</li>
                ) : (
                  toolResults.map((t) => (
                    <li key={t.name}>
                      <label className="sp-item" title={t.desc}>
                        <input type="checkbox" checked={toolSel.has(t.name)} onChange={() => toggleTool(t.name)} />
                        <span className="sp-name sp-mono">{t.name}</span>
                        {toolArea === null && t.area_label && <span className="cx-ep-area">{t.area_label}</span>}
                      </label>
                    </li>
                  ))
                )}
                {toolHidden > 0 && <li className="sp-empty">… {toolHidden}개 더 — 앱을 고르거나 검색으로 좁히세요.</li>}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* 전문가 상세 — 역할·태그·샘플질의·보유 지식(레코드). 선택 확인 후 페르소나로 시작. */}
      {agentSel && (
        <div className="sp-detail">
          {detailLoading ? (
            <p className="sp-empty">상세 로딩 중…</p>
          ) : detail ? (
            <>
              <div className="sp-detail-name">👤 {detail.name}</div>
              {detail.role && <p className="sp-detail-role">{detail.role}</p>}
              {detail.tags.length > 0 && (
                <p className="sp-dim">태그: {detail.tags.slice(0, 12).join(' · ')}</p>
              )}
              {detail.samples.length > 0 && (
                <>
                  <div className="sp-sub sp-dim">이런 걸 물을 수 있어요</div>
                  <ul className="sp-detail-list">
                    {detail.samples.slice(0, 3).map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </>
              )}
              {detail.records.length > 0 && (
                <>
                  <div className="sp-sub sp-dim">보유 지식 ({detail.records.length}건)</div>
                  <ul className="sp-detail-list sp-scroll">
                    {detail.records.map((r) => (
                      <li key={r.id || r.title}>
                        {r.title}
                        {r.data_type && <span className="sp-dim"> [{r.data_type}]</span>}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </>
          ) : null}
        </div>
      )}

      <div className="sp-foot">
        <span className="sp-summary">
          {agentSel ? `👤 ${agentSel}` : '전문가 미지정'}
          {toolSel.size > 0 && ` · 🔧 ${toolSel.size}개`}
        </span>
        <button type="button" className="sp-apply" onClick={apply}>
          적용하고 대화 시작
        </button>
      </div>

      {/* 조직도는 고르기만 하고 돌아온다 — 확정은 위 '적용하고 대화 시작'에서 도구·앱과 함께. */}
      {browse && (
        <PersonaBrowser
          onClose={() => setBrowse(false)}
          onPick={pickFromOrg}
          picked={agentSel}
        />
      )}
    </div>
  );
}
