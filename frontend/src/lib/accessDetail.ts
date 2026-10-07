// 접속 이력의 사유 코드(원장 detail)를 화면 문장으로 바꾼다 — 페이지 파일에서 떼어 내 node 로 돌려 볼 수 있다
// (페이지에서 그냥 export 하면 react-refresh 린트가 막는다 — 컴포넌트 파일은 컴포넌트만 내보낸다)
const DETAIL_LABEL: Record<string, string> = {
  local: '이메일 로그인',
  sso: 'SSO',
  primer: '자동 갱신',
  credential: '자격 중계',
  // 정지된 계정이 SSO 로 들어왔다(사번을 안 받는 박스에서는 세션은 나가고 요청마다 403 이다 — 그래서 '거절' 이라 적지 않는다).
  // 종전엔 라벨이 없어 이 줄만 코드 원문(sso:disabled)으로 나왔다
  'sso:disabled': 'SSO — 정지된 계정',
  // 정지된 사람이 다른 Mail 로 들어오려다 사번으로 걸렸다(SAML_ATTR_SABUN) — 제 이메일의 정지(sso:disabled)와 다른 줄이다
  'sso:disabled:sabun': 'SSO — 거절(같은 사번의 정지된 계정이 있음)',
};

/** affLabels — 소속 id → 라벨(권한 표의 affiliations). 없거나 그 id 가 없으면 id 그대로 보인다. */
export function detailText(d: string | null, affLabels: Record<string, string> = {}): string {
  if (!d) return '';
  if (d.startsWith('local:')) return `이메일 로그인 — ${d.slice(6)}`;
  // SSO 로 처음 생긴 행에 포털이 소속을 넣었다(sso:aff:map|default:<소속>) — 사람이 정한 값이 아니라는 흔적이다
  const aff = /^sso:aff:(map|default):(.+)$/.exec(d);
  if (aff) {
    // 소속은 라벨로 보인다 — 이 줄만 id 원문(CAEG)이었고, 바로 옆 사용자 관리 화면은 같은 소속을 라벨로만 보인다. id 는 괄호로
    // 남긴다: 서버 로그와 박스 파일(access.local.yaml·SSO_DEFAULT_AFFILIATION)이 id 로 적혀 있어 규칙을 찾는 열쇠다.
    // 출처는 무엇으로 맞췄는지 짐작해 적지 않는다 — 원장에는 map|default 만 있고 규칙의 Claim 은 무엇이든 될 수 있다.
    const label = affLabels[aff[2]];
    const who = label && label !== aff[2] ? `${label}(${aff[2]})` : aff[2];
    return `SSO — 첫 로그인, 소속 ${who} 자동 지정(${aff[1] === 'map' ? 'SSO 속성 규칙 · Claim 매핑' : '기본 소속'})`;
  }
  return DETAIL_LABEL[d] ?? d;
}
