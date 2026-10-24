// 챗 답을 MX 백서 LLM 위키 원천으로 보내는 포털 API — '위키에 남기기' · '해결됨'(docs/mxwp-wiki P6 · P7)
import { apiFetch, errorDetail } from './client';

export type WikiMode = 'button' | 'candidate';

/** 포털이 게이트웨이 wiki_submit_source 로 보낸 결과 — 원천 번호 · 범위 · 같은 것을 이미 받았는가. */
export interface WikiSendResult {
  ok: boolean;
  mode: WikiMode;
  audience: string[];
  id: string;
  short?: string | null;
  dedup?: boolean | null;
  doc_slug?: string | null;
  ingest_state?: string | null;
}

/** 저장된 그 답을 보낸다 — 본문은 서버가 저장된 답과 짝을 찾는 열쇠로만 쓴다(근거는 서버가 저장된 턴에서 짓는다). */
export async function sendTurnToWiki(
  serverId: string,
  body: { text: string; mode: WikiMode; model?: string | null },
): Promise<WikiSendResult> {
  // 챗과 같은 이유로 apiFetch — 화면을 오래 띄워 두면 raw fetch 는 401 로 조용히 실패한다.
  const res = await apiFetch(`/agent/conversations/${encodeURIComponent(serverId)}/wiki`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const fallback = `위키에 보내지 못했습니다 (HTTP ${res.status}).`;
    let msg = fallback;
    try {
      msg = errorDetail((await res.json())?.detail, fallback);
    } catch {
      /* 본문이 JSON 이 아니면 기본 문구 */
    }
    throw new Error(msg);
  }
  return (await res.json()) as WikiSendResult;
}
