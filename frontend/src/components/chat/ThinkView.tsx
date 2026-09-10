// Thinking 라이브 뷰 — 좌석별 예심·자기판정을 보이고, 답한 좌석은 답을, 기권한 좌석은 넘긴 곳을 그린다
import { useMemo, useState } from 'react';
import type { Message, ThinkSeat } from '../../types/chat';
import { TextBlock } from './renderers/TextBlock';

// 좌석 → 고정 색(이름 해시). DelibView 와 같은 계열이라 두 모드의 아바타가 같은 사람으로 읽힌다.
const PALETTE = ['#c0673a', '#3f7d80', '#7a5aa6', '#4a7a3c', '#b08a2a', '#a24a5e', '#3a6ea0', '#6b8e23'];
function colorOf(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}
const initialOf = (name: string) => (name.replace(/[^0-9A-Za-z가-힣]/g, '')[0] ?? '·').toUpperCase();

function Seat({ s }: { s: ThinkSeat }) {
  const label = s.name || s.key;
  return (
    <article className="tv-answer">
      <header className="tv-answer-head">
        <span className="tv-avatar" style={{ background: colorOf(s.key) }} aria-hidden="true">
          {initialOf(label)}
        </span>
        <span className="tv-answer-who">
          <b>{label}</b>
          <code>{s.key}</code>
        </span>
        {s.hop ? <span className="tv-badge tv-badge-hop">위임 {s.hop}홉</span> : null}
      </header>
      {s.scope && <p className="tv-scope">{s.scope}</p>}
      <TextBlock text={s.answer ?? ''} />
      {s.basis && s.basis.length > 0 && (
        <p className="tv-basis">
          근거 — {s.basis.join(' / ')}
        </p>
      )}
    </article>
  );
}

export function ThinkView({ msg }: { msg: Message }) {
  const [openSkipped, setOpenSkipped] = useState(false);
  const d = msg.think ?? {};
  const seats = useMemo(() => d.seats ?? [], [d.seats]);

  // 좌석을 성격별로 가른다. '안 물어봄'(예심은 통과했는데 상한에 걸린 좌석)을 기권과
  // 섞지 않는 것이 핵심이다 — 섞으면 묻지도 않은 전문가가 거절한 것처럼 읽힌다.
  const answered = seats.filter((s) => s.verdict === 'answer' && s.answer);
  const passed = seats.filter((s) => s.verdict === 'pass');
  const errored = seats.filter((s) => s.verdict === 'error');
  const screened = seats.filter((s) => s.screened);
  const unasked = seats.filter((s) => !s.verdict && !s.screened);
  const sum = d.summary;
  const live = Boolean(msg.streaming);

  return (
    <div className="tv">
      <header className="tv-head">
        <span className="tv-title">🧠 Thinking</span>
        <span className="tv-counts">
          {answered.length > 0 && <b className="tv-c-ok">{answered.length}명 답변</b>}
          {passed.length > 0 && <span className="tv-c-pass">{passed.length}명 기권</span>}
          {errored.length > 0 && <span className="tv-c-err">{errored.length}명 응답 실패</span>}
          {live && <span className="tv-c-live">진행 중 · 소집 {seats.length}명</span>}
        </span>
      </header>

      {sum?.no_answer && (
        <p className="tv-none" role="status">
          {errored.length > 0 && passed.length === 0
            ? '전문가를 부르지 못했습니다 — 기권이 아니라 응답 실패입니다. 질문을 바꿔도 해결되지 않습니다.'
            : '답할 수 있다고 판정한 전문가가 없습니다. 이것은 오류가 아니라 판정 결과입니다 — 풀에 이 주제의 전문성이 없거나, 질문을 그 도메인의 용어로 좁혀야 합니다.'}
        </p>
      )}

      {answered.map((s) => (
        <Seat key={s.key} s={s} />
      ))}

      {live && answered.length === 0 && passed.length === 0 && seats.length > 0 && (
        <p className="tv-wait">좌석별로 답할 수 있는지 판정하는 중입니다…</p>
      )}

      {passed.length > 0 && (
        <section className="tv-passed">
          <h4>기권 — 소관이 아니라고 스스로 판정했습니다</h4>
          <ul>
            {passed.map((s) => (
              <li key={s.key}>
                <code>{s.key}</code>
                <span className="tv-pass-why">{s.scope || '소관 아님'}</span>
                {s.refer && s.refer.length > 0 && (
                  <span className="tv-refer">
                    → {s.refer.map((r) => (
                      <span className="tv-refer-chip" key={r}>{r}</span>
                    ))}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {d.handoffs && d.handoffs.length > 0 && (
        <p className="tv-handoff">
          위임 — {d.handoffs.map((h, i) => (
            <span key={i}>
              {h.phrases.join(' · ')} → {h.seats.map((k) => <code key={k}>{k}</code>)}
            </span>
          ))}
        </p>
      )}

      {(unasked.length > 0 || screened.length > 0 || errored.length > 0) && (
        <div className="tv-skipped">
          <button type="button" className="tv-skip-toggle" onClick={() => setOpenSkipped((v) => !v)}>
            {openSkipped ? '▾' : '▸'} 묻지 않은 좌석 {unasked.length + screened.length}명
            {errored.length > 0 && ` · 응답 실패 ${errored.length}명`}
          </button>
          {openSkipped && (
            <ul className="tv-skip-list">
              {unasked.map((s) => (
                <li key={s.key}>
                  <code>{s.key}</code> 답변 상한에 걸려 묻지 않았습니다
                  {typeof s.hits === 'number' && ` (근거 ${s.hits}건)`}
                </li>
              ))}
              {screened.map((s) => (
                <li key={s.key}>
                  <code>{s.key}</code> 예심 탈락 — {s.screenReason}
                </li>
              ))}
              {errored.map((s) => (
                <li key={s.key} className="tv-skip-err">
                  <code>{s.key}</code> 응답 실패(기권 아님)
                  {/* 사유를 반드시 보여 준다 — 없으면 그 좌석이 이유 없이 끊긴 것처럼 읽힌다. */}
                  {s.error && <span className="tv-err-why">{s.error}</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
