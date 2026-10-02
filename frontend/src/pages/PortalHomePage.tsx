import { useEffect, useMemo, useState } from 'react';
import { noteTileOpen } from '../api/launch.api';
import { listSystems, type SystemTile } from '../api/systems.api';
import { useAuth } from '../auth/useAuth';
import { GROUP_ORDER, groupOf } from '../components/catalog/appGroups';
import { PlatformCard } from '../components/catalog/PlatformCard';
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
          {q ? `'${query}' 에 맞는 앱이 없습니다.` : '이 분류에 쓸 수 있는 앱이 없습니다.'}{' '}
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

      {toast && <div className="toast">{toast}</div>}
    </Page>
  );
}
