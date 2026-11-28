// 확인 카드(10-30 HA-29) — 에이전트 서버가 보내지 않고 멈춘 잡 · 쓰기에 사람이 '실행' · '취소' 로 답하는 단추 · 심의 호출의 요약과 고치기(WD-06)
import { useState } from 'react';
import { useChat } from '../../state/ChatContext';
import type { ConfirmCard as Card, ConfirmDelibSummary } from '../../types/chat';
import { EDIT_ROUNDS, ENGINE_JOBS, editDiff, type ConfirmState, type DelibEdit } from './confirm';

const KIND: Record<string, string> = { job: '잡', write: '쓰기', confirm: '되돌리기 어려움' };

const CLOSED: Record<Exclude<ConfirmState, 'open'>, string> = {
  answered: '이 카드에는 이미 답했습니다',
  closed: '카드 바로 다음 말로만 답할 수 있어 이 카드는 닫혔습니다 — 다시 시키면 새 카드가 섭니다',
  expired: '30분이 지나 이 카드는 닫혔습니다 — 다시 시키면 새 카드가 섭니다',
};
const BUSY = "입력창에 쓰던 글 · 붙인 그림이 있어 단추를 잠갔습니다 — 비우면 누를 수 있습니다('실행' 이라고 답해도 됩니다)";
const JOB_LABEL = Object.fromEntries(ENGINE_JOBS);

/** 호출의 무엇 · 인자 · 예상 작업량은 본문의 카드 글에 이미 있다(서버 사본 · 다른 기기도 같은 글을 본다). 여기는 단추와 상태만 더한다 —
 *  단추는 에이전트 서버가 준 승인 · 거절 글(approve_text · decline_text)을 다음 말로 보낸다. 답할 수 없는 카드는 단추를 잠근다(state — confirm.ts,
 *  서버도 바로 다음 말 하나 · 30분만 받는다 — 지난 카드에 답하면 '찾지 못했다' 로 처리하고 필요하면 새 카드가 선다).
 *  심의 시작 · 이어하기 호출이 있으면 맨 위에 종류 · 라운드 · 좌석 · RA 저장 · 근거 · 앱을 고정해 보이고, 종류 · 라운드 · RA 저장을 바꿔 '실행' 과 함께
 *  보낸다(confirm_edit — 에이전트 서버가 그 카드의 심의 호출에만 얹는다, docs/request-1125 WD-06). */
export function ConfirmCard({ card, state }: { card: Card; state: ConfirmState }) {
  const { sendMessage, streaming, input, attachedImages } = useChat();
  // 쓰던 글 · 붙인 그림이 있으면 누르지 않게 한다 — 보내기가 입력창을 비워 그 글이 사라지고 그림은 이 승인 말에 실린다(ChatActionBar 와 같은 까닭).
  // 붙인 문서는 보지 않는다 — 떼기 전까지 모든 말에 실려 다니는 칸이다(ChatContext attachedDocs).
  const busy = input.trim() !== '' || attachedImages.length > 0;
  const off = state !== 'open' || streaming || busy;
  const why = state === 'open' && busy ? BUSY : '';
  const kinds = [...new Set(card.calls.map((c) => KIND[c.kind] ?? c.kind))];
  // 고칠 수 있는 칸은 카드의 첫 심의 호출이 보인 값에서 시작한다 — 에이전트 서버는 같은 고침을 그 카드의 심의 호출 모두에 얹는다
  const first = card.calls.find((c) => c.summary)?.summary;
  const [edit, setEdit] = useState<DelibEdit | null>(() =>
    first ? { save_report: first.save_report, job: first.job, rounds: first.rounds } : null);
  const set = first && edit ? editDiff(first, edit) : {};
  const changed = Object.keys(set).length > 0;
  const approve = () =>
    // 셋째 인자 null — 켜 둔 분석 루틴을 싣지도 쓰지도 않는다. 실리면 에이전트 서버가 카드를 판정하기 전에 루틴 가지로 보내, '취소' 를 눌러도 루틴이
    // 새로 돈다(ChatContext sendMessage 의 약속 — ChatActionBar 의 한 번 누름 보내기와 같다).
    sendMessage(card.approve_text, undefined, null, changed ? { confirmEdit: { id: card.id, set } } : undefined);
  return (
    <>
      {card.calls.map((c, i) =>
        c.summary ? (
          <DelibSummary key={`${c.tool}-${i}`} sm={c.summary} edit={c.summary === first ? edit : null} onEdit={setEdit} locked={off} />
        ) : null,
      )}
      <div className="msg-confirm" role="group" aria-label="확인이 필요한 작업">
        <button type="button" className="btn-primary" disabled={off} title={why} onClick={approve}>
          {changed ? '바꾼 대로 실행' : '실행'}
        </button>
        <button type="button" className="btn-secondary" disabled={off} title={why} onClick={() => sendMessage(card.decline_text, undefined, null)}>
          취소
        </button>
        <span className="msg-confirm-note">
          {state !== 'open' ? CLOSED[state] : busy ? BUSY : `${card.calls.length}건 · ${kinds.join(' · ')} · 확인 번호 ${card.id} · 30분`}
        </span>
      </div>
    </>
  );
}

/** 심의 호출 하나의 요약 — 인자에서 센 값(에이전트 서버 _confirm_delib_summary). edit 가 있으면 종류 · 라운드 · RA 저장을 고칠 수 있다. */
function DelibSummary({ sm, edit, onEdit, locked }: {
  sm: ConfirmDelibSummary; edit: DelibEdit | null; onEdit: (e: DelibEdit) => void; locked: boolean;
}) {
  const can = (k: string) => Boolean(edit) && sm.editable.includes(k) && !locked;
  const cont = sm.call === 'deliberate_continue';
  const jobs = ENGINE_JOBS.some(([k]) => k === sm.job) ? ENGINE_JOBS : [[sm.job, sm.job] as const, ...ENGINE_JOBS];
  return (
    <div className="msg-confirm-sum" role="group" aria-label="심의 요약">
      <div className="mcs-row">
        <b>{cont ? '심의 이어하기' : '심의 시작'}</b>
        <label>
          종류{' '}
          {cont ? (
            <span title="이어하기는 앞 잡의 종류를 잇는다">앞 잡에서 잇는다</span>
          ) : (
            <select aria-label="심의 종류" value={edit?.job ?? sm.job} disabled={!can('job')}
              onChange={(e) => edit && onEdit({ ...edit, job: e.target.value })}>
              {jobs.map(([k, label]) => (
                <option key={k} value={k}>{label} ({k})</option>
              ))}
            </select>
          )}
        </label>
        <label>
          라운드{' '}
          <select aria-label="라운드" value={edit?.rounds ?? sm.rounds} disabled={!can('rounds')}
            onChange={(e) => edit && onEdit({ ...edit, rounds: Number(e.target.value) })}>
            {[...new Set([sm.rounds, ...EDIT_ROUNDS])].map((n) => (
              <option key={n} value={n}>{n === 0 ? '기본(3)' : n}</option>
            ))}
          </select>
        </label>
        <label>
          <input type="checkbox" aria-label="RA 저장" checked={edit?.save_report ?? sm.save_report} disabled={!can('save_report')}
            onChange={(e) => edit && onEdit({ ...edit, save_report: e.target.checked })} /> RA 저장
        </label>
      </div>
      <div className="mcs-row mcs-facts">
        <span>근거 {sm.evidence_n}건 · {sm.evidence_chars.toLocaleString()}자</span>
        {sm.apps.length > 0 && <span>앱 {sm.apps.join(', ')}</span>}
        {sm.modifiers?.length ? <span>층 {sm.modifiers.join(', ')}</span> : null}
        {sm.previous_job_id && <span>이을 잡 <code>{sm.previous_job_id}</code></span>}
        {!cont && <span>{JOB_LABEL[edit?.job ?? sm.job] ?? (edit?.job ?? sm.job)}</span>}
      </div>
      {sm.seats_n > 0 ? (
        <details className="mcs-seats">
          <summary>좌석 {sm.seats_n}석</summary>
          <span>{sm.seats.join(', ')}{sm.seats_n > sm.seats.length ? ` 외 ${sm.seats_n - sm.seats.length}석` : ''}</span>
        </details>
      ) : (
        <div className="mcs-row mcs-facts"><span>좌석은 서버가 고릅니다</span></div>
      )}
    </div>
  );
}
