// 보내기 결과를 대화의 알림 한 건 · 입력창 지시문으로 옮기는 순수 함수 — 다음 턴이 '방금 보낸 것' 을 알게(docs/chat-ppt A1 · A2)
import type { DispatchResult } from '../../api/upload.api';
import type { WikiSendResult } from '../../api/wiki.api';
import type { ActivityItem } from '../../types/chat';

/** 대화에 남길 알림 — 어시스턴트 메시지 글 하나와 업로드 근거가 될 활동 기록 하나(origin: 'upload'). */
export interface UploadNotice {
  text: string;
  activity: ActivityItem[];
  /** 대화가 없을 때 새 대화의 제목. */
  title: string;
}

// 근거로 싣는 변환 결과의 위쪽 — 대화 저장(서버 사본) · 다음 턴 이력에 함께 간다. 넘으면 앞부분만 싣고 다시 부를 길을 적는다
// (에이전트 서버가 이력 예산 안에서 다시 줄인다 — 여기 상한은 한 건이 대화 하나를 통째로 먹지 않게 하는 바깥 그물이다).
export const NOTICE_RESULT_MAX = 400_000;

function clip(text: string, max = NOTICE_RESULT_MAX): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max)}\n…(뒤 ${(text.length - max).toLocaleString()}자 생략 — 같은 도구로 다시 부르면 전부 나온다)`;
}

function preview(text: string): string {
  const one = text.replace(/\s+/g, ' ').trim();
  return one.length > 220 ? `${one.slice(0, 220)}…` : one;
}

/** 위키 보내기 결과 → 대화 알림 한 건(origin: 'upload') — 다음 턴이 '이 답을 위키에 남겼다' 를 안다(docs/mxwp-wiki P6 · P7). */
export function wikiNotice(r: WikiSendResult, now = Date.now()): UploadNotice {
  const src = r.short || r.id;
  const where = (r.audience ?? []).join(', ');
  const facts = { source: src, mode: r.mode, audience: r.audience ?? [], dedup: Boolean(r.dedup),
                  doc_slug: r.doc_slug ?? null, ingest_state: r.ingest_state ?? null };
  const full = JSON.stringify(facts);
  const candidate = r.mode === 'candidate';
  const text = candidate
    ? `이 답을 MX 백서 위키 후보로 보냈습니다 — 원천 ${src}. 나만 보는 후보이고, MX 백서 '내 후보' 에서 범위(제안 ${where})를 골라 `
      + '승인하면 위키에 들어갑니다(승인하지 않으면 7일 뒤 버려집니다).'
    : r.dedup
      ? `이 답은 이미 MX 백서 위키에 남아 있습니다 — 원천 ${src}(범위 ${where}).`
      : `이 답을 MX 백서 위키에 남겼습니다 — 원천 ${src}(범위 ${where}). 위키가 이 질문 · 답 · 조회 근거를 관련 문서에 엮습니다.`;
  return {
    title: 'MX 백서 위키',
    text,
    activity: [{
      ts: now, step: candidate ? 'MX 백서 위키 후보(사람이 보냄)' : 'MX 백서 위키에 남김(사람이 보냄)', tool: 'wiki_submit_source',
      detail: JSON.stringify({ mode: r.mode }), result_full: full, result_preview: preview(full), ok: true, origin: 'upload',
    }],
  };
}

/** 보내기 성공 → 알림. 문서 갈래(RA · AIDH) · SimFlow 가 아니거나 실패면 null(알림을 남기지 않는다). */
export function dispatchNotice(filename: string, r: DispatchResult, now = Date.now()): UploadNotice | null {
  if (r.stage !== 'done') return null;
  if (r.destination === 'aidatahub' && r.inbox_name) {
    const raw = JSON.stringify(r.result ?? {});
    const full = clip(raw);
    return {
      title: `${filename} — AI 데이터 허브 변환`,
      text: `「${filename}」 을 AI 데이터 허브로 보내 변환했습니다 — inbox 파일 \`${r.inbox_name}\`, 지식카드 초안 `
        + `${raw.length.toLocaleString()}자(아직 저장하지 않았습니다). 이 초안은 다음 질문의 근거로 함께 갑니다.`,
      activity: [{
        ts: now, step: 'AI 데이터 허브로 보내 변환(사람이 올림)', tool: 'convert_file',
        detail: JSON.stringify({ file: r.inbox_name }), result_full: full, result_preview: preview(full), ok: true, origin: 'upload',
      }],
    };
  }
  if (r.destination === 'reportarchive' && r.report_id != null) {
    const warns = r.warnings ?? [];
    const facts = { report_id: r.report_id, title: r.title ?? null, pages: r.pages ?? null, blocks: r.blocks ?? null,
                    url: r.url ?? null, warnings: warns };
    const full = clip(JSON.stringify(facts));
    return {
      title: `${filename} — Report Archive 초안`,
      text: `「${filename}」 으로 Report Archive 보고서 초안을 만들었습니다 — 보고서 ${r.report_id}`
        + `${r.title ? `「${r.title}」` : ''} · ${r.pages ?? '?'}쪽 · 블록 ${r.blocks ?? '?'}개`
        + `${warns.length ? ` · 변환하지 못한 요소 ${warns.length}건` : ''}(초안입니다 — 확인한 뒤 저장 · 게시하세요).`,
      activity: [{
        ts: now, step: 'Report Archive 보고서 초안(사람이 올림)', tool: 'create_report_draft',
        detail: JSON.stringify({ file: filename }), result_full: full, result_preview: preview(full), ok: true, origin: 'upload',
      }],
    };
  }
  if (r.destination === 'reportarchive_precise' && r.report_id != null) {
    // 변환 보고서 요약을 함께 — 쪽 · 블록 · 버린 것 · 모델 판독 · 무음 누락(DocForge 는 무음 누락이 있으면 패키지를 만들지 않는다, DF-D17)
    const warns = [...(r.warnings ?? []), ...(r.conversion_warnings ?? [])];
    const facts = { report_id: r.report_id, title: r.title ?? null, pages: r.pages ?? null, blocks: r.blocks ?? null,
                    dropped: r.dropped ?? 0, model_written: r.model_written ?? 0, unaccounted: r.unaccounted ?? 0,
                    fidelity: r.fidelity ?? null, url: r.url ?? null, warnings: warns };
    const full = clip(JSON.stringify(facts));
    const mw = r.model_written ?? 0;
    return {
      title: `${filename} — Report Archive 정밀 변환`,
      text: `「${filename}」 을 정밀 변환해 Report Archive 보고서를 만들었습니다 — 보고서 ${r.report_id}`
        + `${r.title ? `「${r.title}」` : ''} · ${r.pages ?? '?'}쪽 · 블록 ${r.blocks ?? '?'}개 · 버린 요소 ${r.dropped ?? 0}건(까닭은 변환 보고서) · `
        + `모델 판독 ${mw}건 · 무음 누락 ${r.unaccounted ?? 0}`
        + `${r.fidelity === 'drm_bundle' ? ' · PC 추출본으로 만들어 충실도가 낮습니다' : ''}.`
        + `${mw ? ' \'모델 판독\' 블록은 모델이 그림을 읽은 것이니 원본과 맞는지 확인하세요.' : ''}`
        + `${warns.length ? ` 경고 ${warns.length}건.` : ''}`,
      activity: [{
        ts: now, step: 'Report Archive 정밀 변환(사람이 올림)', tool: 'docforge_convert',
        detail: JSON.stringify({ file: filename }), result_full: full, result_preview: preview(full), ok: true, origin: 'upload',
      }],
    };
  }
  if (r.destination === 'simflow' && r.upload_id) {
    // 받은 id 를 글로 박는다 — 다음 턴이 그 id 로 run_workflow 를 부를 수 있게(docs/request-1027 HP-15). DRM 을 아직 푸는 중이면 그렇다고.
    const st = r.upload_status || '?';
    const facts = { upload_id: r.upload_id, status: st, size: r.size ?? null, note: r.note ?? null };
    const full = clip(JSON.stringify(facts));
    return {
      title: `${filename} — SimFlow 업로드`,
      text: `「${filename}」 을 SimFlow 에 올렸습니다 — 업로드 id \`${r.upload_id}\` · 상태 ${st}.`
        + (st === 'drm_pending' ? ' SimFlow 가 아직 DRM 을 푸는 중입니다 — ready 가 된 뒤 run_workflow 에 이 id 를 쓰세요.'
          : ' 이 id 를 run_workflow 의 입력으로 쓸 수 있습니다.'),
      activity: [{
        ts: now, step: 'SimFlow 업로드(사람이 올림)', tool: 'mcp-uploads',
        detail: JSON.stringify({ file: filename }), result_full: full, result_preview: preview(full), ok: true, origin: 'upload',
      }],
    };
  }
  return null;
}

/** 입력창에 넣을 지시문 — 이름 · 번호를 글로 박는다. 근거가 이력 예산에 밀려 '도구 이름만' 남아도 모델이 다시 부를 수 있게(PP-D4). */
export function dispatchInstruction(r: DispatchResult): string {
  if (r.stage !== 'done') return '';
  if (r.destination === 'aidatahub' && r.inbox_name) {
    return `AI 데이터 허브 inbox 파일 \`${r.inbox_name}\` 을 convert_file 로 변환한 초안을 검토하고, 모자란 항목은 `
      + 'import_record(dry_run=true)로 물어봐 줘';
  }
  if ((r.destination === 'reportarchive' || r.destination === 'reportarchive_precise') && r.report_id != null) {
    return `Report Archive 보고서 ${r.report_id}${r.title ? `(「${r.title}」)` : ''}를 get_report_outline · get_report 로 읽고 검토해 줘`;
  }
  if (r.destination === 'simflow' && r.upload_id) {
    return `SimFlow 업로드 \`${r.upload_id}\` 를 입력으로 쓸 워크플로를 골라 run_workflow 로 돌려 줘`;
  }
  return '';
}

/** 만든 보고서를 여는 주소 — RA 가 준 `/w/<공간>/reports/<번호>` 를 포털의 RA 경로 아래로. 모르면 null. */
export function reportLink(r: DispatchResult): string | null {
  return typeof r.url === 'string' && r.url.startsWith('/') ? `/report-archive${r.url}` : null;
}
