// 심의 라이브 뷰 — 절차 스테퍼 + 근거 카드 + 라이브 회의 버블 + 수렴/소수의견 배지 + 산출물 카드
import { useMemo, useState } from 'react';
import { useChat } from '../../state/ChatContext';
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

// 라운드 수는 가변(2~8) — 절차는 환기·발굴 + r1..rN + 의결·보고로 동적 구성한다.
const roundNoOf = (stage?: string): number => {
  const m = stage?.match(/^r(\d+)$/);
  return m ? Number(m[1]) : 0;
};
// 라운드 성격 라벨(1=초기, 마지막=수렴, 중간=심화).
const roundLabel = (r: number, total: number): string =>
  r === 1 ? '도메인별 초기 입장' : r >= total ? '수렴·최종 입장' : '상호 반박·심화';

function stageList(total: number, seen: string[]): { id: string; label: string }[] {
  const rounds = Array.from({ length: total }, (_, i) => ({ id: `r${i + 1}`, label: `${i + 1}라운드` }));
  return [
    { id: 'recall', label: '환기' },
    { id: 'discover', label: '발굴' },
    ...rounds,
    { id: 'decide', label: '의결' },
    { id: 'report', label: '보고' },
  ].filter((s) => s.id !== 'recall' || seen.includes('recall'));
}

function Stepper({ d, live }: { d: DelibData; live: boolean }) {
  const seen = d.stages ?? [];
  const cur = d.stage;
  const list = stageList(d.totalRounds ?? 3, seen);
  const curIdx = list.findIndex((s) => s.id === cur);
  // 현재 라운드 발언 진행률(분자=이 라운드 turn 수, 분모=패널 수)
  const roundNo = roundNoOf(cur);
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

// 참여 전문가 소개 — 심의 시작 시 누가 참여하는지·각자 뭐 하는 사람인지. 아바타 색/이니셜은
// 아래 라운드 버블과 동일해 '이 사람이 이 발언'을 눈으로 잇게 한다(진행 순서 파악에 도움).
function PersonaIntro({ d }: { d: DelibData }) {
  const personas = d.personas ?? [];
  if (!personas.length) return null;
  return (
    <section className="dv-intro" aria-label="참여 전문가">
      <div className="dv-intro-head">참여 전문가 {personas.length}인 · 각자 초기입장 → 상호 반박 → 수렴 순으로 발언합니다</div>
      <ul className="dv-intro-list">
        {personas.map((p) => (
          <li key={p.key} className="dv-intro-item">
            <span className="dv-intro-avatar" style={{ background: colorOf(p.key) }} aria-hidden="true">
              {initialOf(p.key)}
            </span>
            <div className="dv-intro-body">
              <span className="dv-intro-key">{p.key}</span>
              {p.role && <span className="dv-intro-role">{p.role}</span>}
            </div>
          </li>
        ))}
      </ul>
    </section>
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
  const roundNo = roundNoOf(d.stage);
  const total = d.roundN ?? d.personas?.length ?? 0;
  const totalRounds = d.totalRounds ?? 3;
  // 렌더할 라운드 = 1..총라운드 ∪ turn 에 실제로 등장한 라운드(가변·과거 저장분 방어).
  const maxRound = Math.max(totalRounds, roundNo, ...Object.keys(rounds).map(Number), 0);
  const roundNums = Array.from({ length: maxRound }, (_, i) => i + 1);
  return (
    <div className="dv-meeting" role="log" aria-live="polite" aria-label="전문가 회의 발언">
      {roundNums
        .filter((r) => rounds[r]?.length || (live && r === roundNo))
        .map((r) => (
          <section key={r} className="dv-round">
            <div className="dv-round-div">
              <span>{`${r}라운드 · ${roundLabel(r, totalRounds)}`}</span>
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
// 이어하기(사람 개입 스티어링) — 끝난 심의에 의견을 넣어 같은 전문가로 후속 심의를 유도한다.
function ContinueBar({ d }: { d: DelibData }) {
  const { continueDeliberation, streaming } = useChat();
  const [note, setNote] = useState('');
  if (!d.decision) return null;
  const submit = () => {
    const n = note.trim();
    if (!n || streaming) return;
    continueDeliberation(d, n);
    setNote('');
  };
  return (
    <section className="dv-continue">
      <div className="dv-continue-head">💬 의견을 넣어 이어가기 — 같은 전문가들이 이 방향으로 다시 토론합니다</div>
      <div className="dv-continue-row">
        <textarea
          className="dv-continue-input"
          placeholder="예: 낙하 성능을 최우선으로 좁혀라 / A안은 비용 근거로 기각 / dwell 24h 이상만 검토"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          disabled={streaming}
        />
        <button
          type="button"
          className="dv-continue-btn"
          onClick={submit}
          disabled={!note.trim() || streaming}
        >
          이어가기
        </button>
      </div>
    </section>
  );
}

export function DelibView({ msg }: { msg: Message }) {
  const d = msg.delib!;
  const live = Boolean(msg.streaming);
  const decision = useMemo(() => d.decision ?? '', [d.decision]);
  return (
    <div className="dv-root">
      <Stepper d={d} live={live} />
      <PersonaIntro d={d} />
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
      {!live && <ContinueBar d={d} />}
    </div>
  );
}
