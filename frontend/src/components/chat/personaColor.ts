// 전문가 한 명에 색 하나 — 모든 화면이 같은 함수에 같은 입력(키)을 넣어야 같은 사람으로 읽힌다
const PALETTE = ['#c0673a', '#3f7d80', '#7a5aa6', '#4a7a3c', '#b08a2a', '#a24a5e', '#3a6ea0', '#6b8e23'];

/** 전문가 **키** 해시 → 고정 색. 같은 키는 언제 어디서 그려도 같은 색이다.
 *
 *  ⚠ 이름을 넣지 않는다. 이름은 화면마다 다른 꼴로 온다 — 고르기 화면 · 챗 말풍선은 카탈로그의 원래 이름
 *  (`… 전문가 (… Expert)`), 회의록 · 관계도는 명부로 찾은 축약형이고 못 찾으면 키다. 심의 발언에는 처음부터 키만 실린다
 *  (엔진 · MCP 워크플로가 좌석 키를 싣는다). 이름으로 뽑는 화면과 키로 뽑는 화면이 섞여 같은 사람이 화면마다 다른 색이었다
 *  (docs/leftovers-1017/triage-1031.md B12). 키는 어느 화면에나 있고 꼴이 하나다. */
export function colorOf(key: string): string {
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

/** 아바타에 넣을 한 글자. 기호를 걷어내고 첫 글자만. */
export const initialOf = (name: string) =>
  (name.replace(/[^0-9A-Za-z가-힣]/g, '')[0] ?? '·').toUpperCase();

/** 표시용 짧은 이름. 카탈로그 이름은 `한국어 이름 (English Name)` 꼴이라 그대로 쓰면
 *  목록·칩·말풍선이 전부 두 줄이 된다. 뒤에 붙은 **영문 괄호만** 떼고, 이름 안에 든
 *  한글 괄호(`지문 센서(초음파·광학) 전문가`)는 그대로 둔다.
 *
 *  ⚠ 괄호가 중첩된다 — `… (Fingerprint Sensor (Ultrasonic & Optical) Expert)`. 정규식
 *  하나로는 못 잘라서 뒤에서부터 깊이를 세며 짝을 찾는다.
 *
 *  ⚠ 이 결과로 색을 뽑지 않는다 — 색은 키로 뽑는다(colorOf). 축약은 표시만 줄인다. */
export function shortName(name: string): string {
  const t = name.trim();
  if (!t.endsWith(')')) return name;
  let depth = 0;
  let open = -1;
  for (let i = t.length - 1; i >= 0; i--) {
    if (t[i] === ')') depth++;
    else if (t[i] === '(') {
      depth--;
      if (depth === 0) {
        open = i;
        break;
      }
    }
  }
  if (open <= 0) return name;
  const head = t.slice(0, open).trim();
  const inner = t.slice(open + 1, t.length - 1);
  // 한글 이름 뒤의 영문 부기일 때만 떼어 낸다.
  return head && /[가-힣]/.test(head) && !/[가-힣]/.test(inner) ? head : name;
}
