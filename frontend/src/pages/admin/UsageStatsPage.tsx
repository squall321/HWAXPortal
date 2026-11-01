// 이용 통계(관리자 전용) — 포털 안 원장을 읽을 때 센 수와 그 수를 읽는 법(docs/ops-dashboard M1 · 사용자 결정 OD-4)
import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Page, PageHeader } from '../../components/ui/Page';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';
import { ColumnChart, Spark, StatTile } from '../../components/usage/UsageCharts';
import { fetchUsage, type Completion, type Section, type UsageReport } from '../../api/usage.api';
import { useAuth } from '../../auth/useAuth';
import { foldLeading, maxOf, pct, perDay, shortDay } from '../../lib/usageChart';
import '../../styles/admin.css';
import '../../styles/usage.css';

const PRESETS = [7, 30, 90, 180, 400];

const STATUS: Record<string, string> = {
  active: '쓰는 중',
  pending: '승인 대기',
  disabled: '정지',
};
const METHOD: Record<string, string> = { sso: 'SSO', local: '로컬 계정', other: '그 밖' };
const FAMILY: Record<string, string> = {
  upload: '파일 올리기',
  deck: '발표자료',
  wiki: '위키',
  card_review: '카드 대조',
  docx: '대화 내보내기',
  panel: '앱 패널',
  delib: '심의 멈춤',
  other: '그 밖',
};
const REASON: Record<string, string> = {
  agent_unreachable: '에이전트 서버에 닿지 못함',
  agent_stream_idle: '에이전트 서버가 침묵 한도를 넘김',
  max_concurrent_chats: '동시 챗 상한',
  routine_no_pat: '루틴 — 사람 토큰을 못 받음',
  as_of_unsupported: '기준일을 받지 않는 엔진',
  unknown: '까닭 칸 없음',
};
const KIND: Record<string, string> = {
  chat: '챗',
  deliberation: '심의',
  'risk-review': '리스크 심사',
};
const SOURCE: Record<string, string> = { web: '웹', mcp: 'MCP' };
const PAT_KIND: Record<string, string> = {
  personal: '사람이 낸 것',
  exchanged: '교환으로 받은 것',
};

function reasonText(r: string): string {
  const http = /^agent_(\d{3})$/.exec(r);
  return http ? `에이전트 서버 HTTP ${http[1]}` : (REASON[r] ?? r);
}

function when(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

/** 칸 하나 — 못 읽었으면 그 까닭, 아니면 내용과 읽는 법(note) */
function Block({
  sec,
  title,
  children,
}: {
  sec?: Section<unknown>;
  title?: string;
  children: ReactNode;
}) {
  return (
    <div className="uc-block">
      {title && <h3>{title}</h3>}
      {!sec ? (
        <p className="adm-hint">서버가 이 칸을 내지 않았다 — 포털이 이 화면보다 옛 판이다.</p>
      ) : sec.error ? (
        <p className="adm-err">{sec.note}</p>
      ) : (
        <>
          {children}
          <p className="uc-note">{sec.note}</p>
        </>
      )}
    </div>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="uc-card" aria-label={title}>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function Table({
  head,
  rows,
  empty = '이 기간에는 없다.',
}: {
  head: string[];
  rows: ReactNode[][];
  empty?: string;
}) {
  if (!rows.length) return <p className="uc-empty">{empty}</p>;
  return (
    <div className="adm-table-wrap">
      <table className="adm-table">
        <thead>
          <tr>
            {head.map((h, i) => (
              <th key={h} className={i ? 'adm-num' : undefined}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((cell, j) => (
                <td key={j} className={j ? 'adm-num' : undefined}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** 달마다 계정 — 원장 전 달은 한 줄로 접는다(400일이면 열 달 넘게 '기록 전' 만 늘어선다) */
function monthlyRows(
  rows: { month: string; accounts: number | null; partial: boolean }[],
): ReactNode[][] {
  const { span, rest } = foldLeading(
    rows,
    (r) => r.accounts == null,
    (r) => r.month,
  );
  return [
    ...(span ? [[span[0] === span[1] ? span[0] : `${span[0]} ~ ${span[1]}`, '기록 전']] : []),
    ...rest.map((r) => [`${r.month}${r.partial ? ' (일부만)' : ''}`, r.accounts ?? '기록 전']),
  ];
}

/** 실행 묶음(출처 · 실행기)마다 — 실행 · done · 그 밖에 끝남 · 아직 도는 것 · 완주율(끝난 것 가운데 done) */
function runRows<R extends Completion>(rows: R[], name: (r: R) => string): ReactNode[][] {
  return rows.map((r) => [
    name(r),
    r.n,
    r.done,
    r.ended - r.done,
    r.n - r.ended,
    pct(r.completion),
  ]);
}

export default function UsageStatsPage() {
  const { user } = useAuth();
  const isAdmin = Boolean(user?.groups.includes('portal-admin'));
  const [days, setDays] = useState(30);
  const [data, setData] = useState<UsageReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback((d: number) => {
    setLoading(true);
    setError(null);
    fetchUsage(d)
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '불러오기 실패'))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (isAdmin) load(30);
  }, [isAdmin, load]);

  if (!isAdmin)
    return (
      <Page width="wide">
        <PageHeader title="이용 통계" />
        <ErrorBanner message="관리자(portal-admin)만 볼 수 있는 페이지입니다." />
      </Page>
    );

  const s = data?.sections ?? {};
  const axis = data?.range.axis ?? [];
  const logins = s.logins_daily;
  const chat = s.chat_daily;
  const tiles = s.tiles;
  const conv = s.conversations;
  const livePats =
    s.pats_live && !s.pats_live.error ? s.pats_live.rows.reduce((a, r) => a + r.n, 0) : null;

  return (
    <Page width="wide">
      <PageHeader
        title="이용 통계"
        desc={
          <>
            포털 안 원장(접속 · 감사 · 계정 · 대화 · 절차 · 루틴 · PAT)을 읽을 때 셉니다. 날은 KST
            로 가르고 관리자만 봅니다. 칸마다 그 수를 읽는 법을 아래에 적었습니다 — 특히 로그인 수는
            실제로 쓴 사람보다 적습니다.
          </>
        }
      />
      <form
        className="uc-toolbar"
        onSubmit={(e) => {
          e.preventDefault();
          load(days);
        }}
      >
        <select
          id="usage-days"
          aria-label="기간"
          value={days}
          onChange={(e) => {
            const d = Number(e.target.value);
            setDays(d);
            load(d);
          }}
        >
          {PRESETS.map((d) => (
            <option key={d} value={d}>
              최근 {d}일
            </option>
          ))}
        </select>
        <button type="submit" className="btn-secondary" disabled={loading}>
          {loading ? '읽는 중…' : '다시 읽기'}
        </button>
        {data && (
          <span className="uc-meta">
            {data.range.first_day} ~ {data.range.last_day} ({data.range.days}일 · {data.range.tz}) ·{' '}
            {when(data.generated_at)} 에 셈
            {data.range.clamped &&
              ` · 요청한 ${data.range.requested_days}일을 ${data.range.days}일로 맞췄다`}
          </span>
        )}
      </form>
      {error && <ErrorBanner message={error} />}
      {!data && !error && <Spinner label="이용 통계 세는 중…" />}
      {data && (
        <div className={`uc-body${loading ? ' is-loading' : ''}`} aria-busy={loading}>
          <p className="adm-hint uc-excluded">
            {data.excluded.note}
            {data.excluded.accounts.length > 0 && (
              <> 뺀 계정 — {data.excluded.accounts.join(', ')}.</>
            )}
          </p>

          <div className="uc-tiles">
            <StatTile
              label="로그인한 계정"
              value={logins?.totals?.accounts}
              sub="기간 안 서로 다른 계정 · 로그인 기준"
            />
            <StatTile
              label="로그인"
              value={logins?.totals?.logins}
              sub={`실패 ${logins?.totals?.failures ?? '—'}`}
            />
            <StatTile
              label="챗 턴"
              value={chat?.totals?.turns}
              sub={`오류로 끝남 ${chat?.totals?.errors ?? '—'}`}
            />
            <StatTile
              label="챗을 쓴 사람"
              value={chat?.totals?.chatters}
              sub="기간 안 서로 다른 계정"
            />
            <StatTile
              label="타일 진입"
              value={tiles?.totals?.entries}
              sub={`사람 ${tiles?.totals?.accounts ?? '—'}`}
            />
            <StatTile label="살아 있는 PAT" value={livePats} sub="지금 — 폐기 · 만료 빼고" />
          </div>

          <div className="uc-grid2">
            <Card title="로그인">
              <Block sec={logins}>
                {logins && (
                  <ColumnChart
                    title="날마다 로그인한 계정(DAU · 로그인 기준)"
                    values={logins.rows.map((r) => r.accounts)}
                    labels={logins.rows.map((r) => r.day)}
                    unit="명"
                  />
                )}
              </Block>
              <Block sec={s.logins_weekly}>
                {s.logins_weekly && (
                  <ColumnChart
                    title="주마다 로그인한 계정(WAU · 월요일에 시작)"
                    values={s.logins_weekly.rows.map((r) => r.accounts)}
                    labels={s.logins_weekly.rows.map((r) => r.week)}
                    partial={s.logins_weekly.rows.map((r) => r.partial)}
                    unit="명"
                    height={80}
                  />
                )}
              </Block>
              <Block sec={s.logins_monthly} title="달마다 로그인한 계정(MAU)">
                <Table head={['달', '계정']} rows={monthlyRows(s.logins_monthly?.rows ?? [])} />
              </Block>
              <Block sec={s.logins_method} title="로그인 수단">
                <Table
                  head={['수단', '로그인', '실패', '계정']}
                  rows={(s.logins_method?.rows ?? []).map((r) => [
                    METHOD[r.method] ?? r.method,
                    r.logins,
                    r.failures,
                    r.accounts,
                  ])}
                />
              </Block>
            </Card>

            <Card title="챗">
              <Block sec={chat}>
                {chat && (
                  <ColumnChart
                    title="날마다 챗 턴(시작한 턴 — 챗 · 심의 · 띵킹 · 루틴을 가르지 않는다)"
                    values={chat.rows.map((r) => r.turns)}
                    labels={chat.rows.map((r) => r.day)}
                    unit="턴"
                  />
                )}
                {chat && (
                  <ColumnChart
                    title="날마다 챗을 쓴 사람"
                    values={chat.rows.map((r) => r.chatters)}
                    labels={chat.rows.map((r) => r.day)}
                    unit="명"
                    height={70}
                  />
                )}
              </Block>
              <Block sec={s.chat_errors} title="오류로 끝난 턴의 까닭">
                <Table
                  head={['까닭', '턴']}
                  rows={(s.chat_errors?.rows ?? []).map((r) => [reasonText(r.reason), r.n])}
                />
              </Block>
            </Card>

            <Card title="타일 진입">
              <Block sec={tiles}>
                <Table
                  head={['서비스', '진입', '사람', 'launch', 'open', '날마다']}
                  rows={(tiles?.rows ?? []).map((r) => [
                    r.label === r.service ? r.service : `${r.label} (${r.service})`,
                    r.entries,
                    r.accounts,
                    r.launch,
                    r.open,
                    <Spark
                      key="spark"
                      values={r.daily}
                      label={`${r.label} 날마다 진입 — ${shortDay(axis[0] ?? '')} ~ ${shortDay(axis[axis.length - 1] ?? '')}, 가장 많은 날 ${maxOf(r.daily)}번`}
                    />,
                  ])}
                />
              </Block>
            </Card>

            <Card title="대화">
              <Block sec={conv}>
                {conv && (
                  <ColumnChart
                    title="날마다 새 대화"
                    values={perDay(conv.rows, axis)}
                    labels={axis}
                    unit="개"
                    height={80}
                  />
                )}
                <Table
                  head={['종류 · 출처', '대화', '주인']}
                  rows={(conv?.totals ?? []).map((r) => [
                    `${KIND[r.kind] ?? r.kind} · ${SOURCE[r.source] ?? r.source}`,
                    r.n,
                    r.owners,
                  ])}
                />
              </Block>
            </Card>

            <Card title="포털 사건">
              <Block sec={s.events}>
                <Table
                  head={['갈래 · 사건', '상태', '수']}
                  rows={(s.events?.rows ?? []).map((r) => [
                    `${FAMILY[r.family] ?? r.family} · ${r.event}`,
                    r.status || '—',
                    r.n,
                  ])}
                />
              </Block>
            </Card>

            <Card title="절차 · 루틴">
              <Block
                sec={s.procedure_runs}
                title={`절차 실행 — 완주율 ${pct(s.procedure_runs?.completion?.completion)}`}
              >
                <Table
                  head={['출처', '실행', 'done', '그 밖에 끝남', '도는 중', '완주율']}
                  rows={runRows(s.procedure_runs?.rows ?? [], (r) => r.origin)}
                />
              </Block>
              <Block
                sec={s.routine_runs}
                title={`루틴 실행 — 완주율 ${pct(s.routine_runs?.completion?.completion)}`}
              >
                <Table
                  head={['실행기', '실행', 'done', '그 밖에 끝남', '도는 중', '완주율']}
                  rows={runRows(s.routine_runs?.rows ?? [], (r) => r.executor)}
                />
              </Block>
            </Card>

            <Card title="계정">
              <Block sec={s.accounts_status} title="상태(지금)">
                <Table
                  head={['상태', '계정']}
                  rows={(s.accounts_status?.rows ?? []).map((r) => [
                    STATUS[r.status] ?? r.status,
                    r.n,
                  ])}
                />
              </Block>
              <Block sec={s.accounts_affiliation} title="소속(지금)">
                <Table
                  head={['소속', '계정', '쓰는 중']}
                  rows={(s.accounts_affiliation?.rows ?? []).map((r) => [
                    r.folded ? `${r.label} (작은 소속 ${r.folded}곳)` : r.label,
                    r.n,
                    r.active,
                  ])}
                />
              </Block>
              <Block sec={s.accounts_new}>
                {s.accounts_new && (
                  <ColumnChart
                    title="주마다 새 계정"
                    values={s.accounts_new.rows.map((r) => r.n)}
                    labels={s.accounts_new.rows.map((r) => r.week)}
                    partial={s.accounts_new.rows.map((r) => r.partial)}
                    unit="개"
                    height={70}
                  />
                )}
              </Block>
            </Card>

            <Card title="PAT">
              <Block sec={s.pats_live} title="살아 있는 PAT(지금)">
                <Table
                  head={['종류', 'PAT', '주인']}
                  rows={(s.pats_live?.rows ?? []).map((r) => [
                    PAT_KIND[r.kind] ?? r.kind,
                    r.n,
                    r.owners,
                  ])}
                  empty="살아 있는 PAT 이 없다."
                />
              </Block>
              <Block sec={s.pats_weekly}>
                {s.pats_weekly && (
                  <ColumnChart
                    title="주마다 낸 PAT(원장에 남은 것만)"
                    values={s.pats_weekly.rows.map((r) => r.n)}
                    labels={s.pats_weekly.rows.map((r) => r.week)}
                    partial={s.pats_weekly.rows.map((r) => r.partial)}
                    unit="개"
                    height={70}
                  />
                )}
              </Block>
            </Card>

            <Card title="권한 수요">
              <Block sec={s.access_requests} title="권한 요청(기간 안)">
                <Table
                  head={['기능 · 플랫폼', '요청', '대기', '승인', '거절', '승인까지(중앙값)']}
                  rows={(s.access_requests?.rows ?? []).map((r) => [
                    r.label === r.key ? r.key : `${r.label} (${r.key})`,
                    r.n,
                    r.pending,
                    r.approved,
                    r.rejected,
                    r.median_hours == null ? '—' : `${r.median_hours}시간`,
                  ])}
                />
              </Block>
              <Block sec={s.connections} title="외부 연결(지금)">
                <Table
                  head={['서비스', '연결', '기간 안 등록']}
                  rows={(s.connections?.rows ?? []).map((r) => [r.service, r.n, r.new])}
                  empty="등록된 연결이 없다."
                />
              </Block>
            </Card>
          </div>
        </div>
      )}
    </Page>
  );
}
