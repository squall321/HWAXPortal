// 업데이트 이력 공용 헬퍼 — 팝업과 이력 페이지가 같은 '본 날짜'·같은 날짜 표기를 쓴다
// (컴포넌트는 여기 두지 않는다 — 한 파일이 컴포넌트만 export 해야 Fast Refresh 가 산다)

const SEEN_PREFIX = 'hwax.changelog.seen';

const seenKey = (email: string) => `${SEEN_PREFIX}.${email}`;

/** 이 사람이 마지막으로 본 날짜(ISO). 저장이 막힌 브라우저면 빈 문자열. */
export function readSeen(email: string): string {
  try {
    return localStorage.getItem(seenKey(email)) ?? '';
  } catch {
    return '';
  }
}

/** '여기까지 봤다'를 적는다. 적는 값은 **전체의 최신**(`latest`)이지 화면에 뜬 것의
 *  최신이 아니다 — 분류 필터나 개수 상한에 잘린 항목이 다음에 또 뜨면 안 된다. */
export function writeSeen(email: string, date: string): void {
  try {
    localStorage.setItem(seenKey(email), date);
  } catch {
    /* 사생활 모드 등 — 저장이 막혀도 화면은 정상 동작한다 */
  }
}

/** 날짜를 '9월 9일' 로. 올해가 아니면 연도까지 붙인다.
 *  `today` 는 **서버 기준 오늘**이다 — 사용자 시계가 틀려도 판정이 흔들리지 않게. */
export function dayLabel(iso: string, today: string): string {
  const [y, m, d] = iso.split('-');
  if (!y || !m || !d) return iso;
  const sameYear = today.startsWith(`${y}-`);
  const body = `${Number(m)}월 ${Number(d)}일`;
  return sameYear ? body : `${y}년 ${body}`;
}

/** 요일 한 글자 — 이력 페이지의 날짜 옆에 붙는다. 파싱 실패는 빈 문자열. */
export function weekdayLabel(iso: string): string {
  const t = Date.parse(`${iso}T00:00:00`);
  return Number.isNaN(t) ? '' : ['일', '월', '화', '수', '목', '금', '토'][new Date(t).getDay()];
}
