// 행선지 ↔ 게이트웨이 앱 매핑 — 지금 고른 전문가가 그 앱 운영자면 그쪽을 앞세우기 위한 표
//
// 전문가를 고르면 그 사람의 앱이 pinnedApps 로 묶인다(infra/personas/he-team.json 의 apps).
// 그래서 '지금 이 전문가와 대화 중' 이라는 사실만으로 어디로 보낼지 짐작할 수 있다.
// 짐작일 뿐이라 **자동으로 보내지는 않는다** — 앞에 놓고 미리 채워 둘 뿐이고, 보내는 건 사람이다.
//
// 새 행선지를 만들면 여기 한 줄 더한다. 안 더해도 동작은 한다(추천이 안 뜰 뿐).
export const DEST_APPS: Record<string, string[]> = {
  // 파일 업로드 목적지(UploadRouter)
  material: ['heax-materialtwin_web'],
  stepforge: ['heax-step_forge'],
  dynaforge: ['heax-kooremapper_mcp'],
  reportarchive: ['reportarchive'],
  aidatahub: ['ai-data-hub'],
  // 문서 행선지(DocActions)
  card: ['ai-data-hub'],
  report: ['reportarchive'],
  wiki: ['mx-white-paper'],
  paper: ['heax-paper_ingest'],
  dyna: ['heax-kooremapper_mcp'],
  delib: ['hwax-deliberation'],
};
