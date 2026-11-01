// 포털이 만든 RA 보고서 옆 '발표자료로' 단추 — 출력을 고르고 맡기면 진행을 보이고, 끝나면 단추를 누른 그 대화에 받기 링크 알림을 남긴다(docs/wda-deck)
import { useEffect, useRef, useState } from 'react';
import { DECK_CHANGED, DeckHttpError, advanceDeck, createDeck, deckJob, type DeckDocStyle, type DeckJob, type DeckTarget } from '../../api/deck.api';
import { useCan } from '../../auth/useCan';
import { config } from '../../config';
import { useChat } from '../../state/ChatContext';
import { DECK_DOC_STYLES, DECK_DOC_TARGETS, DECK_HIDDEN_BACKOFF, DECK_TARGETS, deckSettled, deckSize, deckStateText, type DeckReport } from './deck';
import { forgetDeckStatus, useDeckStatus, useTabVisible } from './useDeckStatus';

// 화면이 진행을 묻는 박자 — WDA 실측 5.5초(11-01)라 3초면 두 번이면 끝난다. 묻기는 포털이 한 번 WDA 에 묻는 가벼운 일이다.
const POLL_MS = 3000;
const POLL_ERR_MAX = 3;

export function DeckSpot({ report }: { report: DeckReport }) {
  const can = useCan();
  const allowed = can('plat:webdesign') && can('plat:reportarchive');
  const status = useDeckStatus(allowed);
  const { activeConversation, conversations, addDeckNotice, afterStream } = useChat();
  const sid = activeConversation?.serverId ?? null;
  const [open, setOpen] = useState(false);
  const [targets, setTargets] = useState<DeckTarget[]>(['pptx', 'pdf']);
  const [docStyle, setDocStyle] = useState<DeckDocStyle>('report');
  const [job, setJob] = useState<DeckJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [paused, setPaused] = useState(false);
  // 창구가 404 — 박스 스위치가 꺼졌거나 그 잡이 없다. 다시 열 때까지 묻지 않는다(WD-D65)
  const [stopped, setStopped] = useState(false);
  const visible = useTabVisible();
  const errs = useRef(0);
  const cb = useRef({ addDeckNotice, afterStream });
  cb.current = { addDeckNotice, afterStream };

  // 진행 — 끝을 적을 때까지. 끝(next)이면 advance 로 한 걸음(렌더 맡기기 · 끝 적기 — 곧바로. 그 대화에 질문이 돌면 서버가 대화 알림만 미룬다,
  // WD-D75). 이 칸이 사라져도 잡은 WDA 에서 돈다 — 입력창 위 '만들고 있는 발표자료' 줄이 이어 보고 끝을 적는다(WD-D9 · D10).
  useEffect(() => {
    if (!job || paused || stopped || deckSettled(job)) return;
    let stop = false;
    const timer = window.setTimeout(async () => {
      try {
        let j = await deckJob(job.job_id);
        if (stop) return;
        if (j.next) j = await advanceDeck(j.job_id);
        if (stop) return;
        if (j.notice) {
          // 서버 사본에는 남았다 — 화면 사본에는 이 탭이 그 대화의 답을 받는 중이면 끝난 뒤에 붙인다(그 사이 칸이 사라져도 붙인다)
          await cb.current.afterStream(j.conversation_id);
          cb.current.addDeckNotice(j.conversation_id, j.notice);
          if (stop) return;
        }
        // 끝은 적었고 알림만 미뤄 두었다 — 이 칸은 묻기를 멈추고 입력창 위 줄이 다음 차례에 알림을 남긴다(지금 목록을 다시 읽게 알린다)
        if (j.next && deckSettled(j)) window.dispatchEvent(new Event(DECK_CHANGED));
        errs.current = 0;
        setJob(j);
      } catch (e) {
        if (stop) return;
        if (e instanceof DeckHttpError && e.status === 404) {
          forgetDeckStatus();
          setErr(`${e.message} — 발표자료 기능이 꺼졌거나 그 잡이 없어 진행 묻기를 멈춥니다.`);
          setStopped(true);
          return;
        }
        errs.current += 1;
        if (errs.current >= POLL_ERR_MAX) {
          setErr(`${e instanceof Error ? e.message : '진행을 못 읽었습니다.'} — 잡은 계속되고, 입력창 위 '만들고 있는 발표자료' 에서 이어 봅니다.`);
          setPaused(true);
        } else {
          setJob((cur) => (cur ? { ...cur } : cur));      // 다시 묻는다
        }
      }
    }, visible ? POLL_MS : POLL_MS * DECK_HIDDEN_BACKOFF);   // 숨은 탭은 천천히 — 보이면 곧바로 이 박자로 돌아온다
    return () => {
      stop = true;
      window.clearTimeout(timer);
    };
  }, [job, paused, stopped, visible]);

  if (!allowed || !sid || !status?.enabled) return null;
  // 심의 보고서는 WDA 가 그 꼴을 알 때만(사용자 결정 11-01 U-6 — '심의 형식이 설 때까지 숨긴다'). 서버가 실제 템플릿으로 다시 막는다.
  if (report.template === 'deliberation' && !status.formats.deliberation) return null;

  const go = async (again = false) => {
    setBusy(true);
    setErr('');
    try {
      const j = await createDeck({ report_id: report.id, conversation_id: sid, targets, doc_style: docStyle, ...(again ? { again: true } : {}) });
      errs.current = 0;
      setPaused(false);
      setOpen(false);
      setJob(j);
    } catch (e) {
      setErr(e instanceof Error ? e.message : '발표자료를 맡기지 못했습니다.');
    } finally {
      setBusy(false);
    }
  };
  const toggle = (k: DeckTarget) => setTargets((cur) => (cur.includes(k) ? cur.filter((x) => x !== k) : [...cur, k]));
  const name = report.title || `보고서 ${report.id}`;

  if (job) {
    const done = deckSettled(job);
    // 같은 보고서 · 옵션의 잡이 다른 대화에서 돌고 있으면 그 잡을 받는다 — 알림은 그 대화에 남는다(WD-D62)
    const here = job.conversation_id === sid;
    const where = here
      ? '이 대화에'
      : `「${conversations.find((c) => c.serverId === job.conversation_id)?.title || '맡긴 대화'}」 대화에`;
    return (
      <div className="upl-panel deck-panel" role="group" aria-label="발표자료">
        <div className="upl-head">
          <b>{job.state === 'done' && done ? '발표자료를 만들었습니다' : job.state === 'failed' && done ? '발표자료를 만들지 못했습니다' : '발표자료 만드는 중'}</b>
          <span className="upl-file">{name}</span>
          {done && <button type="button" className="upl-x" onClick={() => setJob(null)} aria-label="닫기">✕</button>}
        </div>
        {!done && (
          <p className="upl-note" role="status">
            {deckStateText(job)} — 창을 닫아도 계속되고, 끝나면 {where} 받기 링크를 남깁니다
            {here ? '' : '(그 대화에서 맡긴 같은 발표자료입니다)'}.
          </p>
        )}
        {done && job.state === 'done' && job.expired && (
          <p className="upl-note">파일이 WebDesignAgents 에서 지워졌습니다 — 다시 만들 수 있습니다.</p>
        )}
        {done && job.state === 'done' && job.files.length > 0 && (
          <div className="upl-actions deck-files">
            {job.files.map((f) => (
              <a key={f.kind} className="deck-file" href={`${config.apiBase}${f.url}`} download>
                {f.label} 받기{f.bytes ? ` · ${deckSize(f.bytes)}` : ''}
              </a>
            ))}
          </div>
        )}
        {done && job.skipped.length > 0 && (
          <p className="upl-note">
            만들지 않은 것 — {job.skipped.map((s) => `${DECK_TARGETS.find((t) => t.kind === s.target)?.label ?? s.target}${s.reason ? `(${s.reason})` : ''}`).join(' · ')}
          </p>
        )}
        {done && job.state === 'failed' && <div className="upl-err" role="alert">⚠ {job.error || job.step || '까닭을 받지 못했습니다'}</div>}
        {err && <div className="upl-err" role="alert">⚠ {err}</div>}
        {done && (
          <div className="upl-actions">
            <button type="button" className={job.state === 'failed' || job.expired ? 'upl-go' : undefined} disabled={busy}
              onClick={() => void go(true)}>{busy ? '맡기는 중…' : '다시 만들기'}</button>
          </div>
        )}
      </div>
    );
  }

  if (!open) {
    return (
      <div className="deck-spot">
        <button type="button" className="msg-copy deck-go" onClick={() => setOpen(true)}
          title="이 보고서를 내 이름으로 읽어 WebDesignAgents 로 PPT · PDF 를 만듭니다 — 끝나면 이 대화에 받기 링크를 남깁니다">
          <span>발표자료로</span>
        </button>
        {err && <span className="msg-wiki-note is-err" role="status">{err}</span>}
      </div>
    );
  }

  const doc = targets.some((t) => DECK_DOC_TARGETS.includes(t));
  return (
    <div className="upl-panel deck-panel" role="group" aria-label="발표자료로 — 출력 고르기">
      <div className="upl-head">
        <b>발표자료로</b>
        <span className="upl-file">{name}</span>
        <button type="button" className="upl-x" onClick={() => setOpen(false)} aria-label="닫기">✕</button>
      </div>
      <div className="deck-opts">
        {DECK_TARGETS.map((t) => (
          <label key={t.kind}>
            <input type="checkbox" checked={targets.includes(t.kind)} onChange={() => toggle(t.kind)} />
            {t.label}{t.note ? <em> · {t.note}</em> : null}
          </label>
        ))}
      </div>
      {doc && (
        <label className="deck-style">
          문서 꼴
          <select value={docStyle} onChange={(e) => setDocStyle(e.target.value as DeckDocStyle)}>
            {DECK_DOC_STYLES.map((d) => <option key={d.id} value={d.id}>{d.label}</option>)}
          </select>
        </label>
      )}
      <p className="upl-note">
        이 보고서를 내 이름으로 읽어 WebDesignAgents 에 넘깁니다. 파일은 맡긴 사람만 받을 수 있습니다. PDF · Word · HTML 은 같은 내용을 글로 엮은
        문서입니다(슬라이드를 찍은 것이 아닙니다).
      </p>
      {err && <div className="upl-err" role="alert">⚠ {err}</div>}
      <div className="upl-actions">
        <button type="button" className="upl-go" disabled={busy || targets.length === 0} onClick={() => void go()}>
          {busy ? '맡기는 중…' : '만들기'}
        </button>
        <button type="button" onClick={() => setOpen(false)}>취소</button>
      </div>
    </div>
  );
}
