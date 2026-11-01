// 창을 닫았거나 다른 대화에서 맡긴 발표자료를 입력창 위에서 잇는 줄 — 끝난 잡은 저절로 맡긴 그 대화에 알림을 남긴다(docs/wda-deck WD-D9 · D10)
import { useEffect, useRef, useState } from 'react';
import { DECK_CHANGED, DeckHttpError, advanceDeck, deckJobs, dismissDeck, type DeckJob } from '../../api/deck.api';
import { useCan } from '../../auth/useCan';
import { useChat } from '../../state/ChatContext';
import { DECK_HIDDEN_BACKOFF, deckOpen, deckStateText } from './deck';
import { forgetDeckStatus, useDeckStatus, useTabVisible } from './useDeckStatus';

// 끝나지 않은 잡이 있을 때만 다시 묻는다 — 없으면 화면을 열 때 한 번뿐이다.
const REFRESH_MS = 10_000;

export function DeckResume() {
  const can = useCan();
  const allowed = can('plat:webdesign') && can('plat:reportarchive');
  const status = useDeckStatus(allowed);
  const { addDeckNotice, afterStream } = useChat();
  // 줄에 보일 것 — 끝나지 않았고 숨기지 않은 잡. 숨긴 잡도 끝날 때까지 한 걸음씩 가고 끝 알림을 남긴다(화면에만 없다, WD-D59)
  const [jobs, setJobs] = useState<DeckJob[]>([]);
  const [open, setOpen] = useState(false);
  const [tick, setTick] = useState(0);
  // 다시 묻기 차례 — 끝나지 않은 잡(숨긴 것 포함)이 있으면 다음 차례를 건다. 못 읽은 차례도 그 앞의 수로 건다(WD-D41)
  const [round, setRound] = useState(0);
  const openCount = useRef(0);
  // 창구가 404 — 박스 스위치가 꺼졌다. 다시 열 때까지 묻지 않는다(WD-D65)
  const [stopped, setStopped] = useState(false);
  const visible = useTabVisible();
  const cb = useRef({ addDeckNotice, afterStream });
  cb.current = { addDeckNotice, afterStream };
  const on = Boolean(allowed && status?.enabled);

  useEffect(() => {
    if (!on || stopped) return;
    let stop = false;
    void (async () => {
      let list: DeckJob[];
      try {
        list = (await deckJobs()).jobs;
      } catch (e) {
        if (stop) return;
        if (e instanceof DeckHttpError && e.status === 404) {
          forgetDeckStatus();
          openCount.current = 0;
          setJobs([]);
          setStopped(true);
          return;
        }
        // 못 읽으면 지금 줄을 그대로 두고 다음 차례에 다시 묻는다 — 끝나지 않은 잡이 있었을 때만
        if (openCount.current) setRound((r) => r + 1);
        return;
      }
      // 끝(next)인 잡은 저절로 한 걸음 — 렌더 맡기기 · 끝 알림(숨긴 잡도). 알림은 그 사람의 대화에만 쓰므로 다시 묻지 않는다(WD-D10)
      for (const j of list.filter((x) => x.next)) {
        if (stop) return;
        try {
          if (j.next === 'finish') await cb.current.afterStream(j.conversation_id);
          const a = await advanceDeck(j.job_id);
          if (a.notice) cb.current.addDeckNotice(a.conversation_id, a.notice);
          list = list.map((x) => (x.job_id === a.job_id ? { ...a, dismissed: x.dismissed } : x));
        } catch {
          // 다음 차례에 다시
        }
      }
      if (stop) return;
      const live = list.filter(deckOpen);
      openCount.current = live.length;
      setJobs(live.filter((j) => !j.dismissed));
      if (live.length) setRound((r) => r + 1);
    })();
    return () => {
      stop = true;
    };
  }, [on, tick, stopped]);

  useEffect(() => {
    if (!round || stopped) return;
    // 숨은 탭은 천천히 — 보이게 되면 이 효과가 다시 돌아 곧 박자로 돌아온다
    const t = window.setTimeout(() => setTick((n) => n + 1), visible ? REFRESH_MS : REFRESH_MS * DECK_HIDDEN_BACKOFF);
    return () => window.clearTimeout(t);
  }, [round, visible, stopped]);

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
