// 로그인 직후·만료 전에 downstream SSO 를 숨은 iframe 으로 태워 둔다 — 사용자가 앱마다 다시 로그인하지 않게 한다.
import { useCallback, useEffect, useRef, useState } from 'react';
import { launchSystem, type HandoffPayload } from '../../api/launch.api';

// 미리 태울 시스템. heax-hub 하나면 그 아래 모든 /apps/<slug>/ 가 열린다
// (Caddy forward_auth 가 보는 heax_access_token 쿠키를 콜백이 심는다).
const PRIME_SYSTEMS = ['heax-hub'] as const;
const FLAG = 'hwax.sso.primed';
// heax 액세스 토큰 수명은 3600 s 다(HEAXHub ACCESS_TOKEN_TTL_SECONDS). 만료 전에 갱신해야
// 오래 열어 둔 탭에서 앱이 갑자기 401 로 막히지 않는다 — 15분 여유를 둔다.
const PRIME_TTL_MS = 45 * 60 * 1000;
// 탭을 켜 둔 채 시간이 흐르는 경우를 위해 주기적으로도 확인한다.
const CHECK_MS = 5 * 60 * 1000;

interface Pending {
  systemId: string;
  handoff: HandoffPayload;
}

function readPrimed(): Record<string, number> {
  try {
    const raw = JSON.parse(sessionStorage.getItem(FLAG) ?? '{}');
    // 옛 형식(배열)에서 넘어오는 경우 — 시각을 모르므로 만료로 본다.
    return raw && !Array.isArray(raw) && typeof raw === 'object' ? raw : {};
  } catch {
    return {};
  }
}

/** downstream 세션을 조용히 만들고 만료 전에 갱신한다. 화면에는 아무것도 그리지 않는다. */
export function SsoPrimer({ enabled }: { enabled: boolean }) {
  const [pending, setPending] = useState<Pending | null>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const busyRef = useRef(false);

  const prime = useCallback(() => {
    if (!enabled || busyRef.current) return;
    const primed = readPrimed();
    const now = Date.now();
    const next = PRIME_SYSTEMS.find((id) => !(primed[id] > now - PRIME_TTL_MS));
    if (!next) return;
    busyRef.current = true;
    launchSystem(next)
      .then((handoff) => {
        // redirect 방식은 주소창을 옮겨야 해서 조용히 태울 수 없다 — 그런 시스템은 건너뛴다.
        if (handoff.mode !== 'auto_post') {
          busyRef.current = false;
          return;
        }
        setPending({ systemId: next, handoff });
      })
      .catch(() => {
        // 실패해도 화면은 그대로다. 다음 주기에 다시 시도한다.
        busyRef.current = false;
      });
  }, [enabled]);

  useEffect(() => {
    prime();
    const timer = window.setInterval(prime, CHECK_MS);
    // 탭을 다시 앞으로 가져왔을 때도 확인한다 — 절전으로 인터벌이 밀렸을 수 있다.
    const onVisible = () => { if (document.visibilityState === 'visible') prime(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [prime]);

  // 폼이 DOM 에 들어온 뒤 숨은 iframe 으로 제출한다(주소창은 그대로).
  useEffect(() => {
    if (pending) formRef.current?.submit();
  }, [pending]);

  const done = () => {
    if (!pending) return;
    try {
      sessionStorage.setItem(FLAG, JSON.stringify({ ...readPrimed(), [pending.systemId]: Date.now() }));
    } catch {
      /* sessionStorage 가 막힌 브라우저면 다음 주기에 다시 태운다. */
    }
    setPending(null);
    busyRef.current = false;
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
