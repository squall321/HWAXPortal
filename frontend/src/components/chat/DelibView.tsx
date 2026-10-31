// 심의 라이브 뷰 — 절차 스테퍼 + 멈춤 + 근거 카드 + 라이브 회의 버블 + 수렴/소수의견 배지 + 산출물 카드
import { useMemo, useState } from 'react';
import { cancelDeliberation, type DelibCancelResult } from '../../api/chat.api';
import { delibMayStillRun } from '../../lib/chatErrors';
import { useChat } from '../../state/ChatContext';
import { decisionAsOf } from '../../state/chatStore';
import { useCan } from '../../auth/useCan';
import type { DelibData, DelibTurn, Message } from '../../types/chat';
import { DelibGraph } from './DelibGraph';
import { RosterEditor, type Seat } from './RosterEditor';
import { colorOf, initialOf } from './personaColor';
import { InlineMd, TextBlock } from './renderers/TextBlock';
import { usePersonaName } from './usePersonaPool';
import { IconChat, IconOrg } from './icons';

// 색·이니셜은 공용 모듈에서 온다 — 챗 페르소나 말풍선이 같은 함수에 같은 입력(키)을 넣어야
// 같은 전문가가 심의와 챗에서 같은 색으로 보인다.

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
    { id: 'explain', label: '쉬운 설명' },
    { id: 'report', label: '보고' },
  ].filter((s) => s.id !== 'recall' || seen.includes('recall'));
}

function Stepper({ d, live }: { d: DelibData; live: boolean }) {
  const seen = d.stages ?? [];
  const cur = d.stage;
  // 서버 저장본에서 되살린 심의는 stage·outcome 이 없다(conversations.api) — 결정문이 있으면 끝난 심의다.
  // 종전엔 현재 단계를 못 찾아(-1) 끝난 심의의 모든 단계가 '할 일' 빈 점으로 보였다(docs/ui-refresh 단계 4).
  // 그때는 일어났다고 알 수 있는 단계만 남겨 전부 완료로 — 쉬운 설명은 본문이 있을 때, 보고는 보고서 번호가 있을 때.
  const restored = !live && !cur && Boolean(d.decision);
  const list = stageList(d.totalRounds ?? 3, seen).filter(
    (s) => !restored || ((s.id !== 'explain' || Boolean(d.plain)) && (s.id !== 'report' || d.outcome?.report_id != null)),
  );
  const curIdx = restored ? list.length : list.findIndex((s) => s.id === cur);
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
// 좌석 성격 라벨 — 왜 이 사람이 앉았는지가 보여야 결정문의 커버리지 기록과 이어진다.
// counter 는 "주 도메인이 못 보는 축"을 맡으라고 일부러 앉힌 좌석이라 특히 눈에 띄어야 한다.
const ORIGIN_LABEL: Record<string, { text: string; cls: string }> = {
  counter: { text: '반대 도메인', cls: 'dv-seat-counter' },
  adversary: { text: '지정 반대석', cls: 'dv-seat-counter' },
  new: { text: '이번 회차 합류', cls: 'dv-seat-new' },
  carry: { text: '유임', cls: 'dv-seat-carry' },
};

function PersonaIntro({ d }: { d: DelibData }) {
  const nameOf = usePersonaName();
  const personas = d.personas ?? [];
  if (!personas.length) return null;
  const domains = new Set(personas.map((p) => (p.key.includes('-') ? p.key.split('-')[0] : p.key)));
  return (
    <section className="dv-intro" aria-label="참여 전문가">
      <div className="dv-intro-head">
        참여 전문가 {personas.length}인 · 도메인 {domains.size}종 · 각자 초기입장 → 상호 반박 → 수렴 순으로 발언합니다
      </div>
      <ul className="dv-intro-list">
        {personas.map((p) => (
          <li key={p.key} className="dv-intro-item">
            <span className="dv-intro-avatar" style={{ background: colorOf(p.key) }} aria-hidden="true">
              {initialOf(nameOf(p.key))}
            </span>
            <div className="dv-intro-body">
              <span className="dv-intro-key" title={p.key}>
                {nameOf(p.key)}
                {p.origin && ORIGIN_LABEL[p.origin] && (
                  <span className={`dv-seat ${ORIGIN_LABEL[p.origin].cls}`}>{ORIGIN_LABEL[p.origin].text}</span>
                )}
              </span>
              {p.role && <span className="dv-intro-role"><InlineMd text={p.role} /></span>}
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
            {/* included=false 는 '무관해서 뺀 자료' 만이 아니다 — 엔진이 버린 것을 알리는 카드(사전 근거 예산 초과·
                본문 없음·지식카드 조회 강등 …)도 같은 깃발로 온다. 딱지는 깃발의 뜻만 말하고 사유는 제목·본문에 둔다.
                notice 는 그중에서도 좌석에 안 준 것이 **아닌** 알림이다(의장 전사 상한 초과 — 줄인 것은 의장의 입력이고
                좌석은 전부 받았다 · 좌석 유실 · 앱 범위 제한 불가). '좌석에 주지 않음' 이라고 부르면 거꾸로 말한다. */}
            <span className={`dv-ev-flag${ev.included ? ' in' : ''}`}>
              {ev.included ? '심의에 포함' : ev.notice ? '알림' : '좌석에 주지 않음'}
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
  // ⚠ '미표명' 이 else 로 떨어지면 초록(동의)이 된다 — 말하지 않은 것을 동의로 칠하는 셈이다.
  if (s.includes('미표명')) return 'abstain';
  return 'agree';
}

function Meeting({ d, live }: { d: DelibData; live: boolean }) {
  const nameOf = usePersonaName();
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
              <span>{`${rounds[r]?.[0]?.displayRound ?? r}라운드 · ${roundLabel(r, totalRounds)}`}</span>
            </div>
            {(rounds[r] ?? []).map((t, i) => (
              <div key={`${r}-${t.persona}-${i}`} className="dv-turn">
                <span className="dv-av" style={{ background: colorOf(t.persona) }} aria-hidden="true">
                  {initialOf(nameOf(t.persona))}
                </span>
                <div className="dv-turn-body">
                  {/* 화자는 사람 이름으로 — 기계 키(pcb-warpage)는 툴팁에(docs/ui-refresh 단계 4) */}
                  <div className="dv-who" title={t.persona}>
                    {nameOf(t.persona)}
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
  const nameOf = usePersonaName();
  const r1 = (d.turns ?? []).filter((t) => t.round === 1 && t.position);
  // 마지막(수렴) 라운드 = totalRounds. 종전 3 고정이라 rounds=4 면 심화 라운드를 수렴으로 읽었다.
  const r3 = (d.turns ?? []).filter((t) => t.round === (d.totalRounds ?? 3) && t.position);
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
              : `동의 ${tally.agree} · 조건부 ${tally.conditional} · 반대 ${tally.oppose}` +
                (tally.abstain ? ` · 미표명 ${tally.abstain}` : '')}
          </span>
        )}
        {tally && !d.outcome?.unanimous &&
          (tally.conditional > 0 || tally.oppose > 0 || (tally.abstain ?? 0) > 0) && (
          <span className="dv-minority">
            {(tally.abstain ?? 0) > 0
              ? `미표명 ${tally.abstain}석 — 그 도메인 판단은 빠져 있습니다`
              : '소수의견 있음 — 의사결정문 (3)절 참조'}
          </span>
        )}
      </div>
      <div className="dv-conv-grid">
        {r3.map((t) => {
          const first = r1.find((x) => x.persona === t.persona);
          return (
            <div key={t.persona} className="dv-conv-row">
              <span className="dv-av sm" style={{ background: colorOf(t.persona) }} title={nameOf(t.persona)}>
                {initialOf(nameOf(t.persona))}
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
          <span className="dv-card-k">Report Archive</span>
          <span className="dv-card-t">{o.title || '심의 보고서'}</span>
          <span className="dv-card-s">보고서 #{o.report_id} — 열어보기 ↗</span>
        </a>
      )}
      {o.tally && (
        <div className={`dv-card verdict${o.unanimous ? ' unanimous' : ''}`}>
          <span className="dv-card-k">{o.unanimous ? '만장일치' : '다수결'}</span>
          <span className="dv-card-t">
            동의 {o.tally.agree} · 조건부 {o.tally.conditional} · 반대 {o.tally.oppose}
            {o.tally.abstain ? ` · 미표명 ${o.tally.abstain}` : ''}
          </span>
          <span className="dv-card-s">
            패널 {o.tally.total}명
            {o.tally.responded !== undefined && o.tally.responded < o.tally.total
              ? ` (최종 라운드 응답 ${o.tally.responded}명)`
              : ''}
            {' · 수렴'}
          </span>
        </div>
      )}
    </div>
  );
}

/** 심의 메시지의 본문 렌더 — msg.delib 이 있으면 MessageList 가 TextBlock 대신 이걸 쓴다. */
// 이어하기(사람 개입 스티어링) — 끝난 심의에 의견을 넣어 같은 전문가로 후속 심의를 유도한다.
function ContinueBar({ d }: { d: DelibData }) {
  const { continueDeliberation, streaming, delibOpts } = useChat();
  const [note, setNote] = useState('');
  // 좌석 조정 — 한 회차를 돌고 명단을 사람이 고른다(요청 3번 '토론이 잘 안 되면 한 번 돌고 로스터 선택').
  // 현재 좌석은 personas 정본, 복원된 심의(personas 없음)는 발언자로 채운다.
  const current = useMemo<Seat[]>(
    () =>
      d.personas?.length
        ? d.personas.map((p) => ({ key: p.key, role: p.role ?? '' }))
        : [...new Set((d.turns ?? []).map((t) => t.persona).filter(Boolean))].map((key) => ({ key, role: '' })),
    [d.personas, d.turns],
  );
  const [editing, setEditing] = useState(false);
  const [roster, setRoster] = useState<Seat[] | null>(null);
  const seats = roster ?? current;
  const edited =
    roster !== null &&
    (roster.length !== current.length || roster.some((s) => !current.some((c) => c.key === s.key)));
  if (!d.decision) return null;
  const tooFew = edited && seats.length < 2;
  // 기준일 — 이어하기는 앞 회차의 값으로 돈다(ChatContext continueDeliberation). 심의 옵션의 값과 다르면 어느 쪽인지 여기서 밝힌다(HA-11).
  const priorAsOf = decisionAsOf(d.decision);
  const panelAsOf = delibOpts.as_of || undefined;
  const asOfNote = priorAsOf
    ? `기준일 ${priorAsOf}(앞 회차)로 잇는다${panelAsOf && panelAsOf !== priorAsOf ? ` — 심의 옵션의 기준일 ${panelAsOf} 는 이 이어하기에 쓰지 않는다` : ''}`
    : panelAsOf
      ? `앞 회차가 기준일 없이 돌아 이어하기도 기준일 없이 돈다 — 심의 옵션의 기준일 ${panelAsOf} 는 쓰지 않는다(그 날로 보려면 새 심의를 연다)`
      : '';
  const submit = () => {
    if (streaming || tooFew) return;
    const n = note.trim();
    // 명단만 바꿔 이어갈 수도 있다 — 그때는 무엇을 바꿨는지를 의견으로 대신 싣는다(좌석들이 누가
    // 들어오고 나갔는지 알아야 새 구성으로 쟁점을 다시 다룬다).
    const plus = seats.filter((s) => !current.some((c) => c.key === s.key)).map((s) => s.key);
    const minus = current.filter((c) => !seats.some((s) => s.key === c.key)).map((c) => c.key);
    const change = edited
      ? `좌석 조정 —${plus.length ? ` 합류 ${plus.join(', ')}` : ''}${minus.length ? ` · 제외 ${minus.join(', ')}` : ''}. 새 구성으로 남은 쟁점을 다시 다뤄라.`
      : '';
    const opinion = [n, change].filter(Boolean).join('\n');
    if (!opinion) return;
    continueDeliberation(d, opinion, edited ? seats : undefined);
    setNote('');
    setRoster(null);
    setEditing(false);
  };
  return (
    <section className="dv-continue">
      <div className="dv-continue-head">
        <IconChat className="ico" width={14} height={14} /> 의견을 넣어 이어가기 — {edited ? `고른 ${seats.length}석으로` : '같은 전문가들이'} 이 방향으로 다시 토론합니다
        <button type="button" className="dv-roster-btn" onClick={() => setEditing((v) => !v)} disabled={streaming}>
          {editing ? '좌석 조정 닫기' : <><IconOrg className="ico" width={14} height={14} /> 좌석 조정 ({seats.length}석)</>}
        </button>
      </div>
      {editing && <RosterEditor current={current} roster={seats} onChange={setRoster} />}
      {asOfNote && <div className="dv-continue-asof">{asOfNote}</div>}
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
          disabled={(!note.trim() && !edited) || streaming || tooFew}
        >
          이어가기
        </button>
      </div>
    </section>
  );
}

// 멈춤 결과를 사람의 말로 — 포털 · 에이전트 서버의 code 로 가른다. 모르는 거절은 서버가 준 글을 그대로 붙인다.
function stopSaid(r: DelibCancelResult, cut: boolean): string {
  if (r.ok) return r.already ? '이미 멈춘 심의입니다.' : '멈춤을 요청했습니다 — 서버가 심의를 접고 있습니다(지금까지 받은 발언은 남습니다).';
  if (r.code === 'finishing')
    return (
      '의장이 결정문을 이미 냈습니다 — 쉬운 설명 · 보고서 저장으로 마무리하는 중이라 멈추지 않습니다' +
      (cut ? '. 받기가 끊긴 화면에는 오지 않으니 결과는 Report Archive 에서 찾으세요.' : '(곧 이 칸에 결정문이 옵니다).')
    );
  if (r.code === 'already_finished') return '이미 끝난 심의입니다 — 멈출 것이 없습니다.';
  if (r.code === 'delib_not_found') return '서버에서 도는 이 심의를 찾지 못했습니다 — 이미 끝났거나 서버가 다시 떴습니다.';
  return `멈추지 못했습니다 — ${r.message || r.code}`;
}

// 확인 창 — 멈춘 단의 결정문 · 보고서는 없지만, 다단 심의의 앞 단 · 이어하기의 앞 회차가 낸 결정문과 Report Archive 초안은 그대로다(단정하지
// 않는다). 받기가 끊긴 심의는 끊긴 뒤 서버에서 나온 발언이 어디에도 남지 않았다 — 받는 중인 심의와 말이 다르다.
const STOP_KEEPS = '앞 단 · 앞 회차에서 이미 낸 결정문과 Report Archive 에 저장된 초안은 그대로 있습니다.';
const STOP_CONFIRM_LIVE = `이 심의를 서버에서 멈출까요? 지금까지 받은 발언은 남고, 이 단의 결정문 · 보고서는 만들지 않습니다. ${STOP_KEEPS}`;
const STOP_CONFIRM_CUT =
  `이 심의를 서버에서 멈출까요? 받기가 끊긴 뒤 서버에서 나온 발언은 남지 않고, 이 단의 결정문 · 보고서는 만들지 않습니다. ${STOP_KEEPS}`;
// 포털이 서버 대화에 남긴 글(stop_note)이 없을 때 — 받는 중계가 남기기로 했거나(드물다) 옛 포털이다.
const STOP_NOTE_CUT = '사람이 멈췄다(받기가 끊긴 뒤) — 끊긴 뒤 서버에서 나온 발언은 남지 않았다';

// 멈춤 — 도는 웹 심의를 서버에서 그친다(docs/leftovers-1017 triage A24 (나)). 입력창의 ■ 는 받기만 끊고 심의는 서버에서 끝까지 돈다 — 그치는
// 길은 이 단추다(포털 POST /agent/deliberate/cancel → 에이전트 서버). 받는 중인 심의와, 받기가 끊긴 채(■ · 끊김 · 새로고침) 결정문 없이 멈춰
// 보이는 마지막 심의에 보인다 — 끊긴 쪽도 서버에서 아직 돌 수 있다(아니면 서버가 '이미 끝났다' · '찾지 못했다' 로 답한다). 이 칸의 실행 id 로
// 그 심의 하나만 짚는다 — 대화 id 만으로 멈추면 낡은 화면이 같은 대화의 새 심의를 접는다. 누른 동안 잠그고 결과를 단추 옆에 적는다. 받는 중에
// 멈추면 곧 멈춤 사건이 와 이 줄 대신 아래 '멈춤' 알림이 남는다. 받기가 끊긴 심의는 사건이 오지 않으므로 멈춤을 칸에 적는다(새로고침 뒤에도
// 남게 — 포털은 같은 글을 서버 대화에 남긴다).
function StopBar({ msgId, runId, cut }: { msgId: string; runId: string; cut: boolean }) {
  const { activeConversation, markDelibStopped } = useChat();
  const sid = activeConversation?.serverId;
  const [busy, setBusy] = useState(false);
  const [stopped, setStopped] = useState(false);
  const [said, setSaid] = useState<{ text: string; bad: boolean } | null>(null);
  const stop = async () => {
    if (!sid || busy) return;
    if (!window.confirm(cut ? STOP_CONFIRM_CUT : STOP_CONFIRM_LIVE)) return;
    setBusy(true);
    setSaid(null);
    const r = await cancelDeliberation(sid, runId);
    setBusy(false);
    if (r.ok) {
      setStopped(true);
      if (cut) markDelibStopped(msgId, r.stopNote || STOP_NOTE_CUT);
    }
    setSaid({
      text: stopSaid(r, cut),
      bad: !r.ok && !['already_finished', 'delib_not_found', 'finishing'].includes(r.code),
    });
  };
  return (
    <div className="dv-stop">
      {!stopped && (
        <button
          type="button"
          className="dv-stop-btn"
          onClick={() => void stop()}
          disabled={busy || !sid}
          aria-busy={busy}
          title={
            !sid
              ? '서버 대화 사본이 없어 멈출 수 없습니다 — ■ 로 받기만 끊을 수 있습니다'
              : '서버에서 도는 이 심의를 멈춥니다 — ■ 는 받기만 끊고 심의는 서버에서 계속 돕니다'
          }
        >
          {busy ? '멈추는 중…' : '멈춤'}
        </button>
      )}
      {cut && !said && <span className="dv-stop-note">받기가 끊겼습니다 — 심의는 서버에서 아직 돌 수 있습니다.</span>}
      {said && (
        <span className={`dv-stop-said${said.bad ? ' is-bad' : ''}`} role="status">
          {said.text}
        </span>
      )}
    </div>
  );
}

export function DelibView({ msg }: { msg: Message }) {
  const d = msg.delib!;
  const live = Boolean(msg.streaming);
  const can = useCan();
  const { messages } = useChat();
  const decision = useMemo(() => d.decision ?? '', [d.decision]);
  // 받기가 끊긴 채 결정문 없이 멈춰 보이는 대화의 마지막 심의 — 서버에서 아직 돌 수 있다(멈춤 단추를 남긴다).
  const cut =
    !live && !d.decision && !d.outcome && !d.cancelled && delibMayStillRun(msg.error) && messages[messages.length - 1]?.id === msg.id;
  // 멈출 열쇠(실행 id)가 있고, 의장이 결정문을 낸 뒤의 마무리가 아닐 때만 — 마무리에는 에이전트가 멈추지 않는다(다 만든 결정문을 버리지 않게).
  const stoppable = (live || cut) && !d.cancelled && !d.finishing && Boolean(d.runId);
  return (
    <div className="dv-root">
      <Stepper d={d} live={live} />
      {stoppable && <StopBar msgId={msg.id} runId={d.runId ?? ''} cut={cut} />}
      {d.cancelled && (
        <p className="dv-stopped" role="status">
          멈춤 — {d.cancelled.message || '사람이 멈췄다'}
        </p>
      )}
      <PersonaIntro d={d} />
      <EvidenceCard d={d} />
      <Meeting d={d} live={live} />
      {/* 관계도 — 회의록은 시간순이라 '누가 누구를 향해 말했는지' 가 안 보인다.
          진행 중에는 반박이 아직 모이지 않았으므로 끝난 뒤에만 그린다. */}
      {!live && <DelibGraph d={d} />}
      <Convergence d={d} />
      {decision && (
        <section className="dv-decision">
          <div className="dv-round-div chair">
            <span>의장 · 의사결정문</span>
          </div>
          <TextBlock text={decision} />
        </section>
      )}
      {/* 쉬운 설명 — 정식 심의 단계('explain')의 산출물. 결정문이 전문용어로 촘촘해
          비전문가가 못 읽는 문제를 절차로 해소한다. 결정문 본문에도 포함되지만,
          여기서 별도 카드로 강조해 '그래서 뭘 하라는 건지'가 바로 보이게 한다. */}
      {d.plain && (
        <section className="dv-plain">
          <div className="dv-round-div chair">
            <span>쉬운 설명 · 비전문가용 정리</span>
          </div>
          <TextBlock text={d.plain} />
        </section>
      )}
      <OutcomeCards d={d} />
      {/* 지난 심의를 보는 것은 누구나, 이어 돌리는 것은 심의 권한이 있어야 한다. */}
      {!live && can('feat:deliberation') && <ContinueBar d={d} />}
    </div>
  );
}
