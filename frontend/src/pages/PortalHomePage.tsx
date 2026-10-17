import { useEffect, useMemo, useState } from 'react';
import { fetchHubApps, type HubApp } from '../api/access.api';
import { noteTileOpen } from '../api/launch.api';
import { listSystems, type SystemTile } from '../api/systems.api';
import { useAuth } from '../auth/useAuth';
import { GROUP_ORDER, groupOf } from '../components/catalog/appGroups';
import { PlatformCard } from '../components/catalog/PlatformCard';
import { hubMatches } from '../components/catalog/hubSearch';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { Spinner } from '../components/common/Spinner';
import { Page, PageHeader } from '../components/ui/Page';
import '../styles/home.css';

export default function PortalHomePage() {
  const { user } = useAuth();
  const [systems, setSystems] = useState<SystemTile[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [group, setGroup] = useState<string>('전체');
  // HEAX 허브 앱(게이트웨이 앱 목록) — MaterialTwin · StepForge 같은 허브 앱은 'HEAX Hub' 타일 안에 있어 타일 검색에 안 걸렸다
  // (10-18 「MaterialTwin 이 연결 해제되었나」 문의 — 수정 제안서 F4). 검색어를 칠 때 한 번만 부른다(첫 화면마다 게이트웨이를 부르지 않게).
  const [hubApps, setHubApps] = useState<HubApp[] | null>(null);
  const [hubErr, setHubErr] = useState(false);

  useEffect(() => {
    listSystems()
      .then(setSystems)
      .catch(() => setError('앱 목록을 불러오지 못했습니다.'));
  }, []);

  const onOpen = (s: SystemTile) => {
    if (s.status === 'coming_soon') {
      setToast(`${s.name} — 곧 공개됩니다`);
      window.setTimeout(() => setToast(null), 2200);
      return;
    }
    // 모든 앱을 새 탭으로 연다 — 종전엔 토큰 핸드오프 앱만 포털 탭을 갈아치우고 나머지는 새 탭이라 사용자가 길을 잃었다
    // (docs/ui-refresh 단계 4). 핸드오프는 새 탭의 /launch 가 마친다(같은 세션 쿠키).
    if (s.integration_type === 'jwt-handoff' || s.integration_type === 'saml-handoff') {
      window.open(`/launch/${s.id}`, '_blank', 'noopener');
      return;
    }
    // 이 두 갈래는 토큰 발급 없이 곧장 연다 — 접속 원장에는 클릭만 남긴다(docs/access-history).
    noteTileOpen(s.id);
    if (s.integration_type === 'external-url' && s.url) {
      window.open(s.url, '_blank', 'noopener'); // service has its own address (own domain/port)
      return;
    }
    // proxy (default): same portal origin via nginx's /<id>/ reverse proxy — never exposes the
    // internal localhost/IP to the user's browser; the portal domain + /<id>/ always reaches it.
    window.open(`/${s.id}/`, '_blank', 'noopener');
  };

  // 분류 칩 — 있는 묶음만, 정해진 순서로
  const groups = useMemo(() => {
    const have = new Set((systems ?? []).map((s) => groupOf(s.category)));
    return GROUP_ORDER.filter((g) => have.has(g));
  }, [systems]);
  const q = query.trim().toLowerCase();
  useEffect(() => {
    if (!q || hubApps !== null || hubErr) return;
    fetchHubApps()
      .then((r) => setHubApps(r.apps))
      .catch(() => setHubErr(true));
  }, [q, hubApps, hubErr]);
  const hubShown = hubMatches(hubApps ?? [], new Set((systems ?? []).map((s) => s.id)), q);
  const openHub = (slug: string) => {
    noteTileOpen('heax-hub');
    window.open(`/heax-hub/apps/${encodeURIComponent(slug)}`, '_blank', 'noopener');
  };
  const shown = (systems ?? []).filter(
    (s) =>
      (group === '전체' || groupOf(s.category) === group) &&
      (!q ||
        [s.name, s.tagline, s.description, groupOf(s.category)].some((t) =>
          (t ?? '').toLowerCase().includes(q),
        )),
  );

  return (
    <Page width="wide" className="apps">
      <PageHeader
        title="앱"
        desc={`${user?.display_name ? `${user.display_name}님, ` : ''}사내 AI·해석 플랫폼을 한 곳에서 엽니다. 포털 로그인 그대로 들어가고, 새 탭에서 열립니다.`}
        actions={
          <input
            id="apps-search"
            type="search"
            className="apps-search"
            placeholder="앱 검색"
            aria-label="앱 검색"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        }
      />

      {/* 배선 설정 상자는 사용자 관리 맨 위로 옮겼다(헤더 '관리' 에 건수) — 모든 사람이 여는 앱 목록에 운영자 할 일을 두지 않는다 */}

      {groups.length > 1 && (
        <div className="apps-filters" role="group" aria-label="분류">
          {['전체', ...groups].map((g) => (
            <button
              key={g}
              type="button"
              className={`apps-chip${group === g ? ' is-on' : ''}`}
              aria-pressed={group === g}
              onClick={() => setGroup(g)}
            >
              {g}
              <span className="apps-chip-n">
                {g === '전체'
                  ? (systems?.length ?? 0)
                  : (systems ?? []).filter((s) => groupOf(s.category) === g).length}
              </span>
            </button>
          ))}
        </div>
      )}

      {error && <ErrorBanner message={error} />}
      {systems === null && !error ? (
        <Spinner label="앱 불러오는 중…" />
      ) : shown.length === 0 ? (
        <p className="apps-empty">
          {q
            ? hubShown.length
              ? `'${query}' 는 포털 앱에는 없고 HEAX 허브 앱에 있습니다 — 아래에서 고르면 허브에서 엽니다.`
              : `'${query}' 에 맞는 앱이 없습니다.`
            : '이 분류에 쓸 수 있는 앱이 없습니다.'}{' '}
          <button
            type="button"
            className="apps-reset"
            onClick={() => {
              setQuery('');
              setGroup('전체');
            }}
          >
            전체 보기
          </button>
        </p>
      ) : (
        <div className="apps-grid">
          {shown.map((s) => (
            <PlatformCard key={s.id} system={s} onOpen={onOpen} />
          ))}
        </div>
      )}

      {q && hubShown.length > 0 && (
        <section className="apps-hub" aria-label="HEAX 허브 앱">
          <h2 className="apps-hub-title">
            HEAX 허브 앱 <span>— HEAX Hub 안의 앱입니다. 고르면 허브의 그 앱 화면을 새 탭으로 엽니다</span>
          </h2>
          <ul className="apps-hub-list">
            {hubShown.map((a) => (
              <li key={a.app}>
                <button type="button" className="apps-hub-item" onClick={() => openHub(a.slug)}>
                  <b>{a.label}</b>
                  {a.description && <span>{a.description}</span>}
                  <em className={a.reachable ? '' : 'is-down'}>
                    {a.reachable ? `도구 ${a.tool_count}개` : '지금 연결 안 됨'}
                  </em>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      {q && hubErr && (
        <p className="apps-empty">HEAX 허브 앱 목록을 불러오지 못해 허브 앱은 검색하지 않았습니다(게이트웨이에 닿지 않음).</p>
      )}

      {toast && <div className="toast">{toast}</div>}
    </Page>
  );
}
