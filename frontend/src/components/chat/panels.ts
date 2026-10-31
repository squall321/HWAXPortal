// MCP Apps 패널 포인터 — SSE ui_resource 를 메시지에 남길 포인터로 거른다(결과는 이 탭의 live 로만, docs/request-1027 HP-42). 저장 꼴(panelsFromMeta · storedPanels)은 state/chatStore.ts 에 있다
import { panelKey, rememberLive } from '../../lib/mcpApps';
import type { PanelPointer, UiResourceEvent } from '../../types/chat';

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
