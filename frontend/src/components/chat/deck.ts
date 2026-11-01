// 발표자료로 — 메시지에서 단추가 설 RA 보고서를 찾고(자리 셋) 잡 상태를 사람 말로 옮기는 순수 함수(docs/wda-deck)
import type { DeckDocStyle, DeckJob, DeckTarget } from '../../api/deck.api';

/** 숨은 탭에서 묻는 박자를 몇 배로 늦출까 — 보이게 되면 곧바로 다시 묻는다(WD-D65). */
export const DECK_HIDDEN_BACKOFF = 10;
import type { Message } from '../../types/chat';

/** 단추가 설 보고서. template 은 화면이 자리로 아는 값이다 — 서버는 RA 에서 읽은 실제 템플릿으로 다시 막는다(WD-D29). */
export interface DeckReport {
  id: number;
  title: string;
  /** deliberation — 심의 결과 카드 · '/보고서' 저장 답(에이전트 서버가 deliberation 템플릿으로 만든다). other — RA 보내기 알림(__import_blank__). */
  template: 'deliberation' | 'other';
}

// RA 보내기 알림의 도구 — PPT 가져오기(create_report_draft)와 정밀 변환(docforge_convert). 근거(result_full)에 보고서 번호가 있다(uploadNotice.ts).
const RA_UPLOAD_TOOLS = new Set(['create_report_draft', 'docforge_convert']);

function posInt(v: unknown): number | null {
  if (typeof v === 'number' && Number.isInteger(v) && v > 0) return v;
  if (typeof v === 'string' && /^\d+$/.test(v.trim())) {
    const n = Number(v.trim());
    return n > 0 ? n : null;
  }
  return null;
}

/** 이 메시지 옆에 '발표자료로' 단추가 설 보고서 — 심의 결과(delib.outcome) · '/보고서' 답(raReport) · RA 보내기 알림(활동 근거). 없으면 null. */
export function deckReportOf(msg: Message): DeckReport | null {
  if (msg.role !== 'assistant' || msg.streaming) return null;
  const o = msg.delib?.outcome;
  if (o) {
    const id = posInt(o.report_id);
    return id ? { id, title: o.title ?? '', template: 'deliberation' } : null;
  }
  if (msg.raReport) {
    const id = posInt(msg.raReport.id);
    if (id) return { id, title: msg.raReport.title ?? '', template: 'deliberation' };
  }
  for (const a of msg.activity ?? []) {
    if (a.origin !== 'upload' || !a.tool || !RA_UPLOAD_TOOLS.has(a.tool) || a.ok === false) continue;
    try {
      const f = JSON.parse(a.result_full ?? a.result_preview ?? '') as { report_id?: unknown; title?: unknown };
      const id = posInt(f?.report_id);
      if (id) return { id, title: typeof f.title === 'string' ? f.title : '', template: 'other' };
    } catch {
      // 근거가 JSON 이 아니면(잘린 미리보기) 단추를 세우지 않는다
    }
  }
  return null;
}

/** 잡 상태 → 한 줄('장면 구성 · 2분', 늦으면 '— 오래 걸립니다'). */
export function deckStateText(j: Pick<DeckJob, 'state' | 'step' | 'elapsed_s' | 'late'>): string {
  const s = Math.max(0, Math.round(j.elapsed_s || 0));
  const t = s >= 60 ? `${Math.floor(s / 60)}분` : `${s}초`;
  switch (j.state) {
    case 'queued':
      return `줄 서는 중 · ${t}`;
    case 'preparing':
    case 'rendering':
      return `${j.step || '만드는 중'} · ${t}${j.late ? ' — 오래 걸립니다' : ''}`;
    case 'done':
      return '끝';
    default:
      return '만들지 못했습니다';
  }
}

/** 바이트 → '1.2 MB'(모르면 빈 글). */
export function deckSize(bytes: number | null | undefined): string {
  if (typeof bytes !== 'number' || bytes < 0) return '';
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export const DECK_TARGETS: { kind: DeckTarget; label: string; note?: string }[] = [
  { kind: 'pptx', label: 'PPT', note: '글자를 고칠 수 있는 꼴' },
  { kind: 'pdf', label: 'PDF' },
  { kind: 'docx', label: 'Word' },
  { kind: 'html', label: 'HTML' },
  { kind: 'video', label: '영상', note: '오래 걸립니다' },
];

export const DECK_DOC_STYLES: { id: DeckDocStyle; label: string }[] = [
  { id: 'report', label: '정식 보고서' },
  { id: 'brief', label: '요약(2~3쪽)' },
  { id: 'memo', label: '1쪽 메모' },
];

/** 문서 꼴(report · brief · memo)이 뜻을 갖는 출력 — PDF · Word · HTML 은 WDA 의 '읽는 문서' 다(WD-D17). */
export const DECK_DOC_TARGETS: DeckTarget[] = ['pdf', 'docx', 'html'];

/** 끝나지 않은 잡 — 아직 끝을 적지 않았거나(next) 진행 중이다. 알림만 미뤄 둔 잡도 여기 든다(줄이 다음 차례에 알림을 남긴다). */
export function deckOpen(j: Pick<DeckJob, 'state' | 'next'>): boolean {
  return j.next != null || (j.state !== 'done' && j.state !== 'failed');
}

/** 끝을 적은 잡 — 받기 링크 · 까닭이 섰다. 대화 알림만 미뤄 둔 잡(notice_pending — next 는 finish 로 남는다, WD-D75)도 끝이다. */
export function deckSettled(j: Pick<DeckJob, 'state' | 'next' | 'notice_pending'>): boolean {
  return (j.state === 'done' || j.state === 'failed') && (!j.next || Boolean(j.notice_pending));
}
