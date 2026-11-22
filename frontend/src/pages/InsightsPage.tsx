// 과제 인사이트 — 과제(SP 허브 key) · 차수마다 앞선 심의 · 심사의 결정 카드와 리스크 심사 행을 보고, 내 초안을 확인 · 고친다(docs/project-insight-graph M2 · M4)
import { useCallback, useEffect, useState } from 'react';
import { Page, PageHeader } from '../components/ui/Page';
import { Tabs } from '../components/ui/Tabs';
import { ErrorBanner } from '../components/common/ErrorBanner';
import {
  confirmCard,
  disputeCard,
  fetchCard,
  fetchMine,
  fetchProject,
  fetchProjects,
  fetchReview,
  setCardClaim,
  setCardRound,
  setCardSubject,
  projectCardToRa,
  widenCard,
  withdrawCard,
  type InsightCard,
  type InsightStale,
  type MineView,
  type ProjectRow,
  type ProjectView,
  type ReviewView,
  type RiskProject,
} from '../api/insights.api';
import { searchSubjectTasks, type SubjectTaskRow } from '../api/chat.api';
import { STAGE_CODES } from '../components/chat/subject';
import '../styles/insights.css';

type TabKey = 'projects' | 'mine' | 'review';

const PATH_LABEL: Record<string, string> = { web: '웹 심의', 'mcp-job': 'MCP 심의', 'mcp-workflow': 'Claude 워크플로' };
const STATUS_LABEL: Record<string, string> = { waiting: '주제 확인 기다림', draft: '초안 — 나만 본다', confirmed: '확인', disputed: '반박 있음' };
const NOTE = '앞선 인사이트 — 검증 대상이고 독립 근거가 아니다. 출처와 상태를 보고 쓴다.';

const day = (ts: number) => new Date(ts * 1000).toLocaleString();
const roundLabel = (r: string | null) => (r ? `차수 ${r}` : '차수 모름');

function scopeText(scope: string[]): string {
  return scope
    .map((t) => (t === 'org' ? '조직 전체' : t.startsWith('aff:') ? `소속 ${t.slice(4)}` : t.startsWith('user:') ? '나만' : t.startsWith('plat:') ? `권한 ${t.slice(5)}` : t))
    .join(' · ');
}

/** 판 표지 — 서버가 읽을 때 셈한 것(기구 CAD 의 뒤 판 · 내용 바뀜). 낡았을 수 있으면 카드를 다시 읽어 뒤 판의 리스크 변경 심사 줄을 편다. */
function StaleLine({ cardId, stale }: { cardId: string; stale: InsightStale }) {
  const [full, setFull] = useState<InsightStale | null>(stale.risk_note ? stale : null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const open = async () => {
    setBusy(true);
    setErr('');
    try {
      const c = await fetchCard(cardId);
      setFull(c.stale ?? { ...stale, risk_note: '판 표지를 다시 읽지 못했다' });
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  const diffs = full?.risk_diffs ?? [];
  // 뒤 판이 있을 때만 물을 것이 있다 — 내용만 바뀐 카드(뒤 판 없음)는 리스크 변경 심사가 없다
  const hasNext = stale.items.some((i) => (i.next?.length ?? 0) > 0);
  return (
    <div className={`ins-stale ins-stale-${stale.state}`}>
      <p className={stale.state === 'stale' ? 'ins-why' : 'ins-sub'}>
        판 — {stale.say}
        {hasNext && !full && (
          <button type="button" className="btn-secondary ins-inline-btn" disabled={busy} onClick={() => void open()}>
            뒤 판의 리스크 변경 심사 보기
          </button>
        )}
      </p>
      {full?.risk_note && <p className="ins-sub">{full.risk_note}</p>}
      {diffs.map((d) => (
        <div key={d.target_key} className="ins-risk">
          <div>
            <strong>리스크 변경 심사</strong> · {d.risk_project.code || d.risk_project.project_id}
            {d.risk_project.name ? ` — ${d.risk_project.name}` : ''} · 대상 {d.target_key}
            {d.error ? ` · 읽지 못했다(${d.error})` : ` · 변경 ${d.total ?? 0}건`}
          </div>
          {d.lines && d.lines.length > 0 && (
            <ul className="ins-risk-list">
              {d.lines.map((ln, i) => (
                <li key={i}>{ln}</li>
              ))}
              {d.truncated && <li>… 나머지는 리스크 앱에서 본다</li>}
            </ul>
          )}
        </div>
      ))}
      {err && <p className="ins-err">{err}</p>}
    </div>
  );
}

/** 카드 한 장 — 주인이면 확인 · 차수 · 주장 · 조직 공개 · 반박 · 거두기를 한다(쓰기는 세션 + CSRF — 서버가 주인인지 다시 본다). */
function InsightCardView({ card, onChanged }: { card: InsightCard; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [editing, setEditing] = useState(false);
  const [claim, setClaim] = useState(card.claim);
  const [disputing, setDisputing] = useState(false);
  const [byCard, setByCard] = useState('');
  const [note, setNote] = useState('');

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setErr('');
    try {
      await fn();
      onChanged();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  const t = card.tally;
  // RA 투영(M5) — 칸이 오면 박스에서 켜져 있다. 조직에만 연 확인 카드이고 RA 보고서 · 과제가 있을 때 주인이 단다(서버가 다시 본다)
  const canProject =
    card.ra === null &&
    card.mine &&
    card.status === 'confirmed' &&
    card.scope.length === 1 &&
    card.scope[0] === 'org' &&
    card.report_id != null &&
    !!card.subject.sp_task;
  const project = () => {
    const ask =
      `RA 보고서 #${card.report_id} 에 과제 「${card.subject.sp_task}」 의 객체 태그를 답니다. 그 보고서를 볼 수 있는 사람의 RA 검색 · 과제 화면에 ` +
      '서고, 보고서의 공개 범위는 바뀌지 않습니다. 카드를 거두어도 RA 의 태그는 떼지 않습니다(RA 보고서 편집 화면에서 손으로 뗍니다). 달까요?';
    if (window.confirm(ask)) void act(() => projectCardToRa(card.id));
  };
  // 거두기 — 기다림 줄 카드도 주인이 거둔다(주제를 확인할 생각이 없으면 버린다)
  const withdrawBtn = (
    <button
      type="button"
      className="btn-secondary"
      disabled={busy}
      onClick={() => {
        if (window.confirm('이 카드를 거둘까요? 내용이 지워지고 아무에게도 보이지 않습니다.'))
          void act(async () => {
            const out = await withdrawCard(card.id);
            if (out.ra) window.alert(out.ra.note);
          });
      }}
    >
      거두기
    </button>
  );
  return (
    <article className={`ins-card ins-${card.status}`}>
      <header className="ins-card-head">
        <span className={`ins-chip ins-chip-${card.status}`}>{STATUS_LABEL[card.status] ?? card.status}</span>
        {card.stale?.state === 'stale' && <span className="ins-chip ins-chip-waiting">판이 바뀜</span>}
        {card.same && <span className="ins-chip" title="같은 칸에서 주장 글이 같은 카드(내가 볼 수 있는 것만) — 합치지 않는다">같은 결론 {card.same.n}번</span>}
        <span className="ins-meta">
          {PATH_LABEL[card.path] ?? card.path} · {card.stage} · {card.owner}
          {card.mine ? ' (나)' : ''} · {day(card.created_at)}
        </span>
      </header>
      {editing ? (
        <div className="ins-edit">
          <textarea value={claim} maxLength={500} rows={4} onChange={(e) => setClaim(e.target.value)} aria-label="주장" />
          <div className="ins-actions">
            <button type="button" className="btn-primary" disabled={busy} onClick={() => void act(async () => { await setCardClaim(card.id, claim); setEditing(false); })}>
              저장
            </button>
            <button type="button" className="btn-secondary" onClick={() => { setClaim(card.claim); setEditing(false); }}>
              취소
            </button>
          </div>
        </div>
      ) : (
        <p className="ins-claim">{card.claim || '(주장이 없다 — 결정문은 RA 보고서 · 원래 대화에 있다)'}</p>
      )}
      <p className="ins-sub">
        {card.subject.sp_task ? `과제 「${card.subject.sp_task}」` : '과제 없음'} · {roundLabel(card.subject.round)}
        {card.subject.round_by === 'person' ? '(사람이 단 차수)' : ''}
        {card.subject.text ? ` · ${card.subject.text}` : ''}
        {card.claim_edited_by ? ` · 주장은 ${card.claim_edited_by} 가 고쳤다` : ''}
      </p>
      {card.status === 'waiting' && card.subject.sp_why && <p className="ins-why">확인하지 못한 까닭 — {card.subject.sp_why}</p>}
      <p className="ins-sub">
        {t ? `표결 동의 ${t.agree} · 조건부 ${t.conditional} · 반대 ${t.oppose} · 미표명 ${t.abstain}` : ''}
        {card.report_id != null ? ` · RA 보고서 #${card.report_id}` : ''}
        {card.calls_n ? ` · 근거 표지 ${card.calls_n}건` : ''}
        {card.model ? ` · 모델 ${card.model}` : ''}
      </p>
      <p className="ins-sub">
        보이는 범위 — {scopeText(card.scope)}
        {card.scope_note ? ` (${card.scope_note})` : ''}
      </p>
      {card.disputed_by && card.disputed_by.length > 0 && (
        <p className="ins-why">반박 — {card.disputed_by.map((d) => `${d.by ?? '사람'}${d.note ? `: ${d.note}` : ''}`).join(' / ')}</p>
      )}
      {card.continues && <p className="ins-sub">이어하기 — 앞 카드 {card.continues}</p>}
      {card.stale && <StaleLine cardId={card.id} stale={card.stale} />}
      {card.same && <p className="ins-sub">같은 결론의 다른 카드 — {card.same.ids.join(' · ')}</p>}
      {card.ra && (
        <p className="ins-sub">
          RA 과제 객체에 달림 — {card.ra.value}(#{card.ra.entity_id}) · 보고서 #{card.ra.report_id} · {day(card.ra.at)}
        </p>
      )}
      {card.mine && card.status !== 'waiting' && (
        <div className="ins-actions">
          {card.status === 'draft' && (
            <button type="button" className="btn-primary" disabled={busy} onClick={() => void act(() => confirmCard(card.id))}>
              확인 — 같은 소속에 열기
            </button>
          )}
          <label className="ins-round">
            차수
            <select
              value={card.subject.round ?? 'unknown'}
              disabled={busy}
              onChange={(e) => void act(() => setCardRound(card.id, e.target.value))}
            >
              {STAGE_CODES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
              <option value="unknown">모름</option>
            </select>
          </label>
          {!editing && (
            <button type="button" className="btn-secondary" disabled={busy} onClick={() => setEditing(true)}>
              주장 고치기
            </button>
          )}
          {(card.status === 'confirmed' || card.status === 'disputed') && card.evidence_known && !card.scope.includes('org') && (
            <button type="button" className="btn-secondary" disabled={busy} onClick={() => void act(() => widenCard(card.id))}>
              조직에 열기
            </button>
          )}
          {canProject && (
            <button type="button" className="btn-secondary" disabled={busy} onClick={project}>
              RA 과제 객체에 달기
            </button>
          )}
          {(card.status === 'confirmed' || card.status === 'disputed') && (
            <button type="button" className="btn-secondary" disabled={busy} onClick={() => setDisputing((v) => !v)}>
              반박 표시
            </button>
          )}
          {withdrawBtn}
        </div>
      )}
      {card.mine && card.status === 'waiting' && <div className="ins-actions">{withdrawBtn}</div>}
      {disputing && (
        <div className="ins-edit">
          <input value={byCard} onChange={(e) => setByCard(e.target.value)} placeholder="반박한 카드 id(선택)" aria-label="반박한 카드 id" />
          <input value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} placeholder="무엇이 틀렸나(선택)" aria-label="반박 메모" />
          <button
            type="button"
            className="btn-primary"
            disabled={busy}
            onClick={() => void act(async () => { await disputeCard(card.id, byCard.trim(), note.trim()); setDisputing(false); })}
          >
            반박 남기기
          </button>
        </div>
      )}
      {err && <p className="ins-err">{err}</p>}
    </article>
  );
}

/** 기다림 줄의 주제 확인 — 허브 과제 찾기(그 사람의 권한)의 결과 행에서 고른다. 서버가 같은 풀이로 다시 확인한다. */
function SubjectConfirm({ card, onChanged }: { card: InsightCard; onChanged: () => void }) {
  const [q, setQ] = useState(card.subject.sp_task ?? '');
  const [rows, setRows] = useState<SubjectTaskRow[]>([]);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const search = async () => {
    setBusy(true);
    setMsg('');
    const got = await searchSubjectTasks(q.trim());
    setRows(got.rows);
    setMsg(got.error ? `찾지 못했다 — ${got.error}` : got.rows.length ? '' : got.why?.message || '맞는 과제가 없다');
    setBusy(false);
  };
  const pick = async (key: string) => {
    setBusy(true);
    try {
      const r = await setCardSubject(card.id, key);
      if (r.confirmed) onChanged();
      else setMsg(`확인되지 않았다 — ${r.subject.sp_why ?? '까닭 없음'}`);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="ins-confirm">
      <div className="ins-actions">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="과제 이름 · 코드" aria-label="허브 과제 찾기" />
        <button type="button" className="btn-secondary" disabled={busy || !q.trim()} onClick={() => void search()}>
          허브에서 찾기
        </button>
      </div>
      {rows.length > 0 && (
        <ul className="ins-rows">
          {rows.map((r) => (
            <li key={r.key}>
              <button type="button" className="btn-secondary" disabled={busy || r.active === false} onClick={() => void pick(r.key)}>
                {r.key}
                {r.task_code ? ` · ${r.task_code}` : ''}
                {r.active === false ? ' · 비활성' : ''}
              </button>
            </li>
          ))}
        </ul>
      )}
      {msg && <p className="ins-why">{msg}</p>}
    </div>
  );
}

/** 리스크 심사 행 — 과제 머리 · 지금 대상의 판정 · 등록부 앞 행. 리스크 앱의 낱말(판정 · 상태 · 주의)은 번역하지 않는다. */
function RiskRow({ p }: { p: RiskProject }) {
  const targets = p.targets ?? [];
  const top = p.registry_top ?? [];
  return (
    <li className="ins-risk">
      <div>
        <strong>리스크 심사</strong> · {p.code ?? p.project_id} {p.name ? `— ${p.name}` : ''} · 단계 {p.stage || '없음'}
        {p.my_role ? ` · 내 역할 ${p.my_role}` : ''} · 대상 {targets.length} · 등록부 {p.registry_total ?? top.length}
      </div>
      {targets.length > 0 && (
        <ul className="ins-risk-list">
          {targets.map((t) => (
            <li key={t.target_key}>
              대상 {t.target_key}
              {t.kind ? ` (${t.kind}${t.level ? ` · ${t.level}` : ''})` : ''} · 판정{' '}
              {t.verdict_final ?? (t.verdict_candidate ? `${t.verdict_candidate}(후보)` : '없음')}
            </li>
          ))}
        </ul>
      )}
      {top.length > 0 && (
        <ul className="ins-risk-list">
          {top.map((r, i) => (
            <li key={`${r.target_key}:${r.cluster_key ?? i}`}>
              등록부 {r.status ?? '상태 없음'}
              {r.attention ? ` · 주의 ${r.attention}` : ''}
              {r.severity ? ` · 심각도 ${r.severity}` : ''}
              {r.claim ? ` — ${r.claim}` : ''}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

function ProjectDetail({ spTask }: { spTask: string }) {
  const [view, setView] = useState<ProjectView | null>(null);
  const [err, setErr] = useState('');
  const load = useCallback(() => {
    setErr('');
    fetchProject(spTask).then(setView, (e: Error) => setErr(e.message));
  }, [spTask]);
  useEffect(load, [load]);
  if (err) return <ErrorBanner message={err} />;
  if (!view) return <p className="ins-meta">읽는 중…</p>;
  return (
    <section className="ins-project">
      <h2>과제 「{view.sp_task}」</h2>
      {view.previous_keys && view.previous_keys.length > 0 && (
        <p className="ins-sub">옛 key 로 남은 카드를 함께 모았다 — {view.previous_keys.map((k) => `「${k}」`).join(' · ')}</p>
      )}
      {view.keys_note && <p className="ins-why">{view.keys_note}</p>}
      {view.risk_error && <p className="ins-why">{view.risk_error}</p>}
      {view.note_rows && <p className="ins-why">{view.note_rows}</p>}
      {view.rounds.length === 0 && <p className="ins-meta">내가 볼 수 있는 카드 · 리스크 심사가 없다.</p>}
      {view.rounds.map((cell) => (
        <div key={cell.round ?? 'unknown'} className="ins-cell">
          <h3>{roundLabel(cell.round)}</h3>
          {cell.risk.length > 0 && (
            <ul className="ins-risks">
              {cell.risk.map((p) => (
                <RiskRow key={p.project_id} p={p} />
              ))}
            </ul>
          )}
          {cell.cards.map((c) => (
            <InsightCardView key={c.id} card={c} onChanged={load} />
          ))}
        </div>
      ))}
    </section>
  );
}

function ProjectsTab() {
  const [q, setQ] = useState('');
  const [rows, setRows] = useState<ProjectRow[] | null>(null);
  const [riskErr, setRiskErr] = useState('');
  const [rowsNote, setRowsNote] = useState('');
  const [err, setErr] = useState('');
  const [picked, setPicked] = useState('');
  const load = useCallback((query: string) => {
    setErr('');
    fetchProjects(query).then(
      (r) => {
        setRows(r.projects);
        setRiskErr(r.risk_error ?? '');
        setRowsNote(r.note_rows ?? '');
      },
      (e: Error) => setErr(e.message),
    );
  }, []);
  useEffect(() => load(''), [load]);
  return (
    <div className="ins-split">
      <aside className="ins-list">
        <form
          className="ins-actions"
          onSubmit={(e) => {
            e.preventDefault();
            load(q);
          }}
        >
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="과제 key 에 든 말" aria-label="과제 찾기" />
          <button type="submit" className="btn-secondary">
            찾기
          </button>
        </form>
        {err && <ErrorBanner message={err} />}
        {riskErr && <p className="ins-why">{riskErr}</p>}
        {rowsNote && <p className="ins-why">{rowsNote}</p>}
        {rows && rows.length === 0 && <p className="ins-meta">내가 볼 수 있는 과제가 없다.</p>}
        <ul className="ins-projects">
          {rows?.map((p) => (
            <li key={p.sp_task}>
              <button type="button" className={`ins-project-btn${picked === p.sp_task ? ' is-on' : ''}`} onClick={() => setPicked(p.sp_task)}>
                <span>{p.sp_task}</span>
                <span className="ins-meta">
                  카드 {p.total}
                  {p.risk ? ` · 리스크 ${p.risk}` : ''}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <div className="ins-main">{picked ? <ProjectDetail key={picked} spTask={picked} /> : <p className="ins-meta">과제를 고른다.</p>}</div>
    </div>
  );
}

function MineTab() {
  const [view, setView] = useState<MineView | null>(null);
  const [err, setErr] = useState('');
  const load = useCallback(() => {
    setErr('');
    fetchMine().then(setView, (e: Error) => setErr(e.message));
  }, []);
  useEffect(load, [load]);
  if (err) return <ErrorBanner message={err} />;
  if (!view) return <p className="ins-meta">읽는 중…</p>;
  return (
    <div>
      <section className="ins-cell">
        <h3>주제 확인 기다림 {view.waiting.length}</h3>
        <p className="ins-meta">심의를 열 때 준 과제 key 를 서버가 확인하지 못한 카드다 — 어느 과제 보기에도 없다. 허브에서 찾은 행을 고르면 초안이 선다.</p>
        {view.waiting.map((c) => (
          <div key={c.id}>
            <InsightCardView card={c} onChanged={load} />
            <SubjectConfirm card={c} onChanged={load} />
          </div>
        ))}
      </section>
      <section className="ins-cell">
        <h3>초안 {view.draft.length}</h3>
        <p className="ins-meta">나만 본다 — 주제 · 차수 · 주장을 보고 확인하면 같은 소속에 열린다.</p>
        {view.draft.map((c) => (
          <InsightCardView key={c.id} card={c} onChanged={load} />
        ))}
      </section>
      <section className="ins-cell">
        <h3>확인한 카드 {view.shared.length}</h3>
        {view.shared.map((c) => (
          <InsightCardView key={c.id} card={c} onChanged={load} />
        ))}
      </section>
    </div>
  );
}

const REASON_LABEL: Record<string, string> = {
  waiting: '주제 확인',
  disputed: '반박',
  stale: '판이 바뀜',
  draft: '초안',
  round_unknown: '차수 모름',
  admin_disputed: '남의 반박 카드(관리자)',
};

/** 검토 줄 — 내가 손댈 카드와 까닭. 까닭의 글은 서버가 준다(관리자에게는 반박이 달린 남의 카드도 선다). */
function ReviewTab() {
  const [view, setView] = useState<ReviewView | null>(null);
  const [err, setErr] = useState('');
  const load = useCallback(() => {
    setErr('');
    fetchReview().then(setView, (e: Error) => setErr(e.message));
  }, []);
  useEffect(load, [load]);
  if (err) return <ErrorBanner message={err} />;
  if (!view) return <p className="ins-meta">읽는 중…</p>;
  return (
    <section className="ins-cell">
      <h3>손댈 카드 {view.items.length}</h3>
      <p className="ins-meta">
        주제 확인 · 반박 · 설계 판이 바뀐 것 · 초안 · 차수 모름 차례다. 판이 바뀌었는지는 지금 읽어 셈한 것이다(기구 CAD 의 뒤 판 · 내용 바뀜).
      </p>
      {view.items.length === 0 && <p className="ins-meta">손댈 카드가 없다.</p>}
      {view.items.map((it) => (
        <div key={it.card.id}>
          <p className="ins-why">
            {it.reasons.map((r) => REASON_LABEL[r] ?? r).join(' · ')} — {it.say}
          </p>
          <InsightCardView card={it.card} onChanged={load} />
          {it.card.status === 'waiting' && it.card.mine && <SubjectConfirm card={it.card} onChanged={load} />}
        </div>
      ))}
    </section>
  );
}

export default function InsightsPage() {
  const [tab, setTab] = useState<TabKey>('projects');
  return (
    <Page width="wide">
      <PageHeader title="과제 인사이트" desc={`과제 · 차수마다 앞선 심의 · 심사의 결정 카드를 모아 본다. ${NOTE}`} />
      <Tabs
        tabs={[
          { key: 'projects', label: '과제' },
          { key: 'mine', label: '내 카드' },
          { key: 'review', label: '검토 줄' },
        ]}
        value={tab}
        onChange={setTab}
        label="과제 인사이트"
      >
        {tab === 'projects' ? <ProjectsTab /> : tab === 'mine' ? <MineTab /> : <ReviewTab />}
      </Tabs>
    </Page>
  );
}
