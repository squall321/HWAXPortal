// 포털 로그인 → ste 자격을 받아 브라우저에 놓아 둔다(ste 에 따로 로그인하지 않게)
//
// `/ste/` 는 포털과 **같은 오리진**이라, 여기서 localStorage 에 넣어 두면 ste SPA 가
// 그대로 읽는다 — ste 프론트는 한 줄도 안 고친다.
//
// ⚠ **자주 태우면 안 된다.** ste 는 재발급이 같은 통로의 직전 토큰을 **회수**한다
//    (만료 컬럼이 없어 회전이 유일한 수명 통제다). 주기적으로 부르면 먼저 열어 둔 탭의
//    토큰이 죽는다. 그래서 여기서는 **브라우저 세션당 한 번**, 그리고 토큰이 없을 때만 부른다.
import { useEffect, useRef } from 'react';
import { fetchSteCredential } from '../../api/ste.api';

const TOKEN_KEY = 'ste.token';
const FLAG = 'hwax.ste.primed';

function read(store: Storage, key: string): string | null {
  try {
    return store.getItem(key);
  } catch {
    return null;                                   // 사생활 보호 모드 등 — 기능만 꺼진다
  }
}

function write(store: Storage, key: string, value: string): void {
  try {
    store.setItem(key, value);
  } catch {
    /* 저장이 막혔으면 이번 탭에서는 ste 가 자기 로그인 화면을 보여 줄 뿐이다 */
  }
}

/** 화면에는 아무것도 그리지 않는다. */
export function StePrimer({ enabled }: { enabled: boolean }) {
  const doneRef = useRef(false);

  useEffect(() => {
    if (!enabled || doneRef.current) return;
    doneRef.current = true;                        // StrictMode 의 두 번째 실행까지 막는다
    if (read(sessionStorage, FLAG) === '1' && read(localStorage, TOKEN_KEY)) return;
    fetchSteCredential()
      .then((cred) => {
        if (cred?.token) write(localStorage, TOKEN_KEY, cred.token);
        write(sessionStorage, FLAG, '1');
      })
      .catch(() => {
        // ste 가 안 떠 있어도 포털은 그대로 쓴다. 다음 브라우저 세션에 다시 시도한다.
      });
  }, [enabled]);

  return null;
}

/** 로그아웃 때 브라우저 사본을 지운다. 서버 회수는 별도다 — 둘 다 해야 회수다. */
export function clearSteCredential(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(FLAG);
  } catch {
    /* 지울 수 없으면 서버 회수만으로 죽는다 */
  }
}
