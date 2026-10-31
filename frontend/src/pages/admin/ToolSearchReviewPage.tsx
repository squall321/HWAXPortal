// 도구 검색 검토(관리자 전용) — 이 박스의 실사용 search_tools 질의 · 보정 표지 · 뒤이은 호출을 보고 정답을 달고 평가를 돌린다(docs/request-1029 E-9)
import { useCallback, useEffect, useState } from 'react';
import { Page, PageHeader } from '../../components/ui/Page';
import {
  fetchSearchLog,
  postSearchReview,
  runSearchEval,
  type SearchEval,
  type SearchLog,
  type SearchRow,
  type Verdict,
} from '../../api/toolSearchReview.api';
import { useAuth } from '../../auth/useAuth';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';
import '../../styles/admin.css';

const VARIANT_LABEL: Record<string, string> = {
  effective: '지금 값(덧씌운 것)',
  base: '기본값',
  off: '보정 모두 끔',
  '-synonyms': '손 동의어 끔',
  '-core_vocab': '코어 어휘표 끔',
  '-delib_narrow': '심의 좁히기 끔',
  '-quality': '품질 가중 끔',
  '-write_penalty': '쓰기 감점 끔',
  '-copy_fold': '사본 접기 끔',
};
// 평가 판의 손잡이 — 켜진 묶음은 하나씩 끈 판(-), 꺼진 손잡이(기본 끔인 비코어 낮추기 · 박스가 끈 묶음)는 하나씩 켠 판(+)으로 잰다(E-2 E2-5)
const SWITCH_LABEL: Record<string, string> = {
  synonyms: '손 동의어',
  core_vocab: '코어 어휘표',
  delib_narrow: '심의 좁히기',
  quality: '품질 가중',
  write_penalty: '쓰기 감점',
  copy_fold: '사본 접기',
  noncore_demote: '비코어 낮추기',
};

function variantLabel(name: string): string {
  const sw = SWITCH_LABEL[name.slice(1)];
  return VARIANT_LABEL[name] ?? (sw ? `${sw} ${name[0] === '+' ? '켬' : '끔'}` : name);
}
const GROUPS = ['전체', 'doc', 'auto', 'box'];

function ruleText(rule: string): string {
  const i = rule.indexOf(':');
  const kind = i < 0 ? rule : rule.slice(0, i);
  const word = i < 0 ? '' : rule.slice(i + 1);
  if (kind === 'syn') return `동의어 '${word}'`;
  if (kind === 'vocab') return `어휘표 '${word}'`;
  if (kind === 'quality') return '품질 가중';
  if (kind === 'embedding') return '의미 순위';
  if (kind === 'demote') return '비코어 낮추기(감점)';
  return rule;
}

function when(row: SearchRow): string {
  return row.ts ? new Date(row.ts * 1000).toLocaleString() : row.d;
}

function rank(r: number | null): string {
  return r ? `${r}위` : '—';
}

function pct(v: number | undefined): string {
  return v === undefined ? '—' : v.toFixed(3);
}

function MarkEditor({
  row,
  onSave,
  onCancel,
}: {
  row: SearchRow;
  onSave: (verdict: Verdict, gold: string[], memo: string) => void;
  onCancel: () => void;
}) {
  const candidates = [...new Set([...row.top, ...row.outcomes.map((o) => o.t)])];
  const [picked, setPicked] = useState<string[]>(row.mark?.gold ?? []);
  const [extra, setExtra] = useState('');
  const [memo, setMemo] = useState('');
  const gold = [...new Set([...picked, ...extra.split(/[\s,]+/).filter(Boolean)])];
  const toggle = (k: string) => setPicked((p) => (p.includes(k) ? p.filter((x) => x !== k) : [...p, k]));
  return (
    <div className="tsr-editor">
      <fieldset>
        <legend>정답 도구 — 앱키:원래 이름</legend>
        {candidates.map((k) => (
          <label key={k}>
            <input type="checkbox" checked={picked.includes(k)} onChange={() => toggle(k)} /> <code>{k}</code>
          </label>
        ))}
      </fieldset>
      <input
        id="tsr-extra"
        type="text"
        placeholder="목록에 없는 정답 — 앱키:원래 이름(여럿이면 쉼표로)"
        value={extra}
        onChange={(e) => setExtra(e.target.value)}
      />
      <input id="tsr-memo" type="text" placeholder="메모(선택)" value={memo} onChange={(e) => setMemo(e.target.value)} />
      <div className="adm-actions">
        <button type="button" className="btn-primary" disabled={!gold.length} onClick={() => onSave('gold', gold, memo)}>
          고른 것을 정답으로
        </button>
        {row.top[0] && (
          <button type="button" className="btn-secondary" onClick={() => onSave('ok', [row.top[0]], memo)}>
            1위가 맞다
          </button>
        )}
        {row.mark && (
          <button type="button" className="btn-secondary" onClick={() => onSave('remove', [], memo)}>
            표시 지우기
          </button>
        )}
        <button type="button" className="btn-secondary" onClick={onCancel}>
          닫기
        </button>
      </div>
    </div>
  );
}

function EvalResult({ ev }: { ev: SearchEval }) {
  const pc = ev.pairs;
  return (
    <div className="adm-sec">
      <h3>평가 — {ev.seconds}초</h3>
      <p className="adm-hint">
        손잡이 지문 <code>{ev.fingerprint}</code>
        {ev.fingerprint === ev.base ? ' (덧씌우기 없음)' : <> · 기본값 <code>{ev.base}</code></>} · 정답쌍 {pc.total}개 중{' '}
        {pc.measured}개를 쟀다
        {pc.missing_gold ? ` · 정답 도구가 지금 카탈로그에 없어 뺀 ${pc.missing_gold}개` : ''}. 부분문자열 순위만 재고, 실사용
        기록에는 섞지 않는다.
      </p>
      <div className="adm-table-wrap">
        <table className="adm-table tsr-eval">
          <thead>
            <tr>
              <th>판</th>
              <th>출처</th>
              <th className="adm-num">쌍</th>
              <th className="adm-num">1위 적중</th>
              <th className="adm-num">5위 안 적중</th>
              <th className="adm-num">MRR@20</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(ev.variants).flatMap(([name, by]) =>
              GROUPS.filter((g) => by[g]?.n).map((g) => (
                <tr key={`${name}-${g}`}>
                  <td>{variantLabel(name)}</td>
                  <td>{g}</td>
                  <td className="adm-num">{by[g].n}</td>
                  <td className="adm-num">{pct(by[g]['hit@1'])}</td>
                  <td className="adm-num">{pct(by[g]['hit@5'])}</td>
                  <td className="adm-num">{pct(by[g]['mrr@20'])}</td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>
      {ev.changed_count > 0 && (
        <>
          <h3>판마다 정답 순위가 다른 쌍 — {ev.changed_count}개</h3>
          <div className="adm-table-wrap">
            <table className="adm-table tsr-eval">
              <thead>
                <tr>
                  <th>질의</th>
                  <th>출처</th>
                  <th className="adm-num">지금 값</th>
                  <th className="adm-num">기본값</th>
                  <th className="adm-num">보정 끔</th>
                </tr>
              </thead>
              <tbody>
                {ev.changed.map((c) => (
                  <tr key={c.id}>
                    <td>{c.query}</td>
                    <td>{c.source ?? '—'}</td>
                    <td className="adm-num">{rank(c.effective)}</td>
                    <td className="adm-num">{rank(c.base)}</td>
                    <td className="adm-num">{rank(c.off)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {ev.changed_count > ev.changed.length && (
            <p className="adm-hint">앞의 {ev.changed.length}개만 보인다 — 전부는 게이트웨이의 run.py live --detail 로.</p>
          )}
        </>
      )}
    </div>
  );
}

export default function ToolSearchReviewPage() {
  const { user } = useAuth();
  const isAdmin = user?.groups.includes('portal-admin');
  const [q, setQ] = useState('');
  const [days, setDays] = useState(7);
  const [limit, setLimit] = useState(200);
  const [log, setLog] = useState<SearchLog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [ev, setEv] = useState<SearchEval | null>(null);
  const [evaluating, setEvaluating] = useState(false);

  const load = useCallback((f: { q: string; days: number; limit: number }) => {
    setError(null);
    fetchSearchLog(f)
      .then(setLog)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '불러오기 실패'));
  }, []);
  useEffect(() => {
    if (isAdmin) load({ q: '', days: 7, limit: 200 });
  }, [isAdmin, load]);

  if (!isAdmin)
    return (
      <Page width="wide">
        <PageHeader title="도구 검색 검토" />
        <ErrorBanner message="관리자(portal-admin)만 볼 수 있는 페이지입니다." />
      </Page>
    );

  const save = (row: SearchRow, verdict: Verdict, gold: string[], memo: string) => {
    setError(null);
    postSearchReview({ q: row.q, verdict, gold, memo, qid: row.id ?? null })
      .then(() => {
        setOpen(null);
        load({ q, days, limit });
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '표시 저장 실패'));
  };
  const evaluate = () => {
    setEvaluating(true);
    setError(null);
    runSearchEval()
      .then(setEv)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '평가 실패'))
      .finally(() => setEvaluating(false));
  };

  return (
    <Page width="wide">
      <PageHeader
        title="도구 검색 검토"
        desc={
          <>
            이 박스 게이트웨이가 모은 실사용 search_tools 질의입니다. 상위 다섯마다 보정(동의어 · 어휘표 · 품질 가중)이 보탠 규칙과,
            찾은 뒤 600초 안에 같은 사람이 부른 도구를 함께 봅니다(부른 사람은 기록하지 않습니다). 정답 표시는 이 박스의 정답쌍에
            남고, <b>평가 돌리기</b>가 그 정답으로 손잡이를 판마다 잽니다.
          </>
        }
        actions={
          <button type="button" className="btn-secondary" onClick={evaluate} disabled={evaluating}>
            {evaluating ? '평가 중…' : '평가 돌리기'}
          </button>
        }
      />
      {error && <ErrorBanner message={error} />}
      {ev && <EvalResult ev={ev} />}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          load({ q, days, limit });
        }}
        className="adm-filter"
      >
        <input id="tsr-q" placeholder="질의에 든 글" value={q} onChange={(e) => setQ(e.target.value)} />
        <select id="tsr-days" value={days} onChange={(e) => setDays(Number(e.target.value))}>
          {[1, 7, 14, 30].map((d) => (
            <option key={d} value={d}>
              최근 {d}일
            </option>
          ))}
        </select>
        <select id="tsr-limit" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
          {[100, 200, 500, 1000].map((n) => (
            <option key={n} value={n}>
              {n}개까지
            </option>
          ))}
        </select>
        <button type="submit" className="btn-secondary">
          조회
        </button>
        {log && (
          <span className="adm-hint">
            질의 {log.count}개 · 손잡이 지문 <code>{log.fingerprint}</code>
          </span>
        )}
      </form>

      {!log && !error && <Spinner label="검색 기록 불러오는 중…" />}
      {log && (
        <div className="adm-table-wrap">
          <table className="adm-table tsr-log">
            <thead>
              <tr>
                <th>시각</th>
                <th>질의</th>
                <th>상위 다섯</th>
                <th>뒤이은 호출</th>
                <th>표시</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {log.searches.flatMap((row, i) => {
                const called = new Set(row.outcomes.map((o) => o.t));
                const boost = new Set(row.boost_only ?? []);
                const main = (
                  <tr key={`${row.id ?? row.d}-${i}`}>
                    <td className="adm-nowrap">{when(row)}</td>
                    <td>{row.q}</td>
                    <td>
                      <ol className="tsr-top">
                        {row.top.map((k) => (
                          <li key={k}>
                            <code>{k}</code>
                            {boost.has(k) && <span className="tsr-tag is-boost">보정 덕에만</span>}
                            {called.has(k) && <span className="tsr-tag is-called">불림</span>}
                            {row.via?.[k] && <span className="tsr-rules"> · {row.via[k].map(ruleText).join(' · ')}</span>}
                          </li>
                        ))}
                      </ol>
                    </td>
                    <td>
                      {row.outcomes.length === 0 ? (
                        <span className="adm-muted-cell">—</span>
                      ) : (
                        <ul className="tsr-top">
                          {row.outcomes.map((o) => (
                            <li key={o.t}>
                              <code>{o.t}</code> {o.r ? `${o.r}위` : <span className="tsr-tag is-miss">결과에 없었음</span>}
                              {!o.ok && <span className="tsr-tag is-fail">실패</span>}
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                    <td>
                      {row.mark ? (
                        <>
                          {row.mark.verdict === 'ok' ? '1위 맞음' : '정답'} — {row.mark.gold.join(', ')}
                        </>
                      ) : (
                        <span className="adm-muted-cell">—</span>
                      )}
                    </td>
                    <td className="adm-nowrap">
                      <button type="button" className="btn-secondary" onClick={() => setOpen(open === i ? null : i)}>
                        정답 달기
                      </button>
                    </td>
                  </tr>
                );
                if (open !== i) return [main];
                return [
                  main,
                  <tr key={`${row.id ?? row.d}-${i}-edit`}>
                    <td colSpan={6}>
                      <MarkEditor
                        row={row}
                        onSave={(v, g, m) => save(row, v, g, m)}
                        onCancel={() => setOpen(null)}
                      />
                    </td>
                  </tr>,
                ];
              })}
            </tbody>
          </table>
          {log.searches.length === 0 && <p className="adm-hint">이 조건의 질의가 없습니다.</p>}
        </div>
      )}
    </Page>
  );
}
