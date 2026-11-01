// 심의 결과 카드의 Report Archive 링크 — RA 가 준 보고서 주소로 바로 열고, 주소가 없는 옛 카드는 포털에 물어 연다(docs/wda-deck WD-D78)
import { apiFetch } from '../../api/client';

/** RA 첫 화면 — RA 가 그 사람의 기본 공간으로 보낸다. 열 곳을 모를 때의 자리(오류 JSON 대신). */
export const RA_HOME = '/report-archive/';
const RA_URL = /^\/w\/(?!\.{1,2}\/)[A-Za-z0-9._-]{1,120}\/reports\/([0-9]{1,18})$/;

/** RA 가 준 주소(/w/<공간>/reports/<번호>) → 포털의 RA 경로. 꼴이 틀리거나 번호가 다르면 null — 그때는 번호로 물어 연다(openRaReport). */
export function raReportHref(url: unknown, reportId: number): string | null {
  if (typeof url !== 'string') return null;
  const m = RA_URL.exec(url);
  return m && Number(m[1]) === reportId ? `/report-archive${url}` : null;
}

/** 주소가 없는 옛 카드를 누른 순간 — 빈 탭을 열 수 있으면 오프너를 끊고 포털에 그 보고서의 공간을 물어(세션이 지났으면 apiFetch 가 되살려 다시
 *  묻는다) 그 탭을 옮기고 true(화면은 링크의 기본 이동을 막는다). 못 물으면(권한 없음 · 세션을 되살리지 못함 · 끊김) 그 탭은 RA 첫 화면으로 간다.
 *  탭을 못 열면(팝업 막기) false — 묻지 않는다. 화면은 기본 이동을 막지 않아 링크(RA 첫 화면 · 새 탭)가 그대로 간다. 기다린 뒤의 window.open 은
 *  사용자 동작 밖이라 또 막히므로 그 길은 두지 않는다(WD-D84). 탭은 누른 순간에 연다 — 물은 뒤에 열면 팝업 막기에 걸린다. */
export function openRaReport(reportId: number): boolean {
  const w = window.open('', '_blank');
  if (!w) return false;
  w.opener = null;
  void (async () => {
    let target = RA_HOME;
    try {
      const r = await apiFetch(`/agent/ra/reports/${reportId}/open`);
      const j = (await r.json().catch(() => ({}))) as { url?: unknown };
      if (r.ok && typeof j.url === 'string' && j.url.startsWith(RA_HOME)) target = j.url;
    } catch {
      // RA 첫 화면으로
    }
    w.location.replace(target);
  })();
  return true;
}
