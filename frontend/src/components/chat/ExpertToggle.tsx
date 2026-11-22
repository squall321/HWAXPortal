// 지정 전문가 알약 — 입력창 도구 줄에서 '누구와 대화 중인지' 와 '바꾸는 길' 을 한 곳에(종전엔 236px 우측 레일에 늘 떠 있었다)
import { useState } from 'react';
import { useChat } from '../../state/ChatContext';
import { IconUser } from './icons';
import { colorOf, initialOf, shortName } from './personaColor';
import { PersonaBrowser } from './PersonaBrowser';
import { PersonaPicker } from './PersonaPicker';
import { TeamPicker } from './TeamPicker';
import type { TeamSnapshot } from '../../api/teams.api';
import { useOperatorGone } from './useOperatorGone';

export function ExpertToggle() {
  const { pinnedAgent, pinnedAgentName, setPinnedAgent, pinnedHelpers, setPinnedHelpers, pinnedApps, setPinnedApps, pinnedTools,
          setPinnedTools, thinking } = useChat();
  // 대화 중에도 보조 전문가를 더한다(사용자 결정 11-22 — 종전엔 시작 화면에서만 됐다). 시작 화면의 규칙 그대로 — 주 전문가가 있을 때만 ·
  // 주 전문가와 같은 사람 · 이미 있는 사람은 안 받고 · 상한 4.
  const addHelper = (a: { key: string; name?: string }) => {
    if (!pinnedAgent || a.key === pinnedAgent || pinnedHelpers.some((h) => h.key === a.key) || pinnedHelpers.length >= 4) return;
    setPinnedHelpers([...pinnedHelpers, { key: a.key, name: a.name }]);
  };
  // null=닫힘 · quick=가벼운 선택기 · browse=전창 조직도 · team=전문가 팀
  const [mode, setMode] = useState<null | 'quick' | 'browse' | 'team'>(null);
  // 팀을 고르면 그 순간의 사본을 이 대화의 지정값으로 복사한다(docs/expert-teams ET-3) — 팀을 가리키지 않으므로 나중에 팀을 고쳐도 이 대화는 그대로다.
  // 에이전트 서버 계약은 그대로다(pinned_agent · pinned_agents · pinned_apps · pinned_tools).
  const pickTeam = (snap: TeamSnapshot) => {
    setPinnedAgent(snap.lead.key, snap.lead.name);
    setPinnedHelpers(snap.helpers.filter((h) => h.key !== snap.lead.key));
    setPinnedApps(snap.apps);
    setPinnedTools(snap.tools);
  };
  const label = pinnedAgentName || pinnedAgent || '';
  // 고른 운영자의 앱이 이 서버 게이트웨이에 없으면 보내기 전에 알약이 말한다(docs/request-1030 HP-51) — 종전엔 보낸 뒤에야 주의
  // (operator_app_missing)가 떴다.
  const gone = useOperatorGone(pinnedAgent);
  // Thinking 은 서버에서 지정 전문가보다 먼저 갈린다 — 둘 다 켜 두면 지정은 이번 턴에 안 쓰인다. 화면이 말해야 안다.
  const conflict = Boolean(pinnedAgent) && thinking;
  const title = conflict
    ? `Thinking 이 켜져 있어 이번 발화는 여러 전문가가 각자 답합니다 — 지정 전문가(${label})는 쓰이지 않습니다`
    : pinnedAgent
      ? `지정 전문가 — ${label} (${pinnedAgent}). ` +
        (gone.length > 0 ? `모는 앱(${gone.join(', ')})이 이 서버 게이트웨이에 연결돼 있지 않아 그 앱 도구 없이 답합니다. ` : '') +
        '눌러서 바꾸기'
      : '전문가를 골라 그 역할로 대화합니다(조직도에서도 고를 수 있습니다)';

  return (
    <div className="tool-wrap tool-expert">
      <button
        type="button"
        className={`tool-pill${pinnedAgent ? ' is-on' : ''}${conflict || gone.length > 0 ? ' is-warn' : ''}`}
        onClick={() => setMode('quick')}
        title={title}
      >
        {pinnedAgent ? (
          <span className="tool-av" style={{ background: colorOf(pinnedAgent) }} aria-hidden="true">
            {initialOf(label)}
          </span>
        ) : (
          <IconUser width={15} height={15} />
        )}
        <span className="tool-pill-text">{pinnedAgent ? shortName(label) : '전문가'}</span>
      </button>
      {pinnedAgent && (
        <button type="button" className="tool-x" onClick={() => setPinnedAgent(null)} aria-label={`전문가 ${label} 해제`} title="전문가 해제">
          ×
        </button>
      )}
      {mode === 'quick' && (
        <PersonaPicker onClose={() => setMode(null)} onExpand={() => setMode('browse')} onTeams={() => setMode('team')} />
      )}
      {mode === 'team' && (
        <TeamPicker
          current={{ lead: pinnedAgent ? { key: pinnedAgent, name: pinnedAgentName || undefined } : null, helpers: pinnedHelpers,
                     apps: pinnedApps, tools: pinnedTools }}
          onPick={pickTeam}
          onClose={() => setMode(null)}
        />
      )}
      {mode === 'browse' && (
        <PersonaBrowser
          onClose={() => setMode(null)}
          onBack={() => setMode('quick')}
          onAddHelper={pinnedAgent && pinnedHelpers.length < 4 ? addHelper : undefined}
        />
      )}
    </div>
  );
}
