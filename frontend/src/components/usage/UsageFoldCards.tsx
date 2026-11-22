// 이용 통계 — 날마다 접어 둔 표의 카드: 원천을 가로지른 쓴 사람 · MCP 도구 · MCP 심의 · RA 초안 · 정문 요청 · LLM 토큰 · 사람별 이용 · 접기 상태(docs/ops-dashboard M2 · OD-52 ~ OD-55)
import type { ActiveDay, UsageSections } from '../../api/usage.api';
import { compact, maxOf, monthlyRows, msText, pct, shortDay, spanText } from '../../lib/usageChart';
import { Block, Card, Table } from './UsageBlocks';
import { ColumnChart, Spark } from './UsageCharts';

type Sections = Partial<UsageSections>;

const GROUP: [keyof ActiveDay & string, string][] = [
  ['login', '로그인'],
  ['chat', '포털 챗'],
  ['tile', '타일 진입'],
  ['mcp', 'MCP 도구'],
  ['engine', '엔진이 그 사람의 일로 부른 도구'],
  ['delib', 'MCP 심의'],
  ['nginx', '정문 요청'],
];
const LLM_KIND: Record<string, string> = {
  chat: '챗',
  think: '띵킹',
  delib: '심의',
  routine: '분석 루틴',
  card_review: '카드 대조',
  other: '그 밖',
};
const VIA: Record<string, string> = {
  pat: '개인 PAT(개인 Claude)',
  chat: '포털 챗',
  procedure: '절차 실행기',
  'mcp-app': '앱 패널',
  'gw-token': '에이전트 서버(심의 엔진)',
  service: '박스 작업',
  ticket: '그림 · 키트 받기',
  '': '(via 를 적기 전)',
};
const AUTH: Record<string, string> = {
  expired: '수명이 끝난 토큰',
  'unverified-token': '틀렸거나 검증하지 못한 토큰',
  'no-bearer': '토큰 없이 온 요청',
  'duplicate-authorization': '인증 머리가 둘',
  'bad-panel-token': '꼴이 어긋난 패널 토큰',
  'bad-service-token': '꼴이 어긋난 서비스 토큰',
  other: '그 밖',
};
const JOB_STATE: Record<string, string> = {
  done: '끝남',
  error: '오류',
  cancelled: '접음',
  interrupted: '끊김',
  running: '도는 중',
  queued: '줄 선 중',
};

function states(by: Record<string, number>): string {
  return (
    Object.entries(by)
      .sort((a, b) => b[1] - a[1])
      .map(([k, n]) => `${JOB_STATE[k] ?? k} ${n}`)
      .join(' · ') || '—'
  );
}

function when(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

/** 접지 못한 원천이 있으면 그 까닭 — 그 칸은 앞서 접은 데까지만 보인다 */
export function FoldErrors({ s }: { s: Sections }) {
  const bad = (s.fold_status?.rows ?? []).filter((r) => r.error);
  if (!bad.length) return null;
  return (
    <p className="adm-err">
      날마다 접지 못한 원천이 있다 — 그 칸은 앞서 접은 데까지만 보인다.{' '}
      {bad.map((r) => `${r.label}: ${r.error}`).join(' / ')}
    </p>
  );
}

/** 접어 둔 표에서 읽는 카드들 — 쓴 사람 · MCP 도구 · 앱/도구 · 심의/RA · 정문 */
export function FoldCards({ s, axis }: { s: Sections; axis: string[] }) {
  const active = s.active_daily;
  const mcp = s.mcp_daily;
  const delib = s.delib_jobs;
  const ra = s.ra_drafts;
  const door = s.front_door;
  return (
    <>
      <Card title="쓴 사람(원천을 가로질러)">
        <Block sec={active}>
          {active && (
            <ColumnChart
              title="날마다 쓴 사람(DAU — 로그인 · 챗 · 타일 · MCP · 심의 · 정문)"
              values={active.rows.map((r) => r.people)}
              labels={active.rows.map((r) => r.day)}
              unit="명"
            />
          )}
          <Table
            head={['갈래', '기간 안 서로 다른 계정']}
            rows={GROUP.map(([k, label]) => [label, active?.totals?.[k] ?? '—'])}
          />
        </Block>
        <Block sec={s.active_weekly}>
          {s.active_weekly && (
            <ColumnChart
              title="주마다 쓴 사람(WAU · 월요일에 시작)"
              values={s.active_weekly.rows.map((r) => r.people)}
              labels={s.active_weekly.rows.map((r) => r.week)}
              partial={s.active_weekly.rows.map((r) => r.partial)}
              unit="명"
              height={80}
            />
          )}
        </Block>
        <Block sec={s.active_monthly} title="달마다 쓴 사람(MAU)">
          <Table
            head={['달', '계정']}
            rows={monthlyRows(
              (s.active_monthly?.rows ?? []).map((r) => ({
                month: r.month,
                accounts: r.people,
                partial: r.partial,
              })),
            )}
          />
        </Block>
      </Card>

      <Card title="MCP 도구">
        <Block sec={mcp}>
          {mcp && (
            <ColumnChart
              title="날마다 MCP 도구 호출(상태 묻기 빼고)"
              values={mcp.rows.map((r) => r.calls)}
              labels={mcp.rows.map((r) => r.day)}
              unit="번"
            />
          )}
          {mcp && (
            <ColumnChart
              title="날마다 도구를 부른 사람(호출자가 적힌 줄만)"
              values={mcp.rows.map((r) => r.people)}
              labels={mcp.rows.map((r) => r.day)}
              unit="명"
              height={70}
            />
          )}
          <Table
            head={['합계', '수']}
            rows={[
              ['호출(상태 묻기 빼고)', mcp?.totals?.calls ?? '—'],
              ['상태 묻기', mcp?.totals?.status_calls ?? '—'],
              ['실패 — 앱 쪽', mcp?.totals?.errors_app ?? '—'],
              ['실패 — 관문 쪽', mcp?.totals?.errors_gate ?? '—'],
              ['캐시 적중', mcp?.totals?.cache ?? '—'],
              ['큰 응답(10만 자 이상)', mcp?.totals?.big ?? '—'],
              ['엔진이 사람의 일로 부른 호출(누구의 일 머리)', mcp?.totals?.for_calls ?? '—'],
              ['그 일의 사람(서로 다른 계정)', mcp?.totals?.people_for ?? '—'],
              ['누구의 일인지도 모르는 줄', mcp?.totals?.anon_calls ?? '—'],
            ]}
          />
        </Block>
        <Block sec={s.mcp_via} title="어느 자격으로 불렀나">
          <Table
            head={[
              '자격',
              '호출',
              '상태 묻기',
              '실패(앱 쪽)',
              '실패(관문 쪽)',
              '사람',
              '누구의 일로 이은 줄',
              '그 일의 사람',
              '이름 없는 줄',
            ]}
            rows={(s.mcp_via?.rows ?? []).map((r) => [
              r.via in VIA ? `${VIA[r.via]}${r.via ? ` (${r.via})` : ''}` : r.via,
              r.calls,
              r.status_calls,
              r.errors_app,
              r.errors_gate,
              r.people,
              r.for_calls,
              r.people_for,
              r.anon_calls,
            ])}
          />
        </Block>
        <Block sec={s.mcp_personal_weekly}>
          {s.mcp_personal_weekly && (
            <ColumnChart
              title="주마다 개인 PAT 로 도구를 부른 사람(개인 Claude)"
              values={s.mcp_personal_weekly.rows.map((r) => r.people)}
              labels={s.mcp_personal_weekly.rows.map((r) => r.week)}
              partial={s.mcp_personal_weekly.rows.map((r) => r.partial)}
              unit="명"
              height={70}
            />
          )}
        </Block>
        <Block sec={s.mcp_auth} title="/mcp 인증 실패">
          <Table
            head={['까닭', '수']}
            rows={(s.mcp_auth?.rows ?? []).map((r) => [AUTH[r.reason] ?? r.reason, r.n])}
          />
        </Block>
      </Card>

      <Card wide title="MCP 도구 — 앱 · 도구">
        <Block sec={s.mcp_apps} title="앱마다">
          <Table
            head={[
              '앱',
              '호출',
              '상태 묻기',
              '실패(앱 쪽)',
              '실패(관문 쪽)',
              '실패율',
              '캐시',
              '큰 응답',
              '도구',
              'p50',
              'p95',
            ]}
            rows={(s.mcp_apps?.rows ?? []).map((r) => [
              r.app || '(모르는 도구)',
              r.calls,
              r.status_calls,
              r.errors_app,
              r.errors_gate,
              pct(r.error_rate),
              r.cache,
              r.big,
              r.tools,
              msText(r.ms_p50),
              msText(r.ms_p95),
            ])}
          />
        </Block>
        <Block
          sec={s.mcp_tools}
          title={`많이 불린 도구(전체 ${s.mcp_tools?.total_tools ?? '—'}개 가운데)`}
        >
          <Table
            head={[
              '앱 · 도구',
              '호출',
              '실패(앱 쪽)',
              '실패(관문 쪽)',
              '실패율',
              '캐시',
              '큰 응답',
              'p50',
              'p95',
            ]}
            rows={(s.mcp_tools?.rows ?? []).map((r) => [
              `${r.app || '(모르는 도구)'} · ${r.tool}${r.status ? ' (상태 묻기)' : ''}`,
              r.calls,
              r.errors_app,
              r.errors_gate,
              pct(r.error_rate),
              r.cache,
              r.big,
              msText(r.ms_p50),
              msText(r.ms_p95),
            ])}
          />
        </Block>
      </Card>

      <Card title="MCP 심의 · RA 초안">
        <Block sec={delib}>
          {delib?.daily && (
            <ColumnChart
              title="날마다 MCP 심의 잡(줄을 서거나 돌기 시작한 날)"
              values={delib.daily}
              labels={axis}
              unit="건"
              height={80}
            />
          )}
          <Table
            head={[
              '종류',
              '잡',
              '상태',
              '보고서',
              '외부 응답자',
              '좌석(평균)',
              '라운드(평균)',
              '돈 시간(평균)',
            ]}
            rows={(delib?.rows ?? []).map((r) => [
              r.kind,
              r.n,
              states(r.states),
              r.with_report,
              r.external,
              r.seats_avg ?? '—',
              r.rounds_avg ?? '—',
              r.minutes_avg == null ? '—' : `${r.minutes_avg}분`,
            ])}
          />
          <Table
            head={['합계', '수']}
            rows={[
              ['잡', delib?.totals?.jobs ?? '—'],
              ['맡긴 사람(서로 다른 계정)', delib?.totals?.people ?? '—'],
              ['주인이 적히지 않은 잡', delib?.totals?.anon_jobs ?? '—'],
            ]}
          />
        </Block>
        <Block sec={ra} title="Report Archive 초안">
          {ra && (
            <ColumnChart
              title="날마다 RA 초안(create_report_draft 성공 호출)"
              values={ra.rows.map((r) => r.n)}
              labels={ra.rows.map((r) => r.day)}
              unit="건"
              height={80}
            />
          )}
          <Table
            head={['합계', '수']}
            rows={[
              ['초안', ra?.totals?.drafts ?? '—'],
              ['만든 사람(호출자가 적힌 초안 · 서로 다른 계정)', ra?.totals?.people ?? '—'],
              ['엔진이 사람의 일로 만든 초안(누구의 일 머리)', ra?.totals?.named_for ?? '—'],
              ['그 일의 사람(서로 다른 계정)', ra?.totals?.people_for ?? '—'],
              ['누구의 것인지 모르는 초안', ra?.totals?.unnamed ?? '—'],
              ['보고서가 붙은 MCP 심의 잡', ra?.totals?.delib_reports ?? '—'],
              ['RA 초안까지 간 루틴 실행', s.routine_runs?.ra_drafts ?? '—'],
              ...(ra?.by_via ?? []).map((r) => [`자격 — ${VIA[r.via] ?? r.via}`, r.n]),
            ]}
          />
        </Block>
      </Card>

      <Card title="LLM 토큰(에이전트 서버)">
        <Block sec={s.llm_tokens}>
          {s.llm_tokens?.daily && (
            <ColumnChart
              title="날마다 LLM 토큰(입력 + 출력)"
              values={s.llm_tokens.daily}
              labels={axis}
              unit="토큰"
              height={80}
            />
          )}
          <Table
            head={['종류 · 모델', '호출', '모름', '입력', '출력', '캐시 읽기']}
            rows={(s.llm_tokens?.rows ?? []).map((r) => [
              `${LLM_KIND[r.kind] ?? r.kind} · ${r.model}`,
              r.calls,
              r.unknown,
              compact(r.tokens_in),
              compact(r.tokens_out),
              compact(r.cache_read),
            ])}
          />
          <Table
            head={['합계', '수']}
            rows={[
              ['호출', s.llm_tokens?.totals?.calls ?? '—'],
              ['사용량을 모르는 호출', s.llm_tokens?.totals?.unknown ?? '—'],
              ['입력 토큰', s.llm_tokens?.totals ? compact(s.llm_tokens.totals.tokens_in) : '—'],
              ['출력 토큰', s.llm_tokens?.totals ? compact(s.llm_tokens.totals.tokens_out) : '—'],
              ['토큰을 쓴 사람(서로 다른 계정)', s.llm_tokens?.totals?.people ?? '—'],
            ]}
          />
        </Block>
      </Card>

      <Card title="정문 요청(허브 앱 열기)">
        <Block sec={door}>
          <Table
            head={['서비스', '요청', '날', '하루 최대 사람', '날마다']}
            rows={(door?.rows ?? []).map((r) => [
              r.label === r.service ? r.service : `${r.label} (${r.service})`,
              r.requests,
              r.days,
              r.people_max,
              <Spark
                key="spark"
                values={r.daily}
                label={`${r.label} 날마다 요청 — ${shortDay(axis[0] ?? '')} ~ ${shortDay(axis[axis.length - 1] ?? '')}, 가장 많은 날 ${maxOf(r.daily)}번`}
              />,
            ])}
          />
          <Table
            head={['합계', '수']}
            rows={[
              ['사람에게 이어진 요청', door?.totals?.requests ?? '—'],
              ['정문을 지난 사람(서로 다른 계정)', door?.totals?.people ?? '—'],
              ['이어지지 않은 요청(로그인 전 · 스캐너 · PAT)', door?.totals?.unattributed ?? '—'],
            ]}
          />
        </Block>
      </Card>
    </>
  );
}

/** 사람별 이용 — 관리자 화면에서 이메일이 나오는 유일한 카드(사용자 결정 2026-11-22 · OD-55). 다른 카드는 서로 다른 계정의 수만 낸다 */
export function PeopleCard({ s }: { s: Sections }) {
  const sec = s.people;
  return (
    <Card wide title="사람별 이용">
      <Block sec={sec}>
        <Table
          head={[
            '사람',
            '소속',
            '쓴 날',
            '로그인',
            '챗',
            '타일',
            'MCP 도구',
            '엔진(그 사람의 일)',
            'RA 초안',
            'MCP 심의',
            '정문',
            'LLM 호출',
            'LLM 입력',
            'LLM 출력',
          ]}
          rows={(sec?.rows ?? []).map((r) => [
            r.email,
            r.affiliation_label || '—',
            r.active_days,
            r.login,
            r.chat,
            r.tile,
            r.mcp,
            r.engine,
            r.ra,
            r.delib,
            r.nginx,
            r.llm_unknown ? `${r.llm_calls} (모름 ${r.llm_unknown})` : r.llm_calls,
            compact(r.llm_tokens_in),
            compact(r.llm_tokens_out),
          ])}
          empty="이 기간에 쓴 사람이 없다."
        />
        {sec?.truncated && (
          <p className="adm-hint">
            상위 {sec.rows.length}명만 보인다(전체 {sec.total}명).
          </p>
        )}
      </Block>
    </Card>
  );
}

/** 접기 상태 — 원천마다 접어 둔 범위 · 닫힌 날 · 마지막 접기 · 실패 까닭 */
export function FoldStatusCard({ s }: { s: Sections }) {
  return (
    <Card wide title="접기 상태">
      <Block sec={s.fold_status}>
        <Table
          head={[
            '원천',
            '접어 둔 날',
            '닫힌 날까지',
            '마지막 접기',
            '다른 목록으로 접은 날',
            '실패 까닭',
          ]}
          rows={(s.fold_status?.rows ?? []).map((r) => [
            r.label,
            `${spanText(r.first_day, r.last_day)}${r.days ? ` (${r.days}일)` : ''}`,
            r.closed_through ?? '—',
            r.attempt_at ? when(r.attempt_at) : '아직',
            r.other_list_days,
            r.error ?? '—',
          ])}
          empty="아직 접은 적이 없다."
        />
      </Block>
    </Card>
  );
}
