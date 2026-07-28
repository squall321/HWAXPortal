// 챗 시작 전 전문가·도구 선택 패널 — 검색 + 분야별 계층 브라우즈로 전문가(1명, 페르소나)와
// 도구(≤12)를 직접 골라 대화를 구성한다. 전문가 클릭 시 상세(역할·태그·샘플질의·보유 지식)를
// UI 로 보여준다 — LLM 텍스트 나열은 절단되므로 탐색은 결정적 데이터로 그린다.
import { useEffect, useMemo, useState } from 'react';
import {
  fetchAgentDetail,
  fetchDeliberateExperts,
  type AgentDetail,
  type ExpertsResponse,
} from '../../api/chat.api';
import { useChat } from '../../state/ChatContext';

const MAX_TOOLS = 12; // 챗 pinned_tools 상한
const LIST_LIMIT = 10;

export function StartPicker({ onClose }: { onClose: () => void }) {
  const { pinnedTools, setPinnedTools, pinnedAgent, setPinnedAgent } = useChat();
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<ExpertsResponse | null>(null);
  const [agentSel, setAgentSel] = useState<string | null>(pinnedAgent);
  const [toolSel, setToolSel] = useState<Set<string>>(() => new Set(pinnedTools));
  const [toolFilter, setToolFilter] = useState('');
  const [toolGroup, setToolGroup] = useState('');   // 소유 MCP 앱 필터
  const [domain, setDomain] = useState('');
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // 열자마자 전체 풀·도구 카탈로그 로드 — 검색 없이도 분야별 브라우즈가 되게.
  useEffect(() => {
    let cancelled = false;
    void fetchDeliberateExperts('전체 카탈로그 조회').then((r) => {
      if (!cancelled) setRes((cur) => cur ?? r);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const search = async () => {
    const q = query.trim();
    if (!q || loading) return;
    setLoading(true);
    const r = await fetchDeliberateExperts(q);
    setRes(r);
    setLoading(false);
  };

  const pool = useMemo(() => res?.pool ?? [], [res]);
  // 분야 = 키 접두어(cam/mech/rel/…) — 계층 브라우즈의 1단.
  const domains = useMemo(() => {
    const m = new Map<string, number>();
    for (const a of pool) {
      const d = a.key.split('-')[0] || '기타';
      m.set(d, (m.get(d) ?? 0) + 1);
    }
    return [...m.entries()].sort((x, y) => y[1] - x[1]);
  }, [pool]);
  const domainAgents = useMemo(
    () => (domain ? pool.filter((a) => a.key.startsWith(domain + '-') || a.key === domain) : []),
    [pool, domain],
  );

  const experts = useMemo(() => {
    const ranked = res?.candidates?.length ? res.candidates : (res?.recommended ?? []);
    return ranked.slice(0, LIST_LIMIT);
  }, [res]);

  const toolAll = useMemo(() => res?.tools?.all ?? [], [res]);
  const toolRec = res?.tools?.recommended ?? [];
  const toolGroups = useMemo(() => {
    const m = new Map<string, { label: string; n: number }>();
    for (const t of toolAll) {
      const k = t.group || '';
      if (!k) continue;
      const c = m.get(k);
      if (c) c.n += 1; else m.set(k, { label: t.group_label || k, n: 1 });
    }
    return [...m.entries()].sort((a, b) => b[1].n - a[1].n);
  }, [toolAll]);
  // 앱으로 먼저 좁히고(계층 1단) 그 안에서 검색 — 평평한 166개 훑기를 피한다.
  const toolResults = useMemo(() => {
    const q = toolFilter.trim().toLowerCase();
    let pool = toolAll;
    if (toolGroup) pool = pool.filter((t) => t.group === toolGroup);
    if (!q) return toolGroup ? pool.slice(0, 15) : [];
    return pool.filter((t) => `${t.name} ${t.desc}`.toLowerCase().includes(q)).slice(0, 15);
  }, [toolFilter, toolGroup, toolAll]);

  const toggleTool = (name: string) =>
    setToolSel((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else if (next.size < MAX_TOOLS) next.add(name);
      return next;
    });

  // 전문가 선택 + 상세(역할·지식) 로드 — 재클릭 시 해제.
  const pickAgent = (key: string) => {
    if (agentSel === key) {
      setAgentSel(null);
      return;
    }
    setAgentSel(key);
    setDetail(null);
    setDetailLoading(true);
    void fetchAgentDetail(key).then((d) => {
      setDetail(d);
      setDetailLoading(false);
    });
  };

  const apply = () => {
    setPinnedAgent(agentSel);
    setPinnedTools([...toolSel]);
    onClose();
  };

  const agentRow = (key: string, label: string) => (
    <label className="sp-item">
      <input type="radio" name="sp-agent" checked={agentSel === key} onChange={() => {}} onClick={() => pickAgent(key)} />
      <span className="sp-name">{label}</span>
    </label>
  );

  return (
    <div className="sp-card">
      <div className="sp-head">
        <span className="sp-title">전문가·도구 고르고 시작</span>
        <button type="button" className="sp-close" onClick={onClose} aria-label="닫기">
          ×
        </button>
      </div>
      <p className="sp-note">
        검색하거나 분야로 훑어 전문가(페르소나 1명)와 우선 도구를 고르세요. 전문가를 클릭하면
        역할·보유 지식이 보입니다. 고르지 않고 그냥 대화해도 됩니다.
      </p>
      <div className="sp-search-row">
        <input
          className="sp-search"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.nativeEvent.isComposing) {
              e.preventDefault();
              void search();
            }
          }}
          placeholder="주제·키워드 검색 (예: PCB 휨, 배터리 스웰링, 열충격 SED)"
          aria-label="전문가·도구 검색"
        />
        <button type="button" className="sp-go" onClick={() => void search()} disabled={loading || !query.trim()}>
          {loading ? '검색 중…' : '검색'}
        </button>
      </div>

      {res?.error && <p className="sp-warn">조회 실패({res.error}) — 다시 시도하세요.</p>}
      {!res && <p className="sp-empty">카탈로그 로딩 중…</p>}

      {res && (
        <div className="sp-cols">
          <div className="sp-col">
            <div className="sp-sec-title">
              전문가 {pool.length > 0 && <span className="sp-dim">(전체 {pool.length}명)</span>}
            </div>
            {experts.length > 0 && (
              <>
                <div className="sp-dim sp-sub">주제 관련 추천</div>
                <ul className="sp-list">
                  {experts.map((e) => (
                    <li key={e.key}>{agentRow(e.key, e.name)}</li>
                  ))}
                </ul>
              </>
            )}
            <div className="sp-dim sp-sub">분야별 보기</div>
            <select className="sp-domain" value={domain} onChange={(e) => setDomain(e.target.value)} aria-label="분야 선택">
              <option value="">분야 선택…</option>
              {domains.map(([d, n]) => (
                <option key={d} value={d}>
                  {d} ({n}명)
                </option>
              ))}
            </select>
            {domain && (
              <ul className="sp-list sp-scroll">
                {domainAgents.map((a) => (
                  <li key={a.key}>{agentRow(a.key, a.name)}</li>
                ))}
              </ul>
            )}
            {agentSel && (
              <button type="button" className="sp-clear" onClick={() => setAgentSel(null)}>
                전문가 해제
              </button>
            )}
          </div>
          <div className="sp-col">
            <div className="sp-sec-title">도구 (선택 {toolSel.size}/{MAX_TOOLS})</div>
            {toolRec.length > 0 && (
              <ul className="sp-list">
                {toolRec.slice(0, 8).map((t) => (
                  <li key={t.name}>
                    <label className="sp-item" title={t.desc}>
                      <input type="checkbox" checked={toolSel.has(t.name)} onChange={() => toggleTool(t.name)} />
                      <span className="sp-name sp-mono">{t.name}</span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
            <select className="sp-domain" value={toolGroup} onChange={(e) => setToolGroup(e.target.value)} aria-label="MCP 앱 선택">
              <option value="">앱 선택… (전체 {toolAll.length}개)</option>
              {toolGroups.map(([k, g]) => (
                <option key={k} value={k}>{g.label} ({g.n})</option>
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
            {(toolFilter.trim() || toolGroup) && (
              <ul className="sp-list sp-scroll">
                {toolResults.length === 0 ? (
                  <li className="sp-empty">일치 없음</li>
                ) : (
                  toolResults.map((t) => (
                    <li key={t.name}>
                      <label className="sp-item" title={t.desc}>
                        <input type="checkbox" checked={toolSel.has(t.name)} onChange={() => toggleTool(t.name)} />
                        <span className="sp-name sp-mono">{t.name}</span>
                      </label>
                    </li>
                  ))
                )}
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
    </div>
  );
}
