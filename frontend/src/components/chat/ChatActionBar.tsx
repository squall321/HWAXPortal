// 대화 툴바의 사내 연계 버튼(메일 보내기 등) — Knox 연계 타일이 살아 있을 때만 그 앱의 매니페스트를 읽어 그린다
import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { listSystems } from '../../api/systems.api';
import { useAuth } from '../../auth/useAuth';
import { useCan } from '../../auth/useCan';
import { useChat } from '../../state/ChatContext';
import {
  ACTION_SOURCES,
  fillText,
  mergeActions,
  parseManifest,
  safeUrl,
  scopeOf,
  visibleActions,
  type ChatAction,
} from './chatActions';

const TIMEOUT_MS = 1500;

/** 매니페스트 한 곳. null = 일시 실패(타임아웃·네트워크·본문 파싱·5xx·408·429) — 캐시하지 않고 다음 마운트에서 다시 받는다. */
async function fetchManifest(id: string): Promise<ChatAction[] | null> {
  const ctl = new AbortController();
  const timer = window.setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    // apiFetch 를 안 쓰는 것은 apiBase 접두사와 401 → /auth/refresh 재시도가 이 요청에 필요 없어서다.
    // 같은 오리진 path-proxy 라 포털 세션 쿠키는 어느 쪽으로 불러도 사이드카에 간다(context-notes A-6).
    const res = await fetch(`/${id}/ui/actions.json`, {
      credentials: 'same-origin',
      signal: ctl.signal,
      headers: { Accept: 'application/json' },
    });
    if (res.status >= 500 || res.status === 408 || res.status === 429) return null;
    // 그 밖의 4xx 는 확정 — 404(매니페스트 없음)·401/403(사이드카가 이 사용자를 거절). 되풀이되는 거절을
    // 대화 전환마다 다시 찌르지 않는다.
    if (!res.ok) return [];
    // 라우트가 없으면 포털 SPA catch-all 이 200 text/html 을 준다 — 반드시 걸러야 한다.
    if (!(res.headers.get('content-type') || '').includes('application/json')) return [];
    return parseManifest(await res.json());
  } catch {
    return null; // 버튼이 없을 뿐 화면은 그대로다
  } finally {
    window.clearTimeout(timer);
  }
}

// 대화 전환마다 다시 받지 않게 모듈 수준에서 캐시하되, **사용자·권한에 묶는다** — SSO 가 아닌 로컬 로그인은
// 새로고침 없이 사용자가 바뀌므로 전역 하나로 두면 앞 사람의 버튼이 남는다. 일시 실패는 캐시하지 않는다.
let loaded: { key: string; p: Promise<ChatAction[]> } | null = null;
function loadActions(key: string): Promise<ChatAction[]> {
  if (loaded?.key === key) return loaded.p;
  const entry = { key, p: Promise.resolve<ChatAction[]>([]) };
  loaded = entry;
  entry.p = (async () => {
    let transient = false;
    try {
      const systems = await listSystems();
      // 킬 스위치 — 타일이 available 인 것은 SYS_<ID>_URL 환경변수나 routes 파일에 목적지가 있을 때뿐이다
      // (catalog/registry.py). 목적지가 없거나 권한이 없어 타일이 안 내려오면 매니페스트 요청조차 안 만든다.
      const live = ACTION_SOURCES.filter((id) =>
        systems.some((s) => s.id === id && s.status === 'available' && s.integration_type === 'proxy'),
      );
      const lists = await Promise.all(live.map(fetchManifest));
      transient = lists.some((l) => l === null);
      return mergeActions(lists.map((l) => l ?? []));
    } catch {
      transient = true;
      return [];
    } finally {
      if (transient && loaded === entry) loaded = null; // 더 새 항목은 지우지 않는다
    }
  })();
  return entry.p;
}

export function ChatActionBar() {
  const { sendMessage, input, setInput, streaming, conversations, activeId } = useChat();
  const { user } = useAuth();
  const can = useCan();
  const scope = scopeOf(useLocation().pathname);
  const key = `${user?.subject ?? ''}|${(user?.entitlements ?? []).join(',')}`;
  const [got, setGot] = useState<{ key: string; actions: ChatAction[] }>({ key: '', actions: [] });

  useEffect(() => {
    let alive = true;
    void loadActions(key).then((actions) => {
      if (alive) setGot({ key, actions });
    });
    return () => {
      alive = false;
    };
  }, [key]);

  // 사용자·권한이 바뀐 직후 앞 키의 결과를 그리지 않는다.
  const shown = visibleActions(got.key === key ? got.actions : [], scope, can);
  if (shown.length === 0) return null; // 꺼진 환경에서는 DOM 노드가 0개 — 기존 툴바가 그대로다

  // 바로 보내는 버튼은 대답이 있어야 뜻이 있다 — 첫 심의가 실패한 대화에서 "결정문을 메일로" 를 보내면 모델이
  // 없는 결정문을 지어낼 수 있다. 심의 말풍선은 **결정문**이 있어야 대답이다: delib 객체는 첫 stage 이벤트에서
  // 이미 생기므로 발굴 실패·VOC 뒤 실패·취소한 심의도 delib 를 가진다. 그 밖의 말풍선은 오류 없는 본문.
  const conv = conversations.find((c) => c.id === activeId);
  const hasAnswer = !!conv?.messages.some(
    (m) => m.role === 'assistant' && (m.delib ? !!m.delib.decision : !!m.text && !m.error),
  );

  const onClick = (a: ChatAction) => {
    if (a.kind === 'link') {
      const u = safeUrl(a.url);
      if (u) window.open(u, '_blank', 'noopener,noreferrer');
      return;
    }
    if (!a.prompt) return;
    // 쓰던 초안이 있으면 바로 보내지 않고 덧붙여 채운다 — sendMessage 가 입력창을 비워 초안이 사라진다.
    if (a.mode === 'send' && !input.trim()) sendMessage(a.prompt);
    else {
      setInput(fillText(input, a.prompt));
      // 채운 뒤 바로 고칠 수 있게 — 페이지의 fillPrompt 와 같다(두 화면 모두 스레드 입력창은 .cx-composer-dock 안).
      document.querySelector<HTMLTextAreaElement>('.cx-composer-dock textarea')?.focus();
    }
  };

  return (
    <>
      {shown.map((a) => {
        const sending = a.kind === 'prompt' && a.mode === 'send';
        // 스트리밍 중 sendMessage 는 조용히 무시한다 — 눌러도 아무 일 없는 버튼은 꺼 두고 이유를 보인다.
        const why = !sending ? '' : streaming ? '응답이 끝나면 누를 수 있습니다' : !hasAnswer ? '대답이 생기면 누를 수 있습니다' : '';
        const title = why
          ? why
          : a.kind === 'link'
            ? '새 탭으로 엽니다'
            : sending
              ? '누르면 바로 보냅니다(입력창에 쓰던 글이 있으면 채우기만 합니다)'
              : '입력창에 요청을 채웁니다 — 확인하고 보내세요';
        return (
          <button
            key={a.id}
            type="button"
            className="cx-export-btn"
            data-hwax-action={a.id}
            onClick={() => onClick(a)}
            disabled={!!why}
            // .cx-export-btn 에 :disabled 규칙이 없어 꺼진 버튼이 켜진 것과 똑같이 보인다. 색을 인라인으로 박아
            // :hover 의 밝아짐도 누른다(기존 Word·핸드오프 버튼의 모양은 건드리지 않는다).
            style={why ? { opacity: 0.45, cursor: 'not-allowed', color: 'var(--muted)', borderColor: 'var(--border)' } : undefined}
            title={title}
          >
            {a.label}
          </button>
        );
      })}
    </>
  );
}
