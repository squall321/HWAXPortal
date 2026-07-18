// 대화 옆 활동 패널 — 이번 턴에 어떤 전문가(에이전트)가 소집되고 어떤 MCP 도구가 호출되는지 실시간 표시.
// 넓은 화면(≥1180px)은 우측 레일, 좁은 화면은 플로팅 버튼 → 드로어. 도구 항목은 클릭 시 입력/결과 요약.
import { useEffect, useMemo, useState } from 'react';
import type { ActivityItem, Message } from '../../types/chat';

// 도구명 → 소속 서비스 라벨(알려진 것만, 나머지는 게이트웨이로 표기).
const TOOL_ORIGIN: Record<string, string> = {
  recommend_agents: 'AI Data Hub',
  get_agent_session: 'AI Data Hub',
  agent_search: 'AI Data Hub',
  semantic_search: 'AI Data Hub',
  list_records: 'AI Data Hub',
  data_aggregate: 'AI Data Hub',
  signalforge: 'SignalForge',
  alert_check: 'SignalForge',
  daily_briefing: 'SignalForge',
  query_voc: 'SignalForge',
  search_voc: 'SignalForge',
  get_top_issues: 'SignalForge',
  create_report_draft: 'Report Archive',
  update_report_draft: 'Report Archive',
  search_reports: 'Report Archive',
  list_templates: 'Report Archive',
  analyze_laminate: 'Laminate(heax)',
  evaluate_laminate: 'Laminate(heax)',
  solve_load_response: 'Laminate(heax)',
  list_materials: 'MaterialTwin(heax)',
  plot_ashby: 'MaterialTwin(heax)',
  search_documents: 'MX White Paper',
  search_knowledge: 'MX White Paper',
};
const originOf = (tool: string) =>
  TOOL_ORIGIN[tool] ?? (tool.startsWith('slurm_') ? 'Smart Twin(슬럼)' : '게이트웨이');

interface ToolInfo {
  name: string;
  detail?: string; // 마지막 호출 입력 요약
  result?: string; // 마지막 완료 결과 요약
}

/** 활동 패널이 보여줄 메시지 선택 — 스트리밍 중인 턴 우선, 없으면 활동이 있는 마지막 어시스턴트 턴. */
function pickActive(messages: Message[]): Message | null {
  const streaming = [...messages].reverse().find((m) => m.streaming && m.activity?.length);
  if (streaming) return streaming;
  return [...messages].reverse().find((m) => m.role === 'assistant' && m.activity?.length) ?? null;
}

export function ActivityPanel({ messages }: { messages: Message[] }) {
  const msg = pickActive(messages);
  const items: ActivityItem[] = useMemo(() => msg?.activity ?? [], [msg]);
  const live = Boolean(msg?.streaming);
  // 좁은 화면 드로어 상태 — 대화(메시지 주체)가 바뀌면 닫는다.
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [msg?.id]);

  const personas = useMemo(() => {
    const out: string[] = [];
    for (const it of items) for (const p of it.personas ?? []) if (!out.includes(p)) out.push(p);
    return out;
  }, [items]);

  const tools = useMemo(() => {
    const map = new Map<string, ToolInfo>();
    for (const it of items) {
      const names = [it.tool, ...(it.tools_used ?? [])].filter(
        (t): t is string => Boolean(t) && t !== 'signalforge',
      );
      for (const t of names) {
        const cur = map.get(t) ?? { name: t };
        // 호출(detail)과 완료(result_preview)가 별개 status로 오므로 나중 값으로 갱신.
        if (it.detail && it.tool === t) cur.detail = it.detail;
        if (it.result_preview && it.tool === t) cur.result = it.result_preview;
        map.set(t, cur);
      }
    }
    return [...map.values()];
  }, [items]);

  if (!msg || items.length === 0) return null;

  const body = (
    <>
      <div className="act-head">
        <span className={`act-dot${live ? ' live' : ''}`} aria-hidden="true" />
        {live ? '진행 중' : '지난 턴 활동'}
        <button
          type="button"
          className="act-close"
          onClick={() => setOpen(false)}
          aria-label="활동 패널 닫기"
        >
          ×
        </button>
      </div>

      {personas.length > 0 && (
        <section className="act-sec">
          <h4>참여 전문가 {personas.length}</h4>
          <div className="act-tags">
            {personas.map((p) => (
              <span key={p} className="act-tag persona" title={p}>
                {p}
              </span>
            ))}
          </div>
        </section>
      )}

      {tools.length > 0 && (
        <section className="act-sec">
          <h4>MCP 도구 {tools.length}</h4>
          <div className="act-tools">
            {tools.map((t) =>
              t.detail || t.result ? (
                <details key={t.name} className="act-tool">
                  <summary>
                    <code>{t.name}</code>
                    <span className="act-origin">{originOf(t.name)}</span>
                  </summary>
                  {t.detail && (
                    <div className="act-io">
                      <span className="act-io-k">입력</span> {t.detail}
                    </div>
                  )}
                  {t.result && (
                    <div className="act-io">
                      <span className="act-io-k">결과</span> {t.result}
                    </div>
                  )}
                </details>
              ) : (
                <div key={t.name} className="act-tool plain">
                  <code>{t.name}</code>
                  <span className="act-origin">{originOf(t.name)}</span>
                </div>
              ),
            )}
          </div>
        </section>
      )}

      <section className="act-sec">
        <h4>진행</h4>
        <ol className="act-steps">
          {items.slice(-8).map((it, i, arr) => (
            <li key={`${it.ts}-${i}`} className={live && i === arr.length - 1 ? 'now' : ''}>
              {it.step}
            </li>
          ))}
        </ol>
      </section>
    </>
  );

  return (
    <>
      {/* 좁은 화면 전용 토글 — 데스크톱에선 CSS로 숨김 */}
      <button
        type="button"
        className="act-fab"
        onClick={() => setOpen(true)}
        aria-label="에이전트·도구 활동 보기"
      >
        <span className={`act-dot${live ? ' live' : ''}`} aria-hidden="true" />
        활동
      </button>
      {open && <div className="act-backdrop" onClick={() => setOpen(false)} aria-hidden="true" />}
      <aside className={`cx-activity${open ? ' open' : ''}`} aria-label="에이전트·도구 활동">
        {body}
      </aside>
    </>
  );
}
