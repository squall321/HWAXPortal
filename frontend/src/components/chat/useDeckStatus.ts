// 발표자료로 단추를 보일지 훅 — 포털 /agent/deck/status 를 한 화면에서 한 번만 묻는다(모르면 숨긴다 — WD-D23)
import { useEffect, useState } from 'react';
import { deckStatus, type DeckStatus } from '../../api/deck.api';

// 단추가 메시지마다 서므로 묻기는 하나로 묶는다 — 60초 붙잡는다. 못 물으면 붙잡지 않는다(다음 화면이 다시 묻는다).
const TTL_MS = 60_000;
let cache: { at: number; p: Promise<DeckStatus | null> } | null = null;

function ask(): Promise<DeckStatus | null> {
  const now = Date.now();
  if (cache && now - cache.at < TTL_MS) return cache.p;
  const p = deckStatus().catch(() => null);
  cache = { at: now, p };
  void p.then((v) => {
    if (v === null && cache?.p === p) cache = null;
  });
  return p;
}

/** 시험용 — 붙잡은 답을 버린다. */
export function forgetDeckStatus(): void {
  cache = null;
}

/** 상태 · null(모름 — 아직 못 물었거나 실패). `askIt` 이 거짓이면(권한 없음) 묻지 않는다. */
export function useDeckStatus(askIt: boolean): DeckStatus | null {
  const [st, setSt] = useState<DeckStatus | null>(null);
  useEffect(() => {
    if (!askIt) return;
    let live = true;
    void ask().then((v) => {
      if (live) setSt(v);
    });
    return () => {
      live = false;
    };
  }, [askIt]);
  return st;
}
