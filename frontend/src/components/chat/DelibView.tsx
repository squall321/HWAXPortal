// 심의 라이브 뷰 — 절차 스테퍼 + 근거 카드 + 라이브 회의 버블 + 수렴/소수의견 배지 + 산출물 카드
import { useMemo } from 'react';
import type { DelibData, DelibTurn, Message } from '../../types/chat';
import { TextBlock } from './renderers/TextBlock';

// 페르소나 → 고정 색(이름 해시) — 회의 chat 렌더와 같은 계열의 팔레트.
const PALETTE = ['#c0673a', '#3f7d80', '#7a5aa6', '#4a7a3c', '#b08a2a', '#a24a5e', '#3a6ea0', '#6b8e23'];
function colorOf(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}
const initialOf = (name: string) => (name.replace(/[^0-9A-Za-z가-힣]/g, '')[0] ?? '·').toUpperCase();

// 절차 정의 — recall 은 불량 화두에서만 등장(없으면 스테퍼에서 생략).
const STAGES: { id: string; label: string }[] = [
  { id: 'recall', label: '환기' },
  { id: 'discover', label: '발굴' },
  { id: 'r1', label: '1라운드' },
  { id: 'r2', label: '2라운드' },
  { id: 'r3', label: '3라운드' },
  { id: 'decide', label: '의결' },
  { id: 'report', label: '보고' },
];

function Stepper({ d, live }: { d: DelibData; live: boolean }) {
  const seen = d.stages ?? [];
  const cur = d.stage;
  const list = STAGES.filter((s) => s.id !== 'recall' || seen.includes('recall'));
  const curIdx = list.findIndex((s) => s.id === cur);
  // 현재 라운드 발언 진행률(분자=이 라운드 turn 수, 분모=패널 수)
  const roundNo = cur === 'r1' ? 1 : cur === 'r2' ? 2 : cur === 'r3' ? 3 : 0;
  const spoken = roundNo ? (d.turns ?? []).filter((t) => t.round === roundNo).length : 0;
  const total = d.roundN ?? d.personas?.length ?? 0;
  return (
    <div className="dv-stepper" role="list" aria-label="심의 절차">
      {list.map((s, i) => {
        // 종료 후: outcome 있으면 전부 done, 없으면(에러/중단) 멈춘 지점을 펄스 없는 halt 로 동결.
        const state = !live
          ? d.outcome
            ? 'done'
            : i < curIdx
              ? 'done'
              : i === curIdx
                ? 'halt'
                : 'todo'
          : i < curIdx
            ? 'done'
            : i === curIdx
              ? 'now'
              : 'todo';
        return (
          <div
            key={s.id}
            className={`dv-step ${state}`}
            role="listitem"
            aria-current={state === 'now' ? 'step' : undefined}
          >
            <span className="dv-step-dot" aria-hidden="true">
              {state === 'done' ? '✓' : state === 'halt' ? '⏸' : ''}
            </span>
            <span className="dv-step-label">
              {s.label}
              {state === 'now' && roundNo > 0 && total > 0 && (
                <em className="dv-step-sub">
                  {spoken}/{total} 발언
                </em>
              )}
            </span>
            {i < list.length - 1 && <span className="dv-step-bar" aria-hidden="true" />}
          </div>
        );
      })}
    </div>
  );
}

function EvidenceCard({ d }: { d: DelibData }) {
  // 과거 저장분(단일 객체) 호환 — 배열로 정규화 후 출처별 카드.
  const list = Array.isArray(d.evidence) ? d.evidence : d.evidence ? [d.evidence] : [];
  if (!list.length) return null;
  return (
    <>
      {list.map((ev, i) => (
        <details className="dv-evidence" key={`${ev.source}-${i}`}>
          <summary>
            <span className="dv-ev-badge">근거</span>
            {ev.source}
            <span className={`dv-ev-flag${ev.included ? ' in' : ''}`}>
              {ev.included ? '심의에 포함' : '직접 연관 없음'}
            </span>
          </summary>
          <pre className="dv-ev-body">{ev.text}</pre>
        </details>
      ))}
    </>
  );
}

const ROUND_LABEL: Record<number, string> = {
  1: '1라운드 · 도메인별 초기 입장',
  2: '2라운드 · 상호 반박·심화',
  3: '3라운드 · 수렴·최종 입장',
};

function stanceClass(s?: string): string {
  if (!s) return '';
  if (s.includes('반대')) return 'oppose';
  if (s.includes('조건')) return 'cond';
  return 'agree';
}

function Meeting({ d, live }: { d: DelibData; live: boolean }) {
  const turns = d.turns ?? [];
  if (turns.length === 0 && !live) return null;
  const rounds: Record<number, DelibTurn[]> = {};
  for (const t of turns) (rounds[t.round] ??= []).push(t);
  const roundNo = d.stage === 'r1' ? 1 : d.stage === 'r2' ? 2 : d.stage === 'r3' ? 3 : 0;
  const total = d.roundN ?? d.personas?.length ?? 0;
  return (
    <div className="dv-meeting" role="log" aria-live="polite" aria-label="전문가 회의 발언">
      {[1, 2, 3]
        .filter((r) => rounds[r]?.length || (live && r === roundNo))
        .map((r) => (
          <section key={r} className="dv-round">
            <div className="dv-round-div">
              <span>{ROUND_LABEL[r]}</span>
            </div>
            {(rounds[r] ?? []).map((t, i) => (
              <div key={`${r}-${t.persona}-${i}`} className="dv-turn">
                <span className="dv-av" style={{ background: colorOf(t.persona) }}>
                  {initialOf(t.persona)}
                </span>
                <div className="dv-turn-body">
                  <div className="dv-who">
                    {t.persona}
                    {t.stance && <span className={`dv-stance ${stanceClass(t.stance)}`}>{t.stance}</span>}
                  </div>
                  <div className="dv-bub" style={{ borderLeftColor: colorOf(t.persona) }}>
                    {/* 블록 렌더 — 발언의 문단 구분(수용/반박/심화)·목록·인라인 서식이 그대로 보인다 */}
                    <TextBlock text={t.say} />
                  </div>
                </div>
              </div>
            ))}
            {live && r === roundNo && (rounds[r]?.length ?? 0) < total && (
              <div className="dv-typing">
                <span className="typing-dots" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </span>
                남은 전문가 {total - (rounds[r]?.length ?? 0)}명 발언 작성 중…
              </div>
            )}
          </section>
        ))}
    </div>
  );
}

function Convergence({ d }: { d: DelibData }) {
  const r1 = (d.turns ?? []).filter((t) => t.round === 1 && t.position);
  const r3 = (d.turns ?? []).filter((t) => t.round === 3 && t.position);
  if (r3.length === 0) return null;
  const tally = d.outcome?.tally;
  return (
    <section className="dv-conv">
      <div className="dv-conv-head">
        입장 수렴
        {tally && (
          <span className={`dv-verdict${d.outcome?.unanimous ? ' unanimous' : ''}`}>
            {d.outcome?.unanimous
              ? `만장일치 ${tally.agree}/${tally.total}`
              : `동의 ${tally.agree} · 조건부 ${tally.conditional} · 반대 ${tally.oppose}`}
          </span>
        )}
        {tally && !d.outcome?.unanimous && (tally.conditional > 0 || tally.oppose > 0) && (
          <span className="dv-minority">소수의견 있음 — 의사결정문 (3)절 참조</span>
        )}
      </div>
      <div className="dv-conv-grid">
        {r3.map((t) => {
          const first = r1.find((x) => x.persona === t.persona);
          return (
            <div key={t.persona} className="dv-conv-row">
              <span className="dv-av sm" style={{ background: colorOf(t.persona) }}>
                {initialOf(t.persona)}
              </span>
              <span className="dv-conv-pos from" title={first?.position}>
                {first?.position ?? '—'}
              </span>
              <span className="dv-conv-arrow" aria-hidden="true">
                →
              </span>
              <span className={`dv-conv-pos to ${stanceClass(t.stance)}`} title={t.position}>
                {t.position}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function OutcomeCards({ d }: { d: DelibData }) {
  const o = d.outcome;
  if (!o) return null;
  return (
    <div className="dv-outcome">
      {o.report_id != null && (
        <a
          className="dv-card report"
          href={`/report-archive/w/dev/reports/${o.report_id}`}
          target="_blank"
          rel="noreferrer"
        >
          <span className="dv-card-k">📄 Report Archive</span>
          <span className="dv-card-t">{o.title || '심의 보고서'}</span>
          <span className="dv-card-s">보고서 #{o.report_id} — 열어보기 ↗</span>
        </a>
      )}
      {o.tally && (
        <div className={`dv-card verdict${o.unanimous ? ' unanimous' : ''}`}>
          <span className="dv-card-k">{o.unanimous ? '🤝 만장일치' : '⚖ 다수결'}</span>
          <span className="dv-card-t">
            동의 {o.tally.agree} · 조건부 {o.tally.conditional} · 반대 {o.tally.oppose}
          </span>
          <span className="dv-card-s">패널 {o.tally.total}명 · 3라운드 수렴</span>
        </div>
      )}
    </div>
  );
}

/** 심의 메시지의 본문 렌더 — msg.delib 이 있으면 MessageList 가 TextBlock 대신 이걸 쓴다. */
export function DelibView({ msg }: { msg: Message }) {
  const d = msg.delib!;
  const live = Boolean(msg.streaming);
  const decision = useMemo(() => d.decision ?? '', [d.decision]);
  return (
    <div className="dv-root">
      <Stepper d={d} live={live} />
      <EvidenceCard d={d} />
      <Meeting d={d} live={live} />
      <Convergence d={d} />
      {decision && (
        <section className="dv-decision">
          <div className="dv-round-div chair">
            <span>의장 · 의사결정문</span>
          </div>
          <TextBlock text={decision} />
        </section>
      )}
      <OutcomeCards d={d} />
    </div>
  );
}
