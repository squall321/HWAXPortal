// 챗·심의 액션 바의 순수 규칙 — 사내 앱 매니페스트 검증·링크 안전 판정·화면별 선별(ChatActionBar 가 쓴다)
//
// 버튼 정본은 포털 밖(사내 앱이 서비스하는 /<id>/ui/actions.json)이다. 그 JSON 은 포털이 통제하지 못하므로
// 여기서 모르는 값은 전부 버린다(fail-closed). docs/chat-actions/.

export const ACTIONS_SCHEMA = 'hwax.chat-actions/1';
// 매니페스트를 읽을 타일 id. 타일이 available(= SYS_<ID>_URL 또는 routes 파일에 목적지가 있다)일 때만 읽는다.
// 모든 proxy 타일을 찔러 보지 않는다 — 관계없는 앱마다 404·401 요청이 한 번씩 간다(context-notes A-3).
export const ACTION_SOURCES = ['knox-bridge'];
export const MAX_PER_SOURCE = 8;
export const MAX_TOTAL = 12;
export const MAX_LABEL = 24;
export const MAX_PROMPT = 2000;

export type ActionScope = 'chat' | 'deliberate';

export interface ChatAction {
  id: string;
  label: string;
  kind: 'prompt' | 'link';
  prompt?: string; // kind === 'prompt'
  url?: string; // kind === 'link' — safeUrl 을 통과한 값
  mode: 'fill' | 'send'; // fill = 입력창에 채운다(사람이 고친 뒤 보낸다), send = 바로 보낸다
  scope: ActionScope | 'both';
  need?: string; // 이 권한 키가 있어야 보인다
}

/** 새 탭으로 열어도 되는 주소만 돌려준다 — http(s) 절대주소 또는 같은 오리진 절대경로.
 *  공백·제어문자·역슬래시가 하나라도 있으면 거부한다: 브라우저는 `/\evil.com` 을 `//evil.com`(프로토콜 상대)으로
 *  읽고, URL 파서가 탭·개행을 지우므로 `/<탭>/evil.com` 도 같은 곳으로 간다. 스킴이 없으면 javascript: 류는 불가.
 *  제어문자는 정규식 대신 코드값으로 본다 — 정규식에 쓰면 원본 파일에 제어 바이트가 박혀 git 이 이진으로 본다. */
export function safeUrl(u: unknown): string | null {
  if (typeof u !== 'string' || !u || /\s/.test(u)) return null;
  for (let i = 0; i < u.length; i++) {
    const c = u.charCodeAt(i);
    if (c < 0x20 || c === 0x7f || c === 0x5c /* 역슬래시 */) return null;
  }
  if (/^https?:\/\/[^/]/i.test(u)) return u;
  if (/^\/(?!\/)/.test(u)) return u;
  return null;
}

function normalize(raw: unknown): ChatAction | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Record<string, unknown>;
  if (typeof r.id !== 'string' || !r.id) return null;
  if (typeof r.label !== 'string' || !r.label.trim() || r.label.length > MAX_LABEL) return null;
  if (r.need !== undefined && typeof r.need !== 'string') return null;
  let scope: ChatAction['scope'];
  if (r.scope === undefined || r.scope === 'both') scope = 'both';
  else if (r.scope === 'chat' || r.scope === 'deliberate') scope = r.scope;
  else return null;
  const base = { id: r.id, label: r.label, scope, ...(r.need ? { need: r.need } : {}) };
  if (r.kind === 'prompt') {
    if (typeof r.prompt !== 'string' || !r.prompt.trim() || r.prompt.length > MAX_PROMPT) return null;
    // 모르는 mode 는 채우기로 — 고르는 건 사람이다.
    return { ...base, kind: 'prompt', prompt: r.prompt, mode: r.mode === 'send' ? 'send' : 'fill' };
  }
  if (r.kind === 'link') {
    const url = safeUrl(r.url);
    return url ? { ...base, kind: 'link', url, mode: 'fill' } : null;
  }
  return null; // 모르는 kind 를 링크로 여는 것은 fail-open 이다
}

/** 매니페스트 JSON → 쓸 수 있는 액션. schema 가 다르거나 모양이 틀리면 빈 배열. */
export function parseManifest(j: unknown): ChatAction[] {
  if (!j || typeof j !== 'object') return [];
  const m = j as { schema?: unknown; actions?: unknown };
  if (m.schema !== ACTIONS_SCHEMA || !Array.isArray(m.actions)) return [];
  return mergeActions([m.actions.map(normalize).filter((a): a is ChatAction => a !== null)], MAX_PER_SOURCE);
}

/** 출처별 목록을 합친다 — id 가 겹치면 앞의 것만(React key·같은 버튼 두 개), 상한까지. */
export function mergeActions(lists: ChatAction[][], max = MAX_TOTAL): ChatAction[] {
  const out: ChatAction[] = [];
  const seen = new Set<string>();
  for (const a of lists.flat()) {
    if (seen.has(a.id)) continue;
    seen.add(a.id);
    out.push(a);
    if (out.length >= max) break;
  }
  return out;
}

export function scopeOf(pathname: string): ActionScope {
  return pathname === '/deliberate' || pathname.startsWith('/deliberate/') ? 'deliberate' : 'chat';
}

/** 이 화면·이 사용자에게 보일 액션. */
export function visibleActions(
  actions: ChatAction[],
  scope: ActionScope,
  can: (key: string) => boolean,
): ChatAction[] {
  return actions.filter((a) => (a.scope === 'both' || a.scope === scope) && (!a.need || can(a.need)));
}

/** 입력창에 요청을 채울 값 — 쓰던 초안이 있으면 지우지 않고 뒤에 덧붙인다. */
export function fillText(current: string, prompt: string): string {
  return current.trim() ? `${current.replace(/\s+$/, '')}\n\n${prompt}` : prompt;
}
