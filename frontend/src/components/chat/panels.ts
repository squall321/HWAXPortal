// MCP Apps 패널 포인터 — SSE ui_resource 를 메시지에 남길 포인터로 거르고(결과는 이 탭의 live 로만) · 브라우저 사본에 남길 꼴(docs/request-1027 HP-42)
import { panelKey, rememberLive } from '../../lib/mcpApps';
import type { PanelPointer, UiResourceEvent } from '../../types/chat';

// 브라우저 사본에 남기는 입력의 JSON 길이 위쪽 — 다시 열 때 tool-input 으로 보낸다. 넘으면 남기지 않는다(쿼터 · 큰 입력은 그 탭에만).
const INPUT_KEEP_CHARS = 4096;

function okInput(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === 'object' && !Array.isArray(v);
}

/** 사건 하나 → 포인터(주소가 ui:// 가 아니면 버린다). 결과는 이 탭의 live 에 둔다 — 메시지 · 영속 · 다음 턴 이력에는 들어가지 않는다(B-6 (가)). */
export function panelPointer(e: UiResourceEvent | null | undefined): PanelPointer | null {
  if (!e || typeof e.uri !== 'string' || !e.uri.startsWith('ui://') || e.uri.length > 2048) return null;
  if (typeof e.tool !== 'string' || !e.tool) return null;
  const p: PanelPointer = {
    call: String(e.call ?? '').slice(0, 80),
    tool: e.tool.slice(0, 200),
    app: String(e.app ?? '').slice(0, 120),
    uri: e.uri,
    ...(okInput(e.input) ? { input: e.input } : {}),
  };
  rememberLive(panelKey(p), e.result && typeof e.result === 'object' ? e.result : null);
  return p;
}

/** 저장된 포인터 → 화면 포인터. 서버 사본(meta.panels)에는 입력이 없다(다른 기기에서 다시 열면 입력 없이 연다) — 브라우저 사본을 읽을 때만
 *  keepInput 으로 입력을 되살린다. */
export function panelsFromMeta(raw: unknown, keepInput = false): PanelPointer[] | undefined {
  if (!Array.isArray(raw)) return undefined;
  const out = raw
    .filter((p): p is Record<string, unknown> => !!p && typeof p === 'object')
    .filter((p) => typeof p.uri === 'string' && p.uri.startsWith('ui://') && typeof p.tool === 'string' && p.tool)
    .map((p) => ({
      call: String(p.call ?? ''),
      tool: String(p.tool),
      app: String(p.app ?? ''),
      uri: String(p.uri),
      ...(typeof p.title === 'string' && p.title ? { title: p.title } : {}),
      ...(keepInput && okInput(p.input) ? { input: p.input } : {}),
    }));
  return out.length ? out.slice(0, 8) : undefined;
}

/** 브라우저 사본(localStorage)에 남길 꼴 — 포인터와 작은 입력만. */
export function storedPanels(list: PanelPointer[] | undefined): PanelPointer[] | undefined {
  if (!list?.length) return undefined;
  return list.slice(0, 8).map((p) => {
    const keep = p.input && JSON.stringify(p.input).length <= INPUT_KEEP_CHARS;
    return { call: p.call, tool: p.tool, app: p.app, uri: p.uri, ...(p.title ? { title: p.title } : {}), ...(keep ? { input: p.input } : {}) };
  });
}
