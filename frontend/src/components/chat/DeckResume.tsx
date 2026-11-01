// 창을 닫았거나 다른 대화에서 맡긴 발표자료를 입력창 위에서 잇는 줄 — 끝난 잡은 저절로 맡긴 그 대화에 알림을 남긴다(docs/wda-deck WD-D9 · D10)
import { useEffect, useRef, useState } from 'react';
import { DECK_CHANGED, advanceDeck, deckJobs, dismissDeck, type DeckJob } from '../../api/deck.api';
import { useCan } from '../../auth/useCan';
import { useChat } from '../../state/ChatContext';
import { deckOpen, deckStateText } from './deck';
import { useDeckStatus } from './useDeckStatus';

// 끝나지 않은 잡이 있을 때만 다시 묻는다 — 없으면 화면을 열 때 한 번뿐이다.
const REFRESH_MS = 10_000;

export function DeckResume() {
  const can = useCan();
  const allowed = can('plat:webdesign') && can('plat:reportarchive');
  const status = useDeckStatus(allowed);
  const { addDeckNotice, afterStream } = useChat();
  const [jobs, setJobs] = useState<DeckJob[]>([]);
  const [open, setOpen] = useState(false);
  const [tick, setTick] = useState(0);
  const cb = useRef({ addDeckNotice, afterStream });
  cb.current = { addDeckNotice, afterStream };
  const on = Boolean(allowed && status?.enabled);

  useEffect(() => {
    if (!on) return;
    let stop = false;
    void (async () => {
      let list: DeckJob[];
      try {
        list = (await deckJobs()).jobs;
      } catch {
        // 못 읽으면 지금 줄을 그대로 두고 다음 차례에 다시 묻는다 — 같은 배열이면 다시 묻기가 멈춰 끝 알림이 남지 않는다(새 배열로 다음 차례를 건다)
        if (!stop) setJobs((xs) => (xs.length ? [...xs] : xs));
        return;
      }
      // 끝(next)인 잡은 저절로 한 걸음 — 렌더 맡기기 · 끝 알림(알림은 그 사람의 대화에만 쓰므로 다시 묻지 않는다, WD-D10)
      for (const j of list.filter((x) => x.next)) {
        if (stop) return;
        try {
          if (j.next === 'finish') await cb.current.afterStream(j.conversation_id);
          const a = await advanceDeck(j.job_id);
          if (a.notice) cb.current.addDeckNotice(a.conversation_id, a.notice);
          list = list.map((x) => (x.job_id === a.job_id ? a : x));
        } catch {
          // 다음 차례에 다시
        }
      }
      if (!stop) setJobs(list.filter(deckOpen));
    })();
    return () => {
      stop = true;
    };
  }, [on, tick]);

  useEffect(() => {
    if (!jobs.length) return;
    const t = window.setTimeout(() => setTick((n) => n + 1), REFRESH_MS);
    return () => window.clearTimeout(t);
  }, [jobs]);

  // 단추가 새 잡을 맡기면 목록을 다시 읽는다 — 그 칸이 다른 대화로 옮겨 가 사라져도 이 줄이 진행을 잇고 끝을 적는다
  useEffect(() => {
    const bump = () => setTick((n) => n + 1);
    window.addEventListener(DECK_CHANGED, bump);
    return () => window.removeEventListener(DECK_CHANGED, bump);
  }, []);

  if (!on || !jobs.length) return null;
  return (
    <div className="upl-panel df-resume deck-resume">
      <div className="upl-head">
        <b>만들고 있는 발표자료 {jobs.length}건</b>
        <span className="upl-file">끝나면 맡긴 대화에 받기 링크를 남깁니다</span>
        <button type="button" className="upl-x" onClick={() => setOpen((o) => !o)} aria-expanded={open}
          aria-label={open ? '접기' : '펼치기'}>{open ? '▴' : '▾'}</button>
      </div>
      {open && (
        <ul className="df-resume-list">
          {jobs.map((j) => (
            <li key={j.job_id}>
              <span className="upl-file">{j.report.title || `보고서 ${j.report.id}`}</span>
              <span className="upl-note"> {deckStateText(j)} </span>
              <span className="upl-actions">
                <button type="button" onClick={() => {
                  void dismissDeck(j.job_id);
                  setJobs((xs) => xs.filter((x) => x.job_id !== j.job_id));
                }}>숨기기</button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
