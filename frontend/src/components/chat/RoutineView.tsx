// 분석 루틴 진행 — 어시스턴트 메시지 안(보고서 글 위)의 단계 칩 · 고를 것 · 이어서 · 멈춤 · 보고서 보기 · RA 초안 올리기. 흐르지 않는 메시지는 화면에 보일 때만 포털 원장에서 다시 읽는다(docs/analysis-routines R3 §6)
import { useEffect, useId, useMemo, useRef, useState, type RefObject } from 'react';
import { cancelRun, getRun, getRunReport, pickCandidate, type RunView } from '../../api/routines.api';
import { useCan } from '../../auth/useCan';
import { routineStopNote } from '../../lib/chatErrors';
import { useChat } from '../../state/ChatContext';
import type { Message, RoutineState } from '../../types/chat';
import { TextBlock } from './renderers/TextBlock';
import {
  ROUTINE_POLL_MS,
  ROUTINE_RUN_LABEL,
  ROUTINE_STEP_LABEL,
  SR_ONLY,
  isRoutineLive,
  isRoutineTerminal,
  nextRoutinePoll,
  routineFromRunView,
  type RoutinePoll,
} from './routine';

// 받는 중(챗 스트림이 도는 동안)에는 이어서 · 고르기 · RA 초안 올리기를 꺼 두고 까닭을 단추 title 로 보인다. 셋 다 챗 턴으로 가는데 챗은 한 번에
// 한 스트림이라 받는 중에 보낸 잇기는 조용히 버려진다(ChatContext sendMessage) — 고르기는 원장에서 고른 뒤 잇지 못해 실행을 아무도 돌리지 않는 채
// 남는다. 멈춤은 이 실행을 받고 있는 메시지에서는 켜 둔다 — 포털로 바로 가는 부름(cancelRun)이라 받는 중에도 되고, 실행기가 다음 검사에서 멈춘
// 것을 보고 done(cancelled) 로 스트림을 닫는다. ■ 는 받기만 끊고 실행은 서버에서 계속 돌므로 한 번에 그치는 길은 이 단추다. 다른 답을 받는
// 중에만 꺼 둔다.
const STREAMING_TIP = {
  resume: '답을 받는 중이라 이을 수 없습니다 — 받기가 끝나거나 ■ 로 끊은 뒤 잇습니다',
  pick: '답을 받는 중이라 고를 수 없습니다 — 받기가 끝나거나 ■ 로 끊은 뒤 고릅니다',
  stop: '다른 답을 받는 중이라 멈출 수 없습니다 — 받기가 끝나거나 ■ 로 끊은 뒤 멈춥니다',
  upload: '답을 받는 중이라 올릴 수 없습니다 — 받기가 끝나거나 ■ 로 끊은 뒤 올립니다',
};
const STOP_TIP = '실행을 멈춥니다 — ■ 는 받기만 끊고 실행은 서버에서 계속 돌므로, 그치려면 이 단추를 누릅니다';
const errText = (e: unknown) => (e instanceof Error ? e.message : String(e));
const hasRaId = (v: unknown) => v != null && v !== '';
// 'RA 초안 올리기' 를 낼 보고서 — 끝에 묻는 루틴(ask), 또는 저절로 올리기(auto)가 실패한 루틴(오류만 있다 — 토큰을 등록한 뒤 같은 길로 다시
// 올린다, R3 반대 검토 2차 #15). 오류가 없는 auto 는 올리는 중이거나 올렸다 — 내지 않는다.
const raAskable = (r: RoutineState['report']) => r?.ra_upload === 'ask' || (r?.ra_upload === 'auto' && Boolean(r.ra_error));

// 이 칸이 화면에 보이는가 — 닫힌 독(화면 밖으로 밀어 둔다) · 스크롤로 벗어난 메시지 · 숨은 탭은 보이지 않는다(R3 §6 '화면에 보일 때만').
// 처음은 '안 보임' 이다 — IntersectionObserver 는 지켜보기 시작하면 곧 한 번 알린다. 그것이 없는 곳(서버 렌더 · 오래된 브라우저)은 탭만 본다.
function useOnScreen(ref: RefObject<HTMLElement>): boolean {
  const [inView, setInView] = useState(() => typeof IntersectionObserver === 'undefined');
  const [tabShown, setTabShown] = useState(() => typeof document === 'undefined' || document.visibilityState === 'visible');
  useEffect(() => {
    const onVis = () => setTabShown(document.visibilityState === 'visible');
    document.addEventListener('visibilitychange', onVis);
    return () => document.removeEventListener('visibilitychange', onVis);
  }, []);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;
    const io = new IntersectionObserver((entries) => setInView(entries[entries.length - 1].isIntersecting));
    io.observe(el);
    return () => io.disconnect();
  }, [ref]);
  return inView && tabShown;
}

export function RoutineView({ msg }: { msg: Message }) {
  const base = msg.routine as RoutineState;
  const live = Boolean(msg.streaming);
  const { streaming, resumeRoutine, streamLive } = useChat();
  // 기다린 뒤 잇는 길(고르기)은 누른 때의 함수가 아니라 지금 함수로 부른다 — 누른 때의 함수는 그새 시작한 다른 답을 모른다(R3 반대 검토 2차 #12)
  const resumeRef = useRef(resumeRoutine);
  resumeRef.current = resumeRoutine;
  // 지난 루틴 턴을 보는 것은 누구나, 원장을 읽고 잇고 멈추는 것은 루틴 권한이 있어야 한다(포털 /routines-api 가 같은 권한을 본다)
  const allowed = useCan()('feat:routines');
  const uid = useId();
  const boxRef = useRef<HTMLElement>(null);
  const onScreen = useOnScreen(boxRef);
  const [view, setView] = useState<RunView | null>(null);
  const [reload, setReload] = useState(0);
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [stopped, setStopped] = useState(false);
  const [err, setErr] = useState('');
  const [report, setReport] = useState<string | null>(null);
  const [reportOpen, setReportOpen] = useState(false);
  const [raSent, setRaSent] = useState(false);
  // 고른 뒤 다른 답을 받는 중이라 잇지 못했다 — 받기가 끝나면 '이어서' 를 누르라는 말. 다시 읽기의 setErr('') 가 지우지 않게 따로 쥔다
  const [pickNote, setPickNote] = useState('');
  // 멈춤 · RA 초안 올리기 · 고르기의 결과를 낭독기에 알리는 줄(SR_ONLY) — 그 단추가 사라지거나 꺼지면 아무것도 들리지 않았다(R3 반대 검토 2차 #17)
  const [said, setSaid] = useState('');
  // 누른 단추가 사라지거나 꺼지면(바쁨 · 받는 중) 포커스가 문서(body)로 떨어진다 — 그 동작 뒤 다음 그리기에서 이 칸으로 돌린다. 사람이 그새
  // 다른 곳으로 옮겼으면 그대로 둔다.
  const refocus = useRef(false);
  useEffect(() => {
    if (!refocus.current) return;
    refocus.current = false;
    const box = boxRef.current;
    const a = document.activeElement;
    if (box && (!a || a === document.body || (box.contains(a) && (a as HTMLButtonElement).disabled))) box.focus({ preventScroll: true });
  });
  const runId = base.run_id;

  // 흐르지 않는 메시지 — 단계가 비었거나(서버 저장본은 run_id · 제목 · 상태 포인터만 남는다, R3 §3.3) 실행이 끝나지 않았으면
  // 포털 원장에서 읽고, 실행이 도는 동안은 다시 읽는다 — 처음엔 5초마다, 실행 · 단계가 12번 잇달아(약 1분) 그대로면 30초마다(nextRoutinePoll).
  // 바뀌거나 사람이 누르면(이어서 · 고르기 · 멈춤 — reload 로 효과를 다시 세운다) 5초로 돌아온다. 끝나면 그친다.
  // 끝난(done) 실행인데 이 메시지에 보고서 프레임이 없거나(중계의 자리 글 · '이미 끝났다' 안내) RA 초안을 끝에 묻는데 아직 없으면 한 번 읽는다 —
  // 보고서가 있는지 · 그 뒤 올린 RA 초안은 원장에만 있다.
  // 화면에 보일 때만 읽는다(useOnScreen) — 닫힌 독 · 스크롤로 벗어난 메시지 · 숨은 탭에서는 그치고, 다시 보이면 곧 읽고 이어 간다.
  const baseRep = base.report;
  const need =
    allowed &&
    !live &&
    Boolean(runId) &&
    (!base.steps?.length ||
      !isRoutineTerminal(base.state) ||
      (base.state === 'done' && (!baseRep || (raAskable(baseRep) && !hasRaId(baseRep.ra_report_id)))));
  useEffect(() => {
    if (!need || !onScreen) return;
    let alive = true;
    let timer = 0;
    let fails = 0;
    let poll: RoutinePoll | null = null;
    const tick = () => {
      getRun(runId)
        .then((v) => {
          if (!alive) return;
          fails = 0;
          poll = nextRoutinePoll(poll, routineFromRunView(v));
          setView(v);
          setErr('');
          if (isRoutineLive(v.run.state)) timer = window.setTimeout(tick, poll.delay);
        })
        .catch((e: unknown) => {
          if (!alive) return;
          setErr(`실행을 읽지 못했습니다 — ${errText(e)}`);
          // 잠깐 끊긴 것은 다시 읽고, 세 번 잇달아 못 읽으면 그친다(대화를 다시 열면 또 읽는다)
          fails += 1;
          if (fails < 3) timer = window.setTimeout(tick, ROUTINE_POLL_MS);
        });
    };
    tick();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [need, onScreen, runId, reload]);

  const fromView = useMemo(() => (view ? routineFromRunView(view) : null), [view]);
  // 흐르는 동안은 스트림이 정본이고, 흐르지 않으면 포털에서 읽은 것이 더 새것이다. 보고서 알림(경고 · MCP 클라이언트에게 하는 ra_next)은
  // 스트림에만 오고, RA 초안 결과(번호 · 오류)는 원장이 더 새것이다 — 끝에 묻는 루틴을 뒤에 올렸으면 원장에만 있다.
  const rt: RoutineState =
    !live && fromView
      ? {
          ...fromView,
          title: fromView.title || base.title,
          resumed: base.resumed,
          report:
            base.report && fromView.report
              ? { ...base.report, ra_report_id: fromView.report.ra_report_id, ra_error: fromView.report.ra_error }
              : (base.report ?? fromView.report),
        }
      : base;
  // 멈춘 뒤 — 흐르는 메시지는 다음 단계 검사에서야 cancelled 프레임이 온다. 포털은 이미 멈췄으니 곧바로 그렇게 보인다.
  const state = stopped && !isRoutineTerminal(rt.state) ? 'cancelled' : rt.state;
  const runLive = isRoutineLive(state);
  const steps = rt.steps ?? [];
  const cur = steps.find((s) => s.state === 'running');
  const openStep = steps.find((s) => s.id === open);
  const liveLine = live ? cur?.detail || msg.status || '' : '';
  const gate = allowed && state === 'waiting' ? rt.gate : undefined;
  const rep = rt.report;
  const warns = rep?.warnings ?? [];
  const raId = rep?.ra_report_id;
  const hasRa = hasRaId(raId);
  // 이어서 — 실행이 도는 중(또는 끊김)인데 이 메시지가 흐르지 않을 때. 브라우저가 떠나도 실행은 돌지만, 에이전트가 재기동되면 사람이 잇는다(D8).
  const canResume = allowed && !live && (state === 'running' || state === 'interrupted');
  // 멈춤 — 포털이 받는 상태(줄 · 도는 중 · 고를 것)만. 중지(■)는 받기만 끊고 실행은 돈다 — 실행을 그치는 것은 이 단추다.
  const canStop = allowed && (runLive || state === 'waiting');
  // 다른 답을 받는 중 — 이 메시지가 아닌 스트림이 돈다. 멈춤은 이때만 잠근다(이 실행을 받는 중에는 켜 둔다).
  const otherStreaming = streaming && !live;
  // ■ 뒤 — 이 메시지의 받기는 끊겼고(오류 '취소됨') 실행은 아직 돈다. 오류 상자는 '중단되었습니다' 뿐이라 루틴 칸이 뜻을 말한다.
  const stopNote = !live && runLive ? routineStopNote(msg.error) : null;
  // 보고서 보기 — 끝난 실행의 보고서가 원장에 있으면 이 칸 안에 펼쳐 본다. 이 메시지의 글이 보고서든 중계의 자리 글이든 '이미 끝났다'
  // 안내든 같다(글로 가르지 않는다). 받는 중에는 내지 않는다. 보고서 프레임을 받았으면 원장에 저장된 뒤다.
  const showReport = allowed && !live && state === 'done' && Boolean(view?.run.report_ready || base.report);
  // RA 초안 올리기 — 끝에 묻는 루틴(ask) · 저절로 올리기가 실패한 루틴(auto + 오류)의 끝난 실행에 초안이 아직 없을 때(raAskable). 챗 턴으로
  // run_id 와 upload_ra 를 보내면 에이전트가 routine_report_submit(upload=true) 를 부른다(포털은 저장본을, 게이트웨이는 그 사람 명의 초안을 —
  // 이미 있으면 다시 만들지 않는다). 게이트웨이의 ra_next 는 MCP 클라이언트에게 하는 지시라 화면에 내지 않는다.
  const askRa = allowed && !live && state === 'done' && raAskable(rep) && !hasRa;

  const resume = () => {
    setErr('');
    setPickNote('');
    setReload((n) => n + 1); // 사람이 이었다 — 다시 읽기를 처음(5초)부터 다시 센다
    resumeRoutine(runId, rt.title).catch((e: unknown) => setErr(errText(e)));
  };
  const choose = async (step: string, c: { key: string; label: string }) => {
    setBusy(true);
    setErr('');
    setPickNote('');
    try {
      await pickCandidate(runId, step, c.key);
    } catch (e) {
      setErr(`고르지 못했습니다 — ${errText(e)}`);
      setBusy(false);
      refocus.current = true;
      return;
    }
    setBusy(false);
    setReload((n) => n + 1); // 고른 뒤 실행은 다시 running — 원장을 다시 읽어 고를 것을 거둔다
    refocus.current = true;
    const name = c.label || c.key;
    // 고르는 사이 다른 답이 흐르기 시작했다 — 지금 잇지 않는다(챗은 한 번에 한 스트림이다). 원장은 이미 running 이라 다시 읽으면 '이어서' 가
    // 보이고, 받기가 끝난 뒤 그 단추로 잇는다. 그새의 스트림은 ref 로 본다(streamLive — 누른 때의 streaming 은 낡았다)
    if (streamLive()) {
      const note = `${name} 을(를) 골랐습니다 — 다른 답을 받는 중이라 바로 잇지 못했습니다. 받기가 끝나면 '이어서' 를 누릅니다.`;
      setPickNote(note);
      setSaid(note);
      return;
    }
    setSaid(`${name} 을(를) 골랐습니다 — 이어서 돕니다.`);
    resumeRef.current(runId, rt.title).catch((e: unknown) => setErr(errText(e)));
  };
  const halt = async () => {
    if (!window.confirm('이 실행을 멈출까요? 멈춘 실행은 이어서 돌릴 수 없습니다.')) return;
    setBusy(true);
    setErr('');
    try {
      await cancelRun(runId);
      setStopped(true);
      setReload((n) => n + 1);
      setSaid('실행을 멈췄습니다.');
    } catch (e) {
      setErr(`멈추지 못했습니다 — ${errText(e)}`);
    } finally {
      setBusy(false);
      refocus.current = true;
    }
  };
  // 원장의 보고서를 이 칸 안에 펼친다 — 메시지 글은 그대로 둔다. 처음 펼칠 때만 읽고, 다시 누르면 접는다.
  const toggleReport = async () => {
    if (reportOpen) {
      setReportOpen(false);
      return;
    }
    if (report === null) {
      setBusy(true);
      setErr('');
      try {
        setReport((await getRunReport(runId)).report_md || '(보고서 글이 비어 있습니다)');
      } catch (e) {
        setErr(`보고서를 읽지 못했습니다 — ${errText(e)}`);
        return;
      } finally {
        setBusy(false);
      }
    }
    setReportOpen(true);
  };
  // 끝에 묻는 루틴(또는 저절로 올리기가 실패한 루틴)의 RA 초안 — 결과(번호 · 오류)는 새 답에 온다. 이 메시지는 보냈다고만 말한다.
  const uploadRa = () => {
    setErr('');
    setRaSent(true);
    setSaid('Report Archive 초안 올리기를 보냈습니다 — 결과는 아래 새 답에 적힙니다.');
    refocus.current = true;
    resumeRoutine(runId, rt.title, { uploadRa: true }).catch((e: unknown) => {
      setRaSent(false);
      setErr(`올리지 못했습니다 — ${errText(e)}`);
    });
  };

  return (
    // tabIndex -1 — 누른 단추가 사라진 뒤 포커스를 받는 자리(refocus). 탭 차례에는 들지 않는다
    <section className="rv" aria-label="분석 루틴" ref={boxRef} tabIndex={-1}>
      <header className="rv-head">
        <span className="rv-kicker">분석 루틴</span>
        <b className="rv-title" title={rt.title}>
          {rt.title || '(제목 없음)'}
        </b>
        {/* 서버 사본에서 되살렸는데 상태가 없으면('') 포털에서 읽기 전까지 표지를 달지 않는다 */}
        {state && <span className={`rv-badge is-${state}`}>{ROUTINE_RUN_LABEL[state] ?? state}</span>}
        {rt.resumed && (
          <span className="rv-meta" title="끝난 단계는 건너뛰고 이어서 돌았습니다">
            이어 돌림
          </span>
        )}
      </header>
      {rt.reason && state !== 'done' && <p className="rv-reason">{rt.reason}</p>}
      {!live && view?.run.limit_reached && <p className="rv-reason">실행 상한에 닿았습니다 — {view.run.limit_reached}</p>}

      {steps.length > 0 && (
        <ol className="rv-chips" aria-label="단계">
          {steps.map((s) => {
            const st = s.state || 'pending';
            const label = ROUTINE_STEP_LABEL[st] ?? st;
            return (
              <li key={s.id}>
                <button
                  type="button"
                  className={`rv-chip is-${st}${st === 'running' && runLive ? ' is-now' : ''}${open === s.id ? ' is-open' : ''}`}
                  aria-expanded={open === s.id}
                  aria-controls={open === s.id ? `${uid}-step` : undefined}
                  onClick={() => setOpen(open === s.id ? null : s.id)}
                  title={`${s.title} — ${label}${s.calls ? ` · 호출 ${s.calls}번` : ''}${s.reason ? ` · ${s.reason}` : ''}`}
                >
                  <span className="rv-dot" aria-hidden="true" />
                  <span className="rv-chip-text">{s.title || s.id}</span>
                  {s.calls ? <span className="rv-calls">{s.calls}</span> : null}
                </button>
              </li>
            );
          })}
        </ol>
      )}
      {liveLine && (
        <p className="rv-live" role="status">
          {cur && <b>{cur.title}</b>} {liveLine}
        </p>
      )}

      {openStep && (
        <div className="rv-detail" id={`${uid}-step`}>
          <div className="rv-detail-head">
            <b>{openStep.title || openStep.id}</b>
            <span>
              {ROUTINE_STEP_LABEL[openStep.state || 'pending'] ?? openStep.state}
              {openStep.calls ? ` · 호출 ${openStep.calls}번` : ''}
              {openStep.label ? ` · ${openStep.label}` : ''}
            </span>
          </div>
          {openStep.reason && <p className="rv-reason">{openStep.reason}</p>}
          {openStep.summary ? <TextBlock text={openStep.summary} /> : <p className="rv-none">아직 요약이 없습니다.</p>}
          {(openStep.flags?.length ?? 0) > 0 && (
            <ul className="rv-flags" aria-label="표지">
              {(openStep.flags ?? []).map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {gate && (
        <div className="rv-gate" role="group" aria-label="고를 것">
          <p className="rv-gate-msg">{gate.message || '후보가 여럿입니다 — 하나를 고르면 그 키로 이어서 돕니다.'}</p>
          <div className="rv-cands">
            {(gate.candidates ?? []).map((c) => (
              <button
                key={c.key}
                type="button"
                className="rv-cand"
                disabled={busy || streaming}
                title={streaming ? `${STREAMING_TIP.pick} · ${c.key}` : c.key}
                onClick={() => void choose(gate.step, c)}
              >
                {c.label || c.key}
              </button>
            ))}
          </div>
        </div>
      )}

      {showReport && (
        <>
          <button
            type="button"
            className="rv-btn"
            disabled={busy}
            aria-expanded={reportOpen}
            aria-controls={reportOpen ? `${uid}-report` : undefined}
            onClick={() => void toggleReport()}
          >
            {reportOpen ? '보고서 접기' : '보고서 보기'}
          </button>
          {reportOpen && report !== null && (
            <div className="rv-report" id={`${uid}-report`}>
              <TextBlock text={report} />
            </div>
          )}
        </>
      )}
      {(hasRa || rep?.ra_error || askRa || warns.length > 0) && (
        <div className="rv-ra">
          {hasRa && <span className="rv-ra-ok">Report Archive 초안 #{raId}</span>}
          {rep?.ra_error && <span className="rv-ra-err">Report Archive 초안을 만들지 못했습니다 — {rep.ra_error}</span>}
          {askRa &&
            (raSent ? (
              <span className="rv-ra-next">올리기를 보냈습니다 — 결과는 아래 새 답에 적힙니다.</span>
            ) : (
              <>
                <span className="rv-ra-next">
                  {rep?.ra_upload === 'ask'
                    ? '이 루틴은 Report Archive 초안을 끝에 묻습니다 — 올리려면 아래 단추를 누릅니다.'
                    : '저절로 올리기가 실패했습니다 — 토큰을 등록했으면 아래 단추로 다시 올립니다.'}
                </span>
                <button
                  type="button"
                  className="rv-btn"
                  disabled={busy || streaming}
                  onClick={uploadRa}
                  title={streaming ? STREAMING_TIP.upload : '이 실행의 보고서를 내 이름으로 Report Archive 초안에 올립니다'}
                >
                  RA 초안 올리기
                </button>
              </>
            ))}
          {warns.length > 0 && (
            <details className="rv-warn">
              <summary>보고서 경고 {warns.length}건</summary>
              <ul>
                {warns.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
      {err && (
        <p className="rv-err" role="alert">
          {err}
        </p>
      )}
      {stopNote && (
        <p className="rv-reason" role="status">
          {stopNote}
        </p>
      )}
      {/* 낭독기에는 아래 알림 줄(said)로 들린다 — 여기는 보이는 글만(같은 말을 두 번 읽지 않게) */}
      {pickNote && !isRoutineTerminal(state) && <p className="rv-reason">{pickNote}</p>}
      {(canResume || canStop) && (
        <div className="rv-actions">
          {canResume && (
            <button
              type="button"
              className="rv-btn"
              disabled={busy || streaming}
              onClick={resume}
              title={streaming ? STREAMING_TIP.resume : '이 실행을 이어서 돌립니다 — 끝난 단계는 건너뜁니다'}
            >
              이어서
            </button>
          )}
          {canStop && (
            <button
              type="button"
              className="rv-btn is-stop"
              disabled={busy || otherStreaming}
              onClick={() => void halt()}
              title={otherStreaming ? STREAMING_TIP.stop : STOP_TIP}
            >
              멈춤
            </button>
          )}
        </div>
      )}
      <p role="status" style={SR_ONLY}>
        {said}
      </p>
    </section>
  );
}
