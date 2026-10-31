// 지정 전문가 알약 — 입력창 도구 줄에서 '누구와 대화 중인지' 와 '바꾸는 길' 을 한 곳에(종전엔 236px 우측 레일에 늘 떠 있었다)
import { useState } from 'react';
import { useChat } from '../../state/ChatContext';
import { IconUser } from './icons';
import { colorOf, initialOf, shortName } from './personaColor';
import { PersonaBrowser } from './PersonaBrowser';
import { PersonaPicker } from './PersonaPicker';
import { useOperatorGone } from './useOperatorGone';

export function ExpertToggle() {
  const { pinnedAgent, pinnedAgentName, setPinnedAgent, thinking } = useChat();
  // null=닫힘 · quick=가벼운 선택기 · browse=전창 조직도
  const [mode, setMode] = useState<null | 'quick' | 'browse'>(null);
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
      {mode === 'quick' && <PersonaPicker onClose={() => setMode(null)} onExpand={() => setMode('browse')} />}
      {mode === 'browse' && <PersonaBrowser onClose={() => setMode(null)} onBack={() => setMode('quick')} />}
    </div>
  );
}
