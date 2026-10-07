// 도는 스트림 아래에 '서버 살아 있음 · 마지막 진행 N분 전' 또는 '신호 없음' 한 줄을 보인다 — 끊지 않는다, 표시만 한다
import { useEffect, useState } from 'react';
import { liveness } from '../../lib/streamLive';
import { useChat } from '../../state/ChatContext';

export function StreamPulse() {
  const { streaming, streamLive } = useChat();
  // 프레임이 올 때마다가 아니라 1초마다 다시 읽는다 — 신호가 **안 올 때** 바뀌어야 하는 문장이라 이벤트로는 못 그린다.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!streaming) return;
    const h = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(h);
  }, [streaming]);
  const live = streaming ? streamLive() : null;
  const s = live ? liveness(live, now) : null;
  if (!s) return null;
  return (
    <div className={s.state === 'silent' ? 'msg-warn' : 'msg-status-text'} role="status" data-live={s.state}>
      {s.text}
    </div>
  );
}
