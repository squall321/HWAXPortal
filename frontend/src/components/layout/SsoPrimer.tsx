// 로그인 직후 downstream SSO 를 숨은 iframe 으로 미리 태워 둔다 — 사용자가 앱마다 다시 로그인하지 않게 한다.
import { useEffect, useRef, useState } from 'react';
import { launchSystem, type HandoffPayload } from '../../api/launch.api';

// 미리 태울 시스템. heax-hub 하나면 그 아래 모든 /apps/<slug>/ 가 열린다
// (Caddy forward_auth 가 보는 heax_access_token 쿠키를 콜백이 심는다).
const PRIME_SYSTEMS = ['heax-hub'] as const;
// 세션당 한 번만 — 새로고침마다 반복하면 downstream 에 불필요한 토큰 발급이 쌓인다.
const FLAG = 'hwax.sso.primed';

interface Pending {
  systemId: string;
  handoff: HandoffPayload;
}

/** 로그인한 사용자에 대해 downstream 세션을 조용히 만든다. 화면에는 아무것도 그리지 않는다. */
export function SsoPrimer({ enabled }: { enabled: boolean }) {
  const [pending, setPending] = useState<Pending | null>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const startedRef = useRef(false);

  useEffect(() => {
    if (!enabled || startedRef.current) return;
    let primed: string[] = [];
    try {
      primed = JSON.parse(sessionStorage.getItem(FLAG) ?? '[]');
    } catch {
      primed = [];
    }
    const next = PRIME_SYSTEMS.find((id) => !primed.includes(id));
    if (!next) return;
    startedRef.current = true;
    launchSystem(next)
      .then((handoff) => {
        // redirect 방식은 주소창을 옮겨야 해서 조용히 태울 수 없다 — 그런 시스템은 건너뛴다.
        if (handoff.mode !== 'auto_post') return;
        setPending({ systemId: next, handoff });
      })
      .catch(() => {
        // 실패해도 화면은 그대로다. 사용자는 각 앱의 안내대로 수동 로그인할 수 있다.
        startedRef.current = false;
      });
  }, [enabled]);

  // 폼이 DOM 에 들어온 뒤 숨은 iframe 으로 제출한다(주소창은 그대로).
  useEffect(() => {
    if (pending) formRef.current?.submit();
  }, [pending]);

  const done = () => {
    if (!pending) return;
    try {
      const primed = JSON.parse(sessionStorage.getItem(FLAG) ?? '[]');
      if (!primed.includes(pending.systemId)) {
        sessionStorage.setItem(FLAG, JSON.stringify([...primed, pending.systemId]));
      }
    } catch {
      /* sessionStorage 가 막힌 브라우저면 다음 로드에서 다시 시도한다. */
    }
    setPending(null);
  };

  if (!pending) return null;
  return (
    <div aria-hidden style={{ display: 'none' }}>
      <iframe title="sso" name="hwax-sso-primer" onLoad={done} />
      <form ref={formRef} method="POST" action={pending.handoff.action} target="hwax-sso-primer">
        {Object.entries(pending.handoff.fields).map(([k, v]) => (
          <input key={k} type="hidden" name={k} value={v} />
        ))}
      </form>
    </div>
  );
}
