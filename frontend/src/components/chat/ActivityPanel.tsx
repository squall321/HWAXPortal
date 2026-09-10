// 대화 옆 활동 패널 — 이번 턴에 어떤 전문가(에이전트)가 소집되고 어떤 MCP 도구가 호출되는지 실시간 표시.
// 넓은 화면(≥1180px)은 우측 레일, 좁은 화면은 플로팅 버튼 → 드로어. 도구 항목은 클릭 시 입력/결과 요약.
import { useEffect, useMemo, useState } from 'react';
import { useChat } from '../../state/ChatContext';
import type { ActivityItem, Message } from '../../types/chat';
import { PersonaBrowser } from './PersonaBrowser';
import { PersonaPicker } from './PersonaPicker';
import { colorOf, initialOf, shortName } from './personaColor';

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

/** 현재 페르소나 칸 — 상태 바 바로 아래. **활동이 없어도** 보인다.
 *  "누구와 대화 중인지"와 "바꾸는 길"이 여기 한 곳에 있어야, 대화가 시작된 뒤에도 길이 닫히지 않는다. */
function PersonaBar() {
  const { pinnedAgent, pinnedAgentName, setPinnedAgent, thinking } = useChat();
  // null=닫힘 · quick=가벼운 선택기 · browse=전창 조직도
  const [mode, setMode] = useState<null | 'quick' | 'browse'>(null);
  const label = pinnedAgentName || pinnedAgent || '';

  return (
    <section className="act-sec act-persona">
      <h4>현재 전문가</h4>
      <div className="pb-row">
        {pinnedAgent ? (
          <>
            <span className="pb-av" style={{ background: colorOf(label) }}>
              {initialOf(label)}
            </span>
            <span className="pb-body">
              <span className="pb-name" title={label}>{shortName(label)}</span>
              <span className="pb-key">{pinnedAgent}</span>
            </span>
          </>
        ) : (
          <>
            <span className="pb-av pb-av-none" aria-hidden="true">
              ·
            </span>
            <span className="pb-body">
              <span className="pb-name pb-none">일반 어시스턴트</span>
              <span className="pb-key">전문가 미지정</span>
            </span>
          </>
        )}
      </div>
      {/* Thinking 은 서버에서 지정 전문가보다 먼저 갈린다 — 둘 다 켜 두면 지정은 이번 턴에 안 쓰인다.
          화면이 말하지 않으면 사용자는 알아낼 방법이 없다. */}
      {pinnedAgent && thinking && (
        <p className="pb-conflict">
          Thinking 모드가 켜져 있어 이번 발화는 <b>여러 전문가가 각자</b> 답합니다 — 지정 전문가는
          쓰이지 않습니다.
        </p>
      )}
      <div className="pb-acts">
        <button type="button" className="pb-btn" onClick={() => setMode('quick')}>
          {pinnedAgent ? '바꾸기' : '전문가 고르기'}
        </button>
        <button type="button" className="pb-btn" onClick={() => setMode('browse')}>
          조직도
        </button>
        {pinnedAgent && (
          <button type="button" className="pb-btn pb-btn-off" onClick={() => setPinnedAgent(null)}>
            해제
          </button>
        )}
      </div>
      {mode === 'quick' && (
        <PersonaPicker onClose={() => setMode(null)} onExpand={() => setMode('browse')} />
      )}
      {mode === 'browse' && (
        <PersonaBrowser onClose={() => setMode(null)} onBack={() => setMode('quick')} />
      )}
    </section>
  );
}

export function ActivityPanel({
  messages,
  showPersona = true,
}: {
  messages: Message[];
  /** 심의 페이지는 좌석을 ExpertPicker 로 정한다 — 거기서 '현재 전문가' 를 보여 주면
   *  효과 없는 손잡이를 내미는 셈이라 끈다. */
  showPersona?: boolean;
}) {
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

  const body = (
    <>
      <div className="act-head">
        <span className={`act-dot${live ? ' live' : ''}`} aria-hidden="true" />
        {live ? '진행 중' : items.length > 0 ? '지난 턴 활동' : '대화 설정'}
        <button
          type="button"
          className="act-close"
          onClick={() => setOpen(false)}
          aria-label="활동 패널 닫기"
        >
          ×
        </button>
      </div>

      {showPersona && <PersonaBar />}

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

      {items.length > 0 && (
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
      )}
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
