// 전문가 한 명에 색 하나 — 심의 회의록과 챗 말풍선이 같은 함수를 써야 같은 사람으로 읽힌다
const PALETTE = ['#c0673a', '#3f7d80', '#7a5aa6', '#4a7a3c', '#b08a2a', '#a24a5e', '#3a6ea0', '#6b8e23'];

/** 이름 해시 → 고정 색. 같은 키는 언제 어디서 그려도 같은 색이다. */
export function colorOf(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
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
 *  ⚠ **색은 원래 이름으로 뽑는다.** 축약형으로 뽑으면 같은 사람이 심의(원래 이름)와
 *  챗에서 다른 색이 된다. */
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
