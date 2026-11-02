// LLM · GPU 현황(관리자 전용) — 호스트 수집기가 15초마다 읽은 LLM 서버 · 에이전트 서버 · 라우터 상태를 서버 카드 · 작은 그래프로 본다(docs/ops-dashboard)
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Page, PageHeader } from '../../components/ui/Page';
import {
  CollectorError,
  fetchLlmSeries,
  fetchLlmStatus,
  type Cell,
  type ContextDiff,
  type LlmSeries,
  type LlmSnapshot,
  type LlmTarget,
  type ModelRow,
  type SeriesRange,
  type SideView,
  type SourceAge,
  type StubSection,
} from '../../api/llmStatus.api';
import { useAuth } from '../../auth/useAuth';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';
import '../../styles/admin.css';

const SNAP_EVERY_MS = 15_000; // 수집기 주기와 같다
const SERIES_1H_MS = 60_000;
const SERIES_24H_MS = 300_000;
const nf = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 1 });
const nf0 = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 0 });
const SOURCE_LABEL: Record<string, string> = { health: '상태', version: '판', metrics: '지표', models: '모델 목록' };

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

function ago(s: number | null | undefined): string {
  if (s === null || s === undefined) return '모름';
  if (s < 90) return `${Math.max(0, Math.round(s))}초 전`;
  if (s < 5400) return `${Math.round(s / 60)}분 전`;
  return `${Math.round(s / 3600)}시간 전`;
}

const fmtInt = (v: unknown) => nf0.format(Number(v));
const fmtNum = (v: unknown) => nf.format(Number(v));
const fmtPct = (v: unknown) => `${nf.format(Number(v) * 100)}%`;
const fmtPerMin = (v: unknown) => `${nf.format(Number(v))}/분`;
const fmtSec = (v: unknown) => {
  const s = Number(v);
  return s < 1 ? `${nf0.format(s * 1000)}ms` : `${nf.format(s)}초`;
};

/** 값 칸 — 값이 없으면 까닭(짧으면 그대로, 길면 '—' 에 풍선 도움말), 낡았으면 표지, 어림이면 ≈ */
function V({ c, f }: { c?: Cell; f: (v: unknown) => ReactNode }) {
  if (!c) return <span className="lls-unknown">모름</span>;
  if (c.value === null || c.value === undefined) {
    const e = c.error ?? '';
    return (
      <span className="lls-unknown" title={e || undefined}>
        {e && e.length <= 16 ? e : '—'}
      </span>
    );
  }
  return (
    <>
      {c.approx ? '≈ ' : ''}
      {f(c.value)}
      {c.stale && (
        <span className="lls-badge is-warn" title={c.error ?? undefined}>
          낡음 · {ago(c.age_s)}
        </span>
      )}
    </>
  );
}

function UpBadge({ t }: { t: { problem: string | null; values: Record<string, Cell> } }) {
  const up = t.values.up;
  if (t.problem) return <span className="lls-badge is-bad">설정 문제</span>;
  if (up?.value === true)
    return <span className={`lls-badge ${up.stale ? 'is-warn' : 'is-ok'}`}>{up.stale ? `살아 있음 · 낡음 ${ago(up.age_s)}` : '살아 있음'}</span>;
  if (up?.value === false) return <span className="lls-badge is-bad">내려감</span>;
  return <span className="lls-badge">모름</span>;
}

/** 대상이 '모름' · 내려감이면 그 까닭을 글로(풍선 도움말이 아니라) — 설정된 대상은 숨기지 않는다 */
function whyOf(t: { problem: string | null; values: Record<string, Cell>; sources: Record<string, SourceAge> }): string | null {
  if (t.problem) return t.problem.startsWith('모름') ? t.problem : `모름 — ${t.problem}`;
  const up = t.values.up;
  if (!up || up.value === null) return up?.error ?? '모름 — 아직 읽지 못했다';
  if (up.value === false) return up.error ?? '내려감';
  const m = t.sources.metrics?.error;
  return m ? `지표 — ${m}` : null;
}

// ── 작은 그래프(인라인 SVG — 차트 라이브러리 없음) ────────────────────────────────────────────────
function segments(s: LlmSeries | undefined, t0: number, span: number, top: number, w: number, h: number): string[] {
  if (!s) return [];
  const gap = Math.max(1, s.step_s) * 2.5; // 칸이 비면 선을 끊는다(빈칸을 잇지 않는다)
  const out: string[] = [];
  let cur: string[] = [];
  let prev: number | null = null;
  const flush = () => {
    if (cur.length === 1) cur.push(cur[0]); // 점 하나는 짧은 선으로
    if (cur.length) out.push(cur.join(' '));
    cur = [];
  };
  for (const p of s.points) {
    const ts = num(p[0]);
    const v = num(p[1]);
    if (ts === null || v === null || ts < t0) continue;
    if (prev !== null && ts - prev > gap) flush();
    const x = ((ts - t0) / span) * w;
    const y = h - 1 - (Math.min(v, top) / top) * (h - 2);
    cur.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    prev = ts;
  }
  flush();
  return out;
}

function Spark({ run, wait, span, label }: { run?: LlmSeries; wait?: LlmSeries; span: number; label: string }) {
  const W = 120;
  const H = 32;
  const t0 = Date.now() / 1000 - span;
  const vals = [run, wait].flatMap((s) => (s?.points ?? []).map((p) => num(p[1])).filter((v): v is number => v !== null));
  const top = Math.max(1, ...vals);
  return (
    <figure className="lls-spark-box">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="lls-spark"
        role="img"
        aria-label={`${label} — 도는 요청 · 기다리는 요청${vals.length ? `(최대 ${nf0.format(top)})` : '(기록 없음)'}`}
      >
        <line x1={0} y1={H - 0.5} x2={W} y2={H - 0.5} className="is-axis" />
        {segments(wait, t0, span, top, W, H).map((pts, i) => (
          <polyline key={`w${i}`} points={pts} className="is-wait" />
        ))}
        {segments(run, t0, span, top, W, H).map((pts, i) => (
          <polyline key={`r${i}`} points={pts} className="is-run" />
        ))}
      </svg>
      <figcaption>
        {label} · {vals.length ? `최대 ${nf0.format(top)}` : '기록 없음'}
      </figcaption>
    </figure>
  );
}

function Meter({ frac }: { frac: number }) {
  const pct = Math.max(0, Math.min(1, frac)) * 100;
  const tone = pct >= 90 ? 'is-bad' : pct >= 75 ? 'is-warn' : '';
  return (
    <svg viewBox="0 0 100 6" preserveAspectRatio="none" className="lls-meter" aria-hidden="true">
      <rect x={0} y={0} width={100} height={6} className="is-bg" />
      <rect x={0} y={0} width={pct} height={6} className={`is-fg ${tone}`} />
    </svg>
  );
}

/** 대상 · 지표 · 범위 하나의 시계열을 여러 대상에 대해 — 보이는 동안만 다시 받는다 */
function useSeriesMap(ids: string[], metric: string, range: SeriesRange, everyMs: number, enabled: boolean) {
  const key = ids.join(',');
  const [map, setMap] = useState<Record<string, LlmSeries>>({});
  useEffect(() => {
    if (!enabled || !key) return;
    let dead = false;
    const run = () => {
      if (document.visibilityState !== 'visible') return;
      Promise.all(
        key.split(',').map((id) =>
          fetchLlmSeries(id, metric, range)
            .then((s) => [id, s] as const)
            .catch(() => null),
        ),
      ).then((rows) => {
        if (!dead) setMap(Object.fromEntries(rows.filter((r): r is readonly [string, LlmSeries] => r !== null)));
      });
    };
    run();
    const t = window.setInterval(run, everyMs);
    return () => {
      dead = true;
      window.clearInterval(t);
    };
  }, [key, metric, range, everyMs, enabled]);
  return map;
}

// ── 서버 카드 ─────────────────────────────────────────────────────────────────────────────────────
type Sparks = { run1h?: LlmSeries; wait1h?: LlmSeries; run24h?: LlmSeries; wait24h?: LlmSeries };

function windowsText(ctx: ContextDiff[], label: string): string {
  return ctx
    .filter((d) => label in d.windows)
    .map((d) => `${d.model} — ${Object.entries(d.windows).map(([k, n]) => `${k} ${nf0.format(n)}`).join(' · ')}`)
    .join(' / ');
}

function SourceAges({ src }: { src: Record<string, SourceAge> }) {
  const names = Object.keys(SOURCE_LABEL).filter((k) => src[k]);
  if (!names.length) return null;
  return (
    <p className="lls-ages">
      {names.map((k) => {
        const s = src[k];
        return (
          <span key={k} className={s.stale ? 'is-stale' : undefined} title={s.error ?? undefined}>
            {SOURCE_LABEL[k]} {s.at === null ? '못 읽음' : ago(s.age_s)}
          </span>
        );
      })}
    </p>
  );
}

function TargetCard({ t, ctx, sparks }: { t: LlmTarget; ctx: ContextDiff[]; sparks: Sparks | null }) {
  const v = t.values;
  const models = (v.models?.value as ModelRow[] | null) ?? null;
  const why = whyOf(t);
  const kv = num(v.kv?.value);
  return (
    <article className="lls-card" aria-label={`${t.label} ${t.addr ?? ''}`}>
      <header className="lls-card-head">
        <h3>{t.label}</h3>
        <UpBadge t={t} />
        {t.addr && <code className="lls-addr">{t.addr}</code>}
        {t.busy && (t.busy_s ?? 0) > 5 && <span className="lls-badge is-warn">읽는 중 · {Math.round(t.busy_s ?? 0)}초</span>}
      </header>
      {why && <p className="lls-why">{why}</p>}
      <dl className="lls-kv">
        <dt>모델</dt>
        <dd>
          <V c={v.models} f={() => (models ?? []).map((m) => m.id).join(', ')} />
        </dd>
        <dt>vLLM 판</dt>
        <dd>
          <V c={v.version} f={(x) => String(x)} />
        </dd>
        <dt>창</dt>
        <dd>
          <V c={v.context} f={(x) => `${fmtInt(x)} 토큰`} />
          {v.context_mismatch?.value === true && (
            <span className="lls-badge is-warn" title={windowsText(ctx, t.label)}>
              서버끼리 창이 다르다
            </span>
          )}
        </dd>
        <dt>요청</dt>
        <dd>
          도는 <V c={v.running} f={fmtInt} /> · 기다리는 <V c={v.waiting} f={fmtInt} />
        </dd>
      </dl>
      {sparks && (
        <div className="lls-sparks">
          <Spark run={sparks.run1h} wait={sparks.wait1h} span={3600} label="1시간" />
          <Spark run={sparks.run24h} wait={sparks.wait24h} span={86400} label="24시간" />
          <p className="lls-legend">
            <span className="is-run">— 도는</span> <span className="is-wait">— 기다리는</span>
          </p>
        </div>
      )}
      <dl className="lls-kv">
        <dt>KV 캐시</dt>
        <dd>
          {kv !== null && <Meter frac={kv} />}
          <V c={v.kv} f={fmtPct} />
        </dd>
        <dt>토큰/초</dt>
        <dd>
          입력 <V c={v.prompt_tps} f={fmtNum} /> · 출력 <V c={v.gen_tps} f={fmtNum} />
        </dd>
        <dt>첫 토큰</dt>
        <dd>
          p50 <V c={v.ttft_p50} f={fmtSec} /> · p95 <V c={v.ttft_p95} f={fmtSec} />
        </dd>
        <dt>끝까지</dt>
        <dd>
          p50 <V c={v.e2e_p50} f={fmtSec} /> · p95 <V c={v.e2e_p95} f={fmtSec} />
        </dd>
        <dt>줄 선 시간</dt>
        <dd>
          p50 <V c={v.queue_p50} f={fmtSec} /> · p95 <V c={v.queue_p95} f={fmtSec} />
        </dd>
        <dt>끝낸 요청</dt>
        <dd>
          <V c={v.requests_per_min} f={fmtPerMin} />
        </dd>
        <dt>HTTP 5xx 답</dt>
        <dd>
          <V c={v.http_5xx_per_min} f={fmtPerMin} />
        </dd>
        <dt>오류로 끝난 요청</dt>
        <dd>
          <V c={v.finished_error_per_min} f={fmtPerMin} />
        </dd>
        <dt>끊김 · 선점</dt>
        <dd>
          <V c={v.aborts_per_min} f={fmtPerMin} /> · <V c={v.preempt_per_min} f={fmtPerMin} />
        </dd>
        <dt>앞부분 캐시 적중</dt>
        <dd>
          <V c={v.prefix_hit} f={fmtPct} />
        </dd>
      </dl>
      <SourceAges src={t.sources} />
    </article>
  );
}

function ReplicaTable({ title, rows, ctx }: { title: string; rows: LlmTarget[]; ctx: ContextDiff[] }) {
  return (
    <div className="adm-sec">
      <h3>
        {title} — {rows.length}벌
      </h3>
      <div className="adm-table-wrap">
        <table className="adm-table lls-replicas">
          <thead>
            <tr>
              <th>복제본</th>
              <th>상태</th>
              <th className="adm-num">도는</th>
              <th className="adm-num">기다리는</th>
              <th className="adm-num">KV</th>
              <th className="adm-num">출력 토큰/초</th>
              <th className="adm-num">첫 토큰 p95</th>
              <th className="adm-num">창</th>
              <th>vLLM 판</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const v = r.values;
              const why = whyOf(r);
              return (
                <tr key={r.id}>
                  <td className="adm-nowrap">
                    <code>{r.addr ?? r.label}</code>
                    {r.node && <span className="adm-meta"> · {r.node}</span>}
                  </td>
                  <td>
                    <UpBadge t={r} />
                    {why && <span className="lls-why-inline"> {why}</span>}
                  </td>
                  <td className="adm-num">
                    <V c={v.running} f={fmtInt} />
                  </td>
                  <td className="adm-num">
                    <V c={v.waiting} f={fmtInt} />
                  </td>
                  <td className="adm-num">
                    <V c={v.kv} f={fmtPct} />
                  </td>
                  <td className="adm-num">
                    <V c={v.gen_tps} f={fmtNum} />
                  </td>
                  <td className="adm-num">
                    <V c={v.ttft_p95} f={fmtSec} />
                  </td>
                  <td className="adm-num">
                    <V c={v.context} f={fmtInt} />
                    {v.context_mismatch?.value === true && (
                      <span className="lls-badge is-warn" title={windowsText(ctx, r.label)}>
                        다름
                      </span>
                    )}
                  </td>
                  <td>
                    <V c={v.version} f={(x) => String(x)} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── 라우터 · 지금 쓰는 일 · Slurm · GPU ──────────────────────────────────────────────────────────
type Upstream = { addr: string; up: boolean | null; reachable: boolean | null; models: string | null; running: number | null;
  waiting: number | null; kv: number | null; inflight: number | null; sent: number | null; connect_fail: number | null };

function RouterSection({ r }: { r: SideView }) {
  const v = r.values;
  const ups = (v.upstreams?.value as Upstream[] | null) ?? [];
  const why = whyOf({ ...r, sources: r.sources });
  return (
    <section className="adm-sec" aria-label="LLM 라우터">
      <h2 className="lls-h2">
        LLM 라우터 <UpBadge t={r} /> {r.addr && <code className="lls-addr">{r.addr}</code>}
      </h2>
      {why && <p className="lls-why">{why}</p>}
      <p className="adm-hint">
        상태 <V c={v.status} f={(x) => String(x)} /> · 지나는 요청 <V c={v.inflight} f={fmtInt} /> · 올라온 서버{' '}
        <V c={v.upstreams_up} f={fmtInt} />/<V c={v.upstreams_total} f={fmtInt} /> · 모델 같음{' '}
        <V c={v.models_match} f={(x) => (x ? '예' : '아니오')} />
      </p>
      {ups.length > 0 && (
        <div className="adm-table-wrap">
          <table className="adm-table lls-upstreams">
            <thead>
              <tr>
                <th>서버</th>
                <th>올라옴</th>
                <th className="adm-num">도는</th>
                <th className="adm-num">기다리는</th>
                <th className="adm-num">KV</th>
                <th className="adm-num">라우터가 보낸 · 지나는</th>
                <th className="adm-num">연결 실패</th>
              </tr>
            </thead>
            <tbody>
              {ups.map((u) => (
                <tr key={u.addr}>
                  <td>
                    <code>{u.addr}</code>
                  </td>
                  <td>{u.up ? '예' : u.reachable ? '닿기만 한다' : '아니오'}</td>
                  <td className="adm-num">{num(u.running) === null ? '—' : fmtInt(u.running)}</td>
                  <td className="adm-num">{num(u.waiting) === null ? '—' : fmtInt(u.waiting)}</td>
                  <td className="adm-num">{num(u.kv) === null ? '—' : fmtPct(u.kv)}</td>
                  <td className="adm-num">
                    {num(u.sent) === null ? '—' : fmtInt(u.sent)} · {num(u.inflight) === null ? '—' : fmtInt(u.inflight)}
                  </td>
                  <td className="adm-num">{num(u.connect_fail) === null ? '—' : fmtInt(u.connect_fail)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

type ChatLoad = { active: number | null; slow: boolean; ttft_ms: Record<string, { n: number | null; p50: number | null; p95: number | null }> };
type ChatLlm = { enabled?: boolean; model?: string | null; server?: string | null; fallback?: { enabled?: boolean; count?: number | null } | null;
  last_error?: string | null };
type CardReview = { active?: number | null; limit?: number | null; limit_reason?: string | null };

function Tile({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="lls-tile">
      <span>{label}</span>
      <b>{children}</b>
    </div>
  );
}

function AgentPanel({ a }: { a: SideView }) {
  const v = a.values;
  const chat = (v.chat?.value as ChatLoad | null) ?? null;
  const cl = (v.chat_llm?.value as ChatLlm | null) ?? null;
  const cr = (v.card_review?.value as CardReview | null) ?? null;
  const why = whyOf(a);
  const ms = (x: number | null | undefined) => (num(x) === null ? '—' : `${nf0.format(Number(x))}ms`);
  return (
    <section className="adm-sec" aria-label="지금 쓰는 일">
      <h2 className="lls-h2">
        지금 쓰는 일 <UpBadge t={a} /> {a.addr && <code className="lls-addr">{a.addr}</code>}
      </h2>
      <p className="adm-hint">{a.caption}</p>
      {why && <p className="lls-why">{why}</p>}
      <div className="lls-tiles">
        <Tile label="심의 도는 · 줄 선">
          <V c={v.delib_active} f={fmtInt} /> · <V c={v.delib_queued} f={fmtInt} />
        </Tile>
        <Tile label="도는 GLM 잡의 좌석 합">
          <V c={v.delib_seats_running} f={fmtInt} />
        </Tile>
        <Tile label="새 심의 멈춤">
          <V c={v.delib_paused} f={(x) => (x ? '멈춤' : '아님')} />
        </Tile>
        <Tile label="루틴 도는 · 쉬는 · 상한">
          <V c={v.routine_active} f={fmtInt} /> · <V c={v.routine_parked} f={fmtInt} /> · <V c={v.routine_max} f={fmtInt} />
        </Tile>
        <Tile label="카드 대조 도는 · 상한">
          <V c={v.review_active} f={fmtInt} /> · {num(cr?.limit) === null ? '—' : fmtInt(cr?.limit)}
        </Tile>
        <Tile label="챗 턴 도는">
          <V c={v.chat_active} f={fmtInt} />
          {chat?.slow && <span className="lls-badge is-warn">느림</span>}
        </Tile>
        <Tile label="챗 첫 조각 p50 · 카드 대조 중">
          {ms(chat?.ttft_ms?.idle?.p50)} · {ms(chat?.ttft_ms?.review?.p50)}
        </Tile>
        <Tile label="챗 LLM">
          {cl === null ? (
            <V c={v.chat_llm} f={() => ''} />
          ) : cl.enabled ? (
            <span title={cl.last_error ?? undefined}>
              {cl.model ?? '—'} · 넘김 {num(cl.fallback?.count) === null ? '—' : fmtInt(cl.fallback?.count)}회
            </span>
          ) : (
            '꺼짐(챗도 심의 LLM)'
          )}
        </Tile>
        <Tile label="심의 LLM 의 창">
          <V c={v.context_tokens} f={(x) => `${fmtInt(x)} 토큰`} />
        </Tile>
      </div>
    </section>
  );
}

function StubBlock({ title, s }: { title: string; s: StubSection }) {
  return (
    <section className="adm-sec" aria-label={title}>
      <h2 className="lls-h2">
        {title} <span className="lls-badge">모름</span>
      </h2>
      <p className="lls-why">{s.error}</p>
    </section>
  );
}

function CollectorHead({ s, targets }: { s: LlmSnapshot; targets: LlmTarget[] }) {
  const c = s.collector;
  const rows: { id: string; label: string; addr: string | null; src: Record<string, SourceAge> }[] = [
    ...targets.map((t) => ({ id: t.id, label: t.label, addr: t.addr, src: t.sources })),
    { id: 'agent', label: s.agent.label, addr: s.agent.addr, src: s.agent.sources },
    ...(s.router ? [{ id: 'router', label: s.router.label, addr: s.router.addr, src: s.router.sources }] : []),
  ];
  const mb = (b: number) => `${nf.format(b / 1048576)} MiB`;
  return (
    <div className="adm-box">
      <p className="lls-head">
        <span className={`lls-badge ${c.state === 'ok' ? 'is-ok' : 'is-bad'}`}>{c.state === 'ok' ? '수집기 도는 중' : '수집기 주기가 멈췄다'}</span>
        <span className="adm-meta">
          {c.interval_s}초마다(모델 목록 {c.models_every_s}초) · 마지막 주기 {ago(c.tick_age_s)} · 낡음 기준 {c.stale_after_s}초 · 시작{' '}
          {new Date(c.started_at * 1000).toLocaleString()} · 저장 {mb(c.db.bytes)}
        </span>
      </p>
      {!c.enabled && (
        <p className="lls-why">infra/.env 에 LLM_STATUS 가 없다 — 손으로 띄운 수집기다. 다음 update-all 이 내린다(늘 돌리려면 LLM_STATUS=1).</p>
      )}
      {c.db.error && <p className="lls-why">저장소 — {c.db.error}</p>}
      {c.problems.map((p) => (
        <p key={p} className="lls-why">
          설정 — {p}
        </p>
      ))}
      <div className="adm-table-wrap">
        <table className="adm-table lls-sources">
          <thead>
            <tr>
              <th>원천</th>
              {Object.values(SOURCE_LABEL).map((l) => (
                <th key={l}>{l}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="adm-nowrap">
                  {r.label} {r.addr && <code className="lls-addr">{r.addr}</code>}
                </td>
                {Object.keys(SOURCE_LABEL).map((k) => {
                  const a = r.src[k];
                  return (
                    <td key={k} className={a?.stale ? 'lls-stale' : undefined} title={a?.error ?? undefined}>
                      {!a ? '—' : a.at === null ? '못 읽음' : ago(a.age_s)}
                      {a?.error && a.at !== null && <span className="lls-badge is-warn">실패</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function LlmStatusPage() {
  const { user } = useAuth();
  const isAdmin = Boolean(user?.groups.includes('portal-admin'));
  const [snap, setSnap] = useState<LlmSnapshot | null>(null);
  const [err, setErr] = useState<CollectorError | null>(null);
  const [loadedAt, setLoadedAt] = useState<number | null>(null);

  const load = useCallback(() => {
    fetchLlmStatus()
      .then((s) => {
        setSnap(s);
        setErr(null);
        setLoadedAt(Date.now());
      })
      .catch((e: unknown) => setErr(e instanceof CollectorError ? e : new CollectorError(e instanceof Error ? e.message : '불러오기 실패', 0)));
  }, []);
  useEffect(() => {
    if (!isAdmin) return;
    load();
    const id = window.setInterval(() => {
      if (document.visibilityState === 'visible') load();
    }, SNAP_EVERY_MS);
    return () => window.clearInterval(id);
  }, [isAdmin, load]);

  const targets = useMemo(() => snap?.targets ?? [], [snap]);
  const cards = targets.filter((t) => t.origin !== 'replica');
  const groups = useMemo(() => {
    const g: Record<string, LlmTarget[]> = {};
    for (const t of targets) if (t.origin === 'replica') (g[t.group ?? 'replicas'] ??= []).push(t);
    return g;
  }, [targets]);
  const mains = useMemo(() => targets.filter((t) => t.origin !== 'replica' && !t.problem).map((t) => t.id), [targets]);
  const run1h = useSeriesMap(mains, 'running', '1h', SERIES_1H_MS, isAdmin);
  const wait1h = useSeriesMap(mains, 'waiting', '1h', SERIES_1H_MS, isAdmin);
  const run24h = useSeriesMap(mains, 'running', '24h', SERIES_24H_MS, isAdmin);
  const wait24h = useSeriesMap(mains, 'waiting', '24h', SERIES_24H_MS, isAdmin);

  if (!isAdmin)
    return (
      <Page width="wide">
        <PageHeader title="LLM · GPU 현황" />
        <ErrorBanner message="관리자(portal-admin)만 볼 수 있는 페이지입니다." />
      </Page>
    );

  const ctx = snap?.context.value ?? [];
  const label = (gid: string) => targets.find((t) => t.id === gid)?.label ?? '복제본';
  return (
    <Page width="wide">
      <PageHeader
        title="LLM · GPU 현황"
        desc={
          <>
            호스트 수집기가 대상마다 15초마다 직접 읽은 상태입니다(서버 · 복제본 주소는 그 한 대, 묶음 주소는 그때 답한 한 대의 숫자). 지연의 p50 · p95 는 히스토그램
            칸으로 어림한 값이라 ≈ 를 붙입니다. 주기 세 번을 놓친 값은 <b>낡음</b>으로 보입니다.
          </>
        }
        actions={
          <>
            {loadedAt && <span className="adm-meta">받은 때 {new Date(loadedAt).toLocaleTimeString()}</span>}
            <button type="button" className="btn-secondary" onClick={load}>
              새로 고침
            </button>
          </>
        }
      />
      {err && (err.status === 502 || err.status === 503) && (
        <div className="adm-box lls-down" role="alert">
          <b>{err.status === 503 ? '수집기가 꺼져 있다' : '수집기가 답하지 않는다'}</b>
          <p className="adm-hint">{err.message}</p>
          {snap && <p className="adm-hint">아래는 마지막으로 받은 값이다{loadedAt ? `(${new Date(loadedAt).toLocaleTimeString()})` : ''}.</p>}
        </div>
      )}
      {err && err.status !== 502 && err.status !== 503 && <ErrorBanner message={err.message} />}
      {!snap && !err && <Spinner label="LLM · GPU 현황 불러오는 중…" />}
      {snap && (
        <>
          <CollectorHead s={snap} targets={targets} />
          {ctx.length > 0 && (
            <div className="adm-box lls-down" role="status">
              <b>같은 모델의 창이 서버마다 다르다</b>
              {ctx.map((d) => (
                <p key={d.model} className="adm-hint">
                  {windowsText([d], Object.keys(d.windows)[0] ?? '')}
                </p>
              ))}
            </div>
          )}
          <section className="adm-sec" aria-label="LLM 서버">
            <h2 className="lls-h2">LLM 서버</h2>
            {cards.length === 0 && (
              <p className="lls-why">
                읽을 LLM 서버가 없다 — infra/.env 에 LLM_STATUS_TARGETS · LLM_UPSTREAMS · LLM_BASE_URL · CHAT_LLM_BASE_URL 가 모두 없다.
              </p>
            )}
            <div className="lls-grid">
              {cards.map((t) => (
                <TargetCard
                  key={t.id}
                  t={t}
                  ctx={ctx}
                  sparks={
                    t.problem
                      ? null
                      : { run1h: run1h[t.id], wait1h: wait1h[t.id], run24h: run24h[t.id], wait24h: wait24h[t.id] }
                  }
                />
              ))}
            </div>
            {Object.entries(groups).map(([gid, rows]) => (
              <ReplicaTable key={gid} title={`${label(gid)} 복제본`} rows={rows} ctx={ctx} />
            ))}
          </section>
          {snap.router && <RouterSection r={snap.router} />}
          <AgentPanel a={snap.agent} />
          <StubBlock title="GPU 잡(stcx Slurm)" s={snap.slurm} />
          <StubBlock title="GPU 하드웨어" s={snap.gpu} />
        </>
      )}
    </Page>
  );
}
