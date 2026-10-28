// 이 박스의 MX 백서 위키 켜짐 여부 훅 — 위키 버튼 · 심의 옵션을 꺼진 박스에서 숨긴다(docs/request-1027 HP-16)
import { useEffect, useState } from 'react';
import { fetchWikiEnabled } from '../../api/wiki.api';

/** true · false · null(모름 — 아직 못 물었거나 서버가 모른다). `ask` 가 거짓이면(권한 없음) 묻지 않는다. */
export function useWikiEnabled(ask: boolean): boolean | null {
  const [on, setOn] = useState<boolean | null>(null);
  useEffect(() => {
    if (!ask) return;
    let live = true;
    void fetchWikiEnabled().then((v) => {
      if (live) setOn(v);
    });
    return () => {
      live = false;
    };
  }, [ask]);
  return on;
}
