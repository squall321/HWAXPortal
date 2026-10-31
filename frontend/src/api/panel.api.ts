// MCP Apps 패널 창구(/agent/panel/*) — 세션 쿠키 + CSRF 로만 부른다(docs/request-1027 HP-42 · 포털 backend/app/agent/panel.py)
import { apiFetch } from './client';
import type { PanelCsp, PanelResult } from '../lib/mcpApps';

export interface PanelOpened {
  panel_id: string;
  html: string;
  csp: PanelCsp;
  prefers_border: boolean;
  app: string;
  app_label: string;
  uri: string;
  tool: string;
  tools: string[];
  open_origins: string[];
  limits?: { call_max_bytes?: number; session_max_mb?: number; idle_s?: number };
}

/** 포털이 거절한 까닭 — code 로 가른다(confirm_required 면 token 이 실린다). */
export class PanelError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public token?: string,
  ) {
    super(message);
  }
}

async function post<T>(path: string, body: unknown, keepalive = false): Promise<T> {
  const r = await apiFetch(`/agent/panel/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    ...(keepalive ? { keepalive: true } : {}),
  });
  let j: unknown = null;
  try {
    j = await r.json();
  } catch {
    j = null;
  }
  if (!r.ok) {
    const d = (j as { detail?: unknown } | null)?.detail;
    const o = d && typeof d === 'object' ? (d as { code?: string; message?: string; token?: string }) : null;
    throw new PanelError(r.status, o?.code ?? `http_${r.status}`, o?.message ?? (typeof d === 'string' ? d : `패널 창구 오류(${r.status})`), o?.token);
  }
  return j as T;
}

export const openPanel = (uri: string, tool: string, call: string) => post<PanelOpened>('open', { uri, tool, call });
export const callPanel = (panelId: string, name: string, args: Record<string, unknown>) =>
  post<{ result?: PanelResult & { isError?: boolean }; error?: { code: number; message: string } }>('call', {
    panel_id: panelId,
    name,
    arguments: args,
  });
export const readPanel = (panelId: string, uri: string) =>
  post<{ result?: unknown; error?: { code: number; message: string } }>('read', { panel_id: panelId, uri });
export const confirmPanel = (panelId: string, token: string) => post<{ ok: boolean }>('confirm', { panel_id: panelId, token });
/** 닫기 — 탭이 떠날 때도 끝까지 가게 keepalive 로 보낸다(실패는 버린다 — 포털 청소가 30분 뒤 닫는다). */
export const closePanel = (panelId: string) => post<{ ok: boolean }>('close', { panel_id: panelId }, true).catch(() => ({ ok: false }));
