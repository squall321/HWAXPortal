// 전문가 고르기 검토(관리자 전용) — 실사용 첫 발화에 맡을 전문가를 사람이 단다 · 순위 · 점수 · 지금 좌석은 보이지 않는다(docs/request-1029 E-5 · E5-2)
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Page, PageHeader } from '../../components/ui/Page';
import {
  fetchSeatCard,
  fetchSeatCatalog,
  fetchSeatItems,
  postSeatLabel,
  runSeatCollect,
  SEAT_SOURCES,
  SOURCE_LABEL,
  type CollectResult,
  type NoneKind,
  type SeatCard,
  type SeatExpert,
  type SeatItem,
  type SeatLabelBody,
  type SeatSource,
  type SeatView,
  type Via,
} from '../../api/seatReview.api';
import { useAuth } from '../../auth/useAuth';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';
import { OrgCrumb, OrgTreeNav } from '../../components/chat/OrgTree';
import { useOrgNav } from '../../components/chat/orgNav';
import '../../styles/chat.css';
import '../../styles/admin.css';

const PAGE = 100;
const PRIMARY_MAX = 3;
const ALSO_MAX = 5;
const FILTERED_LABEL: Record<string, string> = {
  short: '8자 아래',
  not_standalone: '홀로 서지 않는 발화',
  near_dup: '겹침(3글자 조각 0.8 이상)',
};

type Kind = 'experts' | NoneKind | 'unsure';
type Role = 'primary' | 'also';
interface Chosen {
  key: string;
  role: Role;
  via: Via;
}

function markText(m: SeatItem['mine'], names: Map<string, string>): string {
  if (!m) return '—';
  if (m.unsure) return '모르겠음';
  if (m.none === 'core_data') return '없음 — 코어 데이터';
  if (m.none === 'out_of_pool') return '없음 — 풀 밖';
  const nm = (k: string) => names.get(k) ?? k;
  return [
    `주 ${m.primary.map(nm).join(', ')}`,
    ...(m.also.length ? [`같이 ${m.also.map(nm).join(', ')}`] : []),
  ].join(' · ');
}

/** 고른 전문가 — 조직도에서(tree) 골랐나 · 이름 찾기 칸에서(search) 골랐나를 함께 적는다(design-e5 2.4). */
function ExpertPicker({
  pool,
  picks,
  onPick,
}: {
  pool: SeatExpert[];
  picks: Chosen[];
  onPick: (key: string, role: Role, via: Via) => void;
}) {
  const roster = useMemo(
    () => pool.map((e) => ({ key: e.key, name: e.name, tags: [] as string[] })),
    [pool],
  );
  const nav = useOrgNav(roster);
  const [card, setCard] = useState<SeatCard | null>(null);
  const [cardErr, setCardErr] = useState<string | null>(null);
  const via: Via = nav.q.trim() ? 'search' : 'tree';
  const chosen = new Map(picks.map((p) => [p.key, p.role]));
  const nPrimary = picks.filter((p) => p.role === 'primary').length;
  const nAlso = picks.length - nPrimary;
  const open = (key: string) => {
    setCardErr(null);
    setCard(null);
    fetchSeatCard(key)
      .then(setCard)
      .catch((e: unknown) => setCardErr(e instanceof Error ? e.message : '카드 불러오기 실패'));
  };
  return (
    <div className="srv-picker">
      <OrgTreeNav nav={nav} total={pool.length} />
      <div className="srv-pick-main">
        <input
          className="srv-search"
          type="text"
          value={nav.q}
          onChange={(e) => nav.setQ(e.target.value)}
          placeholder="이름 · 키로 찾기(찾아서 고르면 '찾음' 으로 적힌다)"
          aria-label="전문가 이름 찾기"
        />
        {nav.q.trim() || nav.node ? (
          <>
            <OrgCrumb nav={nav} />
            {nav.shown.length === 0 ? (
              <p className="adm-hint">일치하는 전문가가 없습니다.</p>
            ) : (
              <ul className="srv-experts">
                {nav.shown.map((a) => {
                  const role = chosen.get(a.key);
                  return (
                    <li key={a.key} className={role ? 'is-on' : ''}>
                      <button
                        type="button"
                        className="srv-name"
                        onClick={() => open(a.key)}
                        title="설명 보기"
                      >
                        {a.name} <code>{a.key}</code>
                      </button>
                      <span className="srv-pick-btns">
                        <button
                          type="button"
                          className="btn-secondary"
                          disabled={
                            role === 'primary' || (role !== 'also' && nPrimary >= PRIMARY_MAX)
                          }
                          onClick={() => onPick(a.key, 'primary', via)}
                        >
                          주
                        </button>
                        <button
                          type="button"
                          className="btn-secondary"
                          disabled={role === 'also' || (role !== 'primary' && nAlso >= ALSO_MAX)}
                          onClick={() => onPick(a.key, 'also', via)}
                        >
                          같이
                        </button>
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </>
        ) : (
          <p className="adm-hint">왼쪽 조직도에서 분야를 고르거나 이름으로 찾습니다.</p>
        )}
      </div>
      <aside className="srv-card" aria-label="전문가 설명">
        {cardErr && <p className="adm-err">{cardErr}</p>}
        {!card && !cardErr && <p className="adm-hint">이름을 누르면 설명이 여기 보입니다.</p>}
        {card && (
          <>
            <div className="srv-card-name">{card.name}</div>
            <code>{card.key}</code>
            <p>
              {card.desc || (card.error ? '설명을 받지 못했습니다.' : '설명이 없는 전문가입니다.')}
            </p>
          </>
        )}
      </aside>
    </div>
  );
}

function MarkEditor({
  item,
  pool,
  names,
  onSave,
  onCancel,
}: {
  item: SeatItem;
  pool: SeatExpert[];
  names: Map<string, string>;
  onSave: (body: SeatLabelBody) => void;
  onCancel: () => void;
}) {
  const m = item.mine;
  const [kind, setKind] = useState<Kind>(m?.unsure ? 'unsure' : (m?.none ?? 'experts'));
  const [picks, setPicks] = useState<Chosen[]>(() =>
    m
      ? [
          ...m.primary.map((k) => ({ key: k, role: 'primary' as Role, via: m.via[k] ?? 'tree' })),
          ...m.also.map((k) => ({ key: k, role: 'also' as Role, via: m.via[k] ?? 'tree' })),
        ]
      : [],
  );
  const [memo, setMemo] = useState(m?.memo ?? '');
  const pick = (key: string, role: Role, via: Via) =>
    setPicks((ps) => [...ps.filter((p) => p.key !== key), { key, role, via }]);
  const drop = (key: string) => setPicks((ps) => ps.filter((p) => p.key !== key));
  const primary = picks.filter((p) => p.role === 'primary').map((p) => p.key);
  const also = picks.filter((p) => p.role === 'also').map((p) => p.key);
  const canSave =
    kind !== 'experts' ||
    (primary.length >= 1 && primary.length <= PRIMARY_MAX && also.length <= ALSO_MAX);
  const save = () =>
    onSave(
      kind === 'experts'
        ? {
            qid: item.qid,
            primary,
            also,
            via: Object.fromEntries(picks.map((p) => [p.key, p.via])),
            memo,
          }
        : kind === 'unsure'
          ? { qid: item.qid, unsure: true, memo }
          : { qid: item.qid, none: kind, memo },
    );
  const KINDS: [Kind, string][] = [
    ['experts', '맡을 전문가'],
    ['core_data', '없음 — 코어 데이터(정본 허브에서 조회할 질문)'],
    ['out_of_pool', '없음 — 풀 밖(맡을 사람이 풀에 없다)'],
    ['unsure', '모르겠음(빼고 센다)'],
  ];
  return (
    <div className="srv-editor">
      <fieldset className="srv-kinds">
        <legend>표시</legend>
        {KINDS.map(([k, label]) => (
          <label key={k}>
            <input
              type="radio"
              name={`srv-kind-${item.qid}`}
              checked={kind === k}
              onChange={() => setKind(k)}
            />{' '}
            {label}
          </label>
        ))}
      </fieldset>
      {kind === 'experts' && (
        <>
          <div className="srv-chips" aria-label="고른 전문가">
            {picks.length === 0 && (
              <span className="adm-hint">
                주 전문가 1 ~ 3명 · 같이 맡을 만한 전문가 0 ~ 5명을 고릅니다.
              </span>
            )}
            {picks.map((p) => (
              <span key={p.key} className={`srv-chip is-${p.role}`}>
                {p.role === 'primary' ? '주' : '같이'} · {names.get(p.key) ?? p.key}
                {p.via === 'search' && <span className="srv-via"> · 찾음</span>}
                <button
                  type="button"
                  onClick={() => drop(p.key)}
                  aria-label={`${names.get(p.key) ?? p.key} 빼기`}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
          <ExpertPicker pool={pool} picks={picks} onPick={pick} />
        </>
      )}
      <input
        className="srv-memo"
        type="text"
        maxLength={300}
        placeholder="메모(선택 — 300자)"
        value={memo}
        onChange={(e) => setMemo(e.target.value)}
      />
      <div className="adm-actions">
        <button type="button" className="btn-primary" disabled={!canSave} onClick={save}>
          저장
        </button>
        {m && (
          <button
            type="button"
            className="btn-secondary"
            onClick={() => onSave({ qid: item.qid, remove: true })}
          >
            내 표시 지우기
          </button>
        )}
        <button type="button" className="btn-secondary" onClick={onCancel}>
          닫기
        </button>
      </div>
    </div>
  );
}

export default function SeatReviewPage() {
  const { user } = useAuth();
  const isAdmin = user?.groups.includes('portal-admin');
  const [src, setSrc] = useState<SeatSource | ''>('');
  const [offset, setOffset] = useState(0);
  const [view, setView] = useState<SeatView | null>(null);
  const [pool, setPool] = useState<SeatExpert[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [collecting, setCollecting] = useState(false);
  const [collected, setCollected] = useState<CollectResult | null>(null);
  const names = useMemo(() => new Map(pool.map((e) => [e.key, e.name])), [pool]);

  const load = useCallback((f: { src: SeatSource | ''; offset: number }) => {
    setError(null);
    fetchSeatItems({ ...f, limit: PAGE })
      .then(setView)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '불러오기 실패'));
  }, []);
  useEffect(() => {
    if (!isAdmin) return;
    load({ src: '', offset: 0 });
    fetchSeatCatalog()
      .then(setPool)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : '전문가 명부 불러오기 실패'),
      );
  }, [isAdmin, load]);

  if (!isAdmin)
    return (
      <Page width="wide">
        <PageHeader title="전문가 고르기 검토" />
        <ErrorBanner message="관리자(portal-admin)만 볼 수 있는 페이지입니다." />
      </Page>
    );

  const save = (body: SeatLabelBody) => {
    setError(null);
    postSeatLabel(body)
      .then(() => {
        setOpen(null);
        load({ src, offset });
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '표시 저장 실패'));
  };
  const collect = () => {
    setCollecting(true);
    setError(null);
    runSeatCollect()
      .then((r) => {
        setCollected(r);
        load({ src, offset: 0 });
        setOffset(0);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '모으기 실패'))
      .finally(() => setCollecting(false));
  };
  const go = (f: { src: SeatSource | ''; offset: number }) => {
    setSrc(f.src);
    setOffset(f.offset);
    setOpen(null);
    load(f);
  };

  return (
    <Page width="wide">
      <PageHeader
        title="전문가 고르기 검토"
        desc={
          <>
            이 박스에서 사람이 처음 꺼낸 질문(전문가를 지목한 챗의 첫 발화 · 띵킹 질문 · 사람이
            좌석을 고른 심의의 화두 · &apos;/전문가&apos; 질의)에 맡을 전문가를 답니다. 이름 · 메일
            · 대화 id 는 떼었고, 시스템의 추천 순위 · 점수 · 지금 앉은 좌석은 보이지 않습니다 — 보고
            고르면 정답이 시스템을 따라갑니다. 표시는 이 박스 에이전트 서버의 박스 파일에만 남고,
            전문가 고르기 기준선(B0)이 정답으로 씁니다.
          </>
        }
        actions={
          <button
            type="button"
            className="btn-secondary"
            onClick={collect}
            disabled={collecting || !view?.collect.on}
            title={
              view?.collect.on
                ? '켜기 전의 날들을 이 박스 대화 저장소에서 떼어 넣는다(같은 글은 겹치지 않는다)'
                : '모으기가 꺼져 있다'
            }
          >
            {collecting ? '모으는 중…' : '지난 날 모으기'}
          </button>
        }
      />
      {error && <ErrorBanner message={error} />}
      {view && (
        <div className="adm-box">
          <p className="adm-note">
            모으기 —{' '}
            {view.collect.on ? (
              <b>켜짐(최근 {view.collect.days ?? '?'}일)</b>
            ) : (
              <>
                꺼짐 · 사용자 허락을 받은 박스에서만 에이전트 서버 env 에{' '}
                <code>SEAT_QUESTIONS_COLLECT=1</code> 을 적고 다시 띄웁니다
              </>
            )}{' '}
            · 후보{' '}
            {SEAT_SOURCES.map((s) => `${SOURCE_LABEL[s]} ${view.counts[s] ?? 0}`).join(' · ')}
            {Object.keys(view.filtered).length > 0 &&
              ` · 뺀 것 ${Object.entries(view.filtered)
                .map(([k, n]) => `${FILTERED_LABEL[k] ?? k} ${n}`)
                .join(' · ')}`}
          </p>
          <p className="adm-note">
            {view.me.can_label ? (
              <>
                다는 이름 <code>{view.me.by}</code> · 내가 단 것 {view.labeled.mine ?? 0}건 · 누군가
                단 질문 {view.labeled.any}건 — 한 사람이 190건(맡은 질문 150 · 맡은 사람이 없는 질문
                40)을, 다른 한 사람이 그 가운데 30건을 서로 보지 않고 겹쳐 답니다.
              </>
            ) : (
              <>
                이 계정(<code>{view.me.by ?? '—'}</code>)은 정답을 다는 사람이 아니라 보기만 합니다
                — 다는 사람은 사람이 정해 에이전트 서버 env 의 <code>SEAT_QUESTIONS_LABELERS</code>{' '}
                에 메일(소문자)로 적습니다.
              </>
            )}
            {!view.labelers_set &&
              ' ⚠ 다는 사람이 정해지지 않아 지금은 관리자 누구나 달 수 있습니다.'}
          </p>
          {collected && (
            <p className="adm-note">
              지난 날 모으기 — 대화 저장소에서 {collected.harvest.sent}건을 넣었다(최근{' '}
              {collected.harvest.days}일 · 이름 · 메일을 가린 것 {collected.harvest.scrubbed}건) →
              새로 든 것 {collected.agent.added} · 이미 있던 것 {collected.agent.dup} · 창 밖{' '}
              {collected.agent.old} · 짧은 것 {collected.agent.short}.
            </p>
          )}
        </div>
      )}

      <div className="adm-filter">
        <select
          id="srv-src"
          value={src}
          onChange={(e) => go({ src: e.target.value as SeatSource | '', offset: 0 })}
        >
          <option value="">출처 전부</option>
          {SEAT_SOURCES.map((s) => (
            <option key={s} value={s}>
              {SOURCE_LABEL[s]}
            </option>
          ))}
        </select>
        {view && (
          <span className="adm-hint">
            {view.total}건 중 {view.total ? offset + 1 : 0} ~ {Math.min(offset + PAGE, view.total)}
          </span>
        )}
        <button
          type="button"
          className="btn-secondary"
          disabled={offset === 0}
          onClick={() => go({ src, offset: Math.max(0, offset - PAGE) })}
        >
          이전
        </button>
        <button
          type="button"
          className="btn-secondary"
          disabled={!view || offset + PAGE >= view.total}
          onClick={() => go({ src, offset: offset + PAGE })}
        >
          다음
        </button>
      </div>

      {!view && !error && <Spinner label="질문 불러오는 중…" />}
      {view && (
        <div className="adm-table-wrap">
          <table className="adm-table srv-table">
            <thead>
              <tr>
                <th>날짜</th>
                <th>출처</th>
                <th>질문</th>
                <th>내 표시</th>
                <th className="adm-num">다른 표시</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {view.items.flatMap((it) => {
                const row = (
                  <tr key={it.qid}>
                    <td className="adm-nowrap">{it.d ?? '—'}</td>
                    <td className="adm-nowrap">{SOURCE_LABEL[it.src]}</td>
                    <td className="srv-q">{it.text}</td>
                    <td>
                      {it.mine ? (
                        markText(it.mine, names)
                      ) : (
                        <span className="adm-muted-cell">—</span>
                      )}
                    </td>
                    <td className="adm-num">{it.others}</td>
                    <td className="adm-nowrap">
                      <button
                        type="button"
                        className="btn-secondary"
                        disabled={!view.me.can_label}
                        onClick={() => setOpen(open === it.qid ? null : it.qid)}
                      >
                        표시 달기
                      </button>
                    </td>
                  </tr>
                );
                if (open !== it.qid) return [row];
                return [
                  row,
                  <tr key={`${it.qid}-edit`}>
                    <td colSpan={6}>
                      <MarkEditor
                        item={it}
                        pool={pool}
                        names={names}
                        onSave={save}
                        onCancel={() => setOpen(null)}
                      />
                    </td>
                  </tr>,
                ];
              })}
            </tbody>
          </table>
          {view.items.length === 0 && (
            <p className="adm-hint">
              {view.collect.on
                ? '아직 모인 질문이 없습니다 — 지난 날 모으기를 누르거나 쓰이기를 기다립니다.'
                : '모인 질문이 없습니다.'}
            </p>
          )}
        </div>
      )}
    </Page>
  );
}
