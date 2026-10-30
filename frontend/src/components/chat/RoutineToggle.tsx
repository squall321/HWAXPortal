// 분석 루틴 알약 — 입력창 도구 줄에서 루틴을 골라 켜 둔다. 켜 둔 루틴은 다음 발화 한 번에 실려 그 연쇄로 분석한다(docs/analysis-routines R3 §6)
import { useState } from 'react';
import { useCan } from '../../auth/useCan';
import { useChat } from '../../state/ChatContext';
import { IconLink } from './icons';
import { RoutinePicker } from './RoutinePicker';

export function RoutineToggle() {
  const { armedRoutine, setArmedRoutine, thinking, pinnedAgent } = useChat();
  const can = useCan();
  const [open, setOpen] = useState(false);
  // 루틴은 에이전트 서버에서 Thinking · 지정 전문가 · 슬래시보다 먼저 갈린다 — 함께 켜 두면 그것들은 그 발화에 쓰이지 않는다. 화면이 말해야 안다.
  // 권한이 없어 실리지 않는 것(sendMessage 가 거른다)은 겹친다고 말하지 않는다.
  const others = [thinking && can('feat:thinking') && 'Thinking', pinnedAgent && can('feat:expert-chat') && '지정 전문가']
    .filter(Boolean)
    .join(' · ');
  const conflict = Boolean(armedRoutine) && others !== '';
  // 지난 시작이 실행을 만들기 전에 끝나 보낸 값을 되살려 켜 둔 루틴 — 까닭을 말하고 고치러 가게 한다(고르기 창이 칸 옆에 까닭을 보인다)
  const rejected = armedRoutine?.reason;
  const title = !armedRoutine
    ? '분석 루틴 — 내 권한의 플랫폼을 순서대로 엮은 분석을 골라 켭니다. 켜 두면 다음 발화가 그 루틴을 돌립니다'
    : rejected
      ? `지난번 보낸 값으로 시작하지 못했습니다 — ${rejected}. 그 값을 그대로 켜 두었습니다 — 눌러서 고치기`
      : conflict
        ? `루틴이 먼저입니다 — 다음 발화는 「${armedRoutine.title}」 을 돌리고 ${others} 는 그 발화에 쓰이지 않습니다`
        : `켜 둔 루틴 — 「${armedRoutine.title}」. 다음 발화 한 번에 실립니다(글을 비워 보내도 됩니다). 눌러서 바꾸기`;

  return (
    <div className="tool-wrap tool-routine">
      <button
        type="button"
        className={`tool-pill${armedRoutine ? ' is-on' : ''}${conflict || rejected ? ' is-warn' : ''}`}
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
        title={title}
      >
        <IconLink width={15} height={15} />
        <span className="tool-pill-text">{armedRoutine ? armedRoutine.title : '루틴'}</span>
      </button>
      {armedRoutine && (
        <button
          type="button"
          className="tool-x"
          onClick={() => setArmedRoutine(null)}
          aria-label={`루틴 ${armedRoutine.title} 끄기`}
          title="루틴 끄기"
        >
          ×
        </button>
      )}
      {open && <RoutinePicker onClose={() => setOpen(false)} />}
    </div>
  );
}
