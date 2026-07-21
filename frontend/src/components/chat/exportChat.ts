// 대화 이력 내보내기 — (1) 보이는 그대로의 자기완결 HTML(렌더된 DOM + 사이트 CSS 인라인),
// (2) 구조화 JSON(메시지·활동·심의 라운드/표결까지 스키마화). 서버 왕복 없이 브라우저에서 생성.
import type { Conversation, DelibTurn, Message } from '../../types/chat';

const iso = (ms?: number) => (ms ? new Date(ms).toISOString() : undefined);

function sanitizeFilename(s: string): string {
  return (
    s
      .replace(/[\\/:*?"<>|\n\r]+/g, ' ')
      .trim()
      .slice(0, 60) || '대화'
  );
}

function stamp(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`;
}

export function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

// ── JSON 내보내기 ────────────────────────────────────────────────────────────

// 심의 turns 를 라운드별로 묶는다 — 소비측(분석 스크립트)이 라운드 단위로 바로 순회하게.
function groupRounds(turns: DelibTurn[] | undefined) {
  if (!turns?.length) return undefined;
  const rounds: Record<string, DelibTurn[]> = {};
  for (const t of turns) {
    const k = String(t.round);
    (rounds[k] ??= []).push(t);
  }
  return rounds;
}

function exportMessage(m: Message) {
  return {
    id: m.id,
    role: m.role,
    ts: iso(m.ts),
    text: m.text,
    ...(m.result && (m.result.type !== 'text' || m.result.content !== m.text) ? { result: m.result } : {}),
    ...(m.activity?.length ? { activity: m.activity.map((a) => ({ ...a, ts: iso(a.ts) })) } : {}),
    ...(m.delib
      ? {
          delib: {
            stages: m.delib.stages,
            personas: m.delib.personas,
            evidence: m.delib.evidence,
            rounds: groupRounds(m.delib.turns),
            decision: m.delib.decision,
            outcome: m.delib.outcome,
          },
        }
      : {}),
    ...(m.error ? { error: m.error } : {}),
  };
}

export function conversationToJson(conv: Conversation): string {
  const doc = {
    schema: 'hwax.chat.export/1',
    exported_at: new Date().toISOString(),
    origin: window.location.origin,
    conversation: {
      id: conv.id,
      title: conv.title,
      server_id: conv.serverId,
      created_at: iso(conv.createdAt),
      updated_at: iso(conv.updatedAt),
      message_count: conv.messages.length,
    },
    messages: conv.messages.map(exportMessage),
  };
  return JSON.stringify(doc, null, 2);
}

export function exportJson(conv: Conversation): void {
  downloadBlob(
    `hwax-대화-${sanitizeFilename(conv.title)}-${stamp()}.json`,
    new Blob([conversationToJson(conv)], { type: 'application/json' }),
  );
}

// ── HTML 내보내기 — 보이는 그대로 ────────────────────────────────────────────

// 같은 오리진 스타일시트의 규칙을 전부 인라인. 상대 url(폰트 등)은 시트 기준 절대 URL 로
// 재작성해, 내보낸 파일을 어디서 열어도 온라인이면 포털에서 폰트를 받아온다(오프라인은 폴백).
function collectCss(): string {
  const out: string[] = [];
  for (const sheet of Array.from(document.styleSheets)) {
    let rules: CSSRuleList;
    try {
      rules = sheet.cssRules; // cross-origin 시트는 접근 시 throw → 건너뜀
    } catch {
      continue;
    }
    const base = sheet.href ?? window.location.href;
    let text = Array.from(rules)
      .map((r) => r.cssText)
      .join('\n');
    text = text.replace(/url\(\s*(['"]?)([^'")]+)\1\s*\)/g, (whole, _q: string, u: string) => {
      if (/^(data:|https?:|blob:|#)/.test(u)) return whole;
      try {
        return `url("${new URL(u, base).href}")`;
      } catch {
        return whole;
      }
    });
    out.push(text);
  }
  return out.join('\n');
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// 내보낸 문서 전용 보정 — 앱 셸 없이 단독 문서로 읽기 좋게. 스크롤 컨테이너(.chat-body)는
// 정적 문서에선 전체 흐름으로 펼친다(뷰포트 높이 박스에 갇히지 않게).
const EXPORT_STYLE = `
  html { background: var(--bg); }
  body.hwax-export { margin: 0; padding: 2rem 1rem 3rem; }
  .hwax-export-main { max-width: 860px; margin: 0 auto; }
  .hwax-export-head { max-width: 860px; margin: 0 auto 1.2rem; padding-bottom: 0.8rem; border-bottom: 1px solid var(--border); }
  .hwax-export-head h1 { font-size: 1.15rem; margin: 0 0 0.3rem; }
  .hwax-export-head p { margin: 0; font-size: 0.78rem; color: var(--muted); }
  .hwax-export .cx-thread-body, .hwax-export .msg-wrap, .hwax-export .chat-body {
    display: block; height: auto; min-height: 0; overflow: visible; flex: none;
  }
  /* 정적 문서 — 진입 애니메이션이 초기 프레임(투명)으로 얼어붙지 않게 전부 비활성 */
  .hwax-export *, .hwax-export *::before, .hwax-export *::after {
    animation: none !important; transition: none !important; opacity: 1;
  }
  .stream-cursor { display: none; }
`;

export function buildExportHtml(threadEl: HTMLElement, conv: Conversation): string {
  const clone = threadEl.cloneNode(true) as HTMLElement;
  // 정적 문서에서 동작하지 않는 인터랙션 제거(복사/토글 버튼, 입력류). sandbox iframe 미리보기는
  // srcdoc 자기완결이라 유지된다.
  clone.querySelectorAll('button, textarea, input, .stream-cursor').forEach((el) => el.remove());
  const when = new Date().toLocaleString('ko-KR');
  return (
    `<!doctype html><html lang="ko"><head><meta charset="utf-8">` +
    `<meta name="viewport" content="width=device-width, initial-scale=1">` +
    `<title>${escapeHtml(conv.title || 'HWAX 대화')}</title>` +
    `<style>${collectCss()}\n${EXPORT_STYLE}</style></head>` +
    `<body class="hwax-export"><header class="hwax-export-head">` +
    `<h1>${escapeHtml(conv.title || 'HWAX 대화')}</h1>` +
    `<p>HWAX 대화 내보내기 · ${escapeHtml(when)} · ${escapeHtml(window.location.origin)} · 메시지 ${conv.messages.length}건</p>` +
    `</header><main class="hwax-export-main">${clone.innerHTML}</main></body></html>`
  );
}

export function exportHtml(threadEl: HTMLElement, conv: Conversation): void {
  downloadBlob(
    `hwax-대화-${sanitizeFilename(conv.title)}-${stamp()}.html`,
    new Blob([buildExportHtml(threadEl, conv)], { type: 'text/html' }),
  );
}
