// 챗 시작 전 전문가·도구 선택 패널 — 주제/키워드 검색으로 전문가(1명, 페르소나)와 도구(≤12)를
// 직접 골라 대화를 구성한다. 심의 선정 패널과 같은 '검색→선택→시작' 구조의 챗 버전.
import { useMemo, useState } from 'react';
import { fetchDeliberateExperts, type ExpertsResponse } from '../../api/chat.api';
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

  const search = async () => {
    const q = query.trim();
    if (!q || loading) return;
    setLoading(true);
    const r = await fetchDeliberateExperts(q);
    setRes(r);
    setLoading(false);
  };

  const experts = useMemo(() => {
    const ranked = res?.candidates?.length ? res.candidates : (res?.recommended ?? []);
    return ranked.slice(0, LIST_LIMIT);
  }, [res]);

  const toolAll = useMemo(() => res?.tools?.all ?? [], [res]);
  const toolRec = res?.tools?.recommended ?? [];
  const toolResults = useMemo(() => {
    const q = toolFilter.trim().toLowerCase();
    if (!q) return [];
    return toolAll.filter((t) => `${t.name} ${t.desc}`.toLowerCase().includes(q)).slice(0, 15);
  }, [toolFilter, toolAll]);

  const toggleTool = (name: string) =>
    setToolSel((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else if (next.size < MAX_TOOLS) next.add(name);
      return next;
    });

  const apply = () => {
    setPinnedAgent(agentSel);
    setPinnedTools([...toolSel]);
    onClose();
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
        주제를 검색해 전문가(페르소나 1명)와 우선 사용할 도구를 직접 고르세요. 고르지 않고 그냥
        대화해도 됩니다.
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

      {res && (
        <>
          {res.error && <p className="sp-warn">검색 실패({res.error}) — 다시 시도하세요.</p>}
          <div className="sp-cols">
            <div className="sp-col">
              <div className="sp-sec-title">전문가 (1명 선택 — 페르소나로 대화)</div>
              <ul className="sp-list">
                {experts.length === 0 ? (
                  <li className="sp-empty">관련 전문가가 없습니다.</li>
                ) : (
                  experts.map((e) => (
                    <li key={e.key}>
                      <label className="sp-item">
                        <input
                          type="radio"
                          name="sp-agent"
                          checked={agentSel === e.key}
                          onChange={() => setAgentSel(agentSel === e.key ? null : e.key)}
                          onClick={() => {
                            if (agentSel === e.key) setAgentSel(null); // 재클릭 = 해제
                          }}
                        />
                        <span className="sp-name">{e.name}</span>
                      </label>
                    </li>
                  ))
                )}
              </ul>
              {agentSel && (
                <button type="button" className="sp-clear" onClick={() => setAgentSel(null)}>
                  전문가 해제
                </button>
              )}
            </div>
            <div className="sp-col">
              <div className="sp-sec-title">도구 (선택 {toolSel.size}/{MAX_TOOLS})</div>
              <ul className="sp-list">
                {toolRec.length === 0 ? (
                  <li className="sp-empty">관련 도구가 없습니다 — 아래 검색으로 찾으세요.</li>
                ) : (
                  toolRec.slice(0, 8).map((t) => (
                    <li key={t.name}>
                      <label className="sp-item" title={t.desc}>
                        <input type="checkbox" checked={toolSel.has(t.name)} onChange={() => toggleTool(t.name)} />
                        <span className="sp-name sp-mono">{t.name}</span>
                      </label>
                    </li>
                  ))
                )}
              </ul>
              <input
                className="sp-search sp-search-sm"
                type="text"
                value={toolFilter}
                onChange={(e) => setToolFilter(e.target.value)}
                placeholder={`전체 ${toolAll.length}개 도구 검색`}
                aria-label="도구 검색"
              />
              {toolFilter.trim() && (
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
        </>
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
