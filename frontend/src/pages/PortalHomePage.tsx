import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listSystems, type SystemTile } from '../api/systems.api';
import { useAuth } from '../auth/useAuth';
import { PlatformCard } from '../components/catalog/PlatformCard';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { Spinner } from '../components/common/Spinner';
import '../styles/home.css';

export default function PortalHomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [systems, setSystems] = useState<SystemTile[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    listSystems()
      .then(setSystems)
      .catch(() => setError('플랫폼 카탈로그를 불러오지 못했습니다.'));
  }, []);

  const onOpen = (s: SystemTile) => {
    if (s.status === 'coming_soon') {
      setToast(`${s.name} — 곧 공개됩니다`);
      window.setTimeout(() => setToast(null), 2200);
      return;
    }
    if (s.integration_type === 'jwt-handoff' || s.integration_type === 'saml-handoff') {
      navigate(`/launch/${s.id}`); // token handoff (Phase 4)
      return;
    }
    if (s.integration_type === 'external-url' && s.url) {
      window.open(s.url, '_blank', 'noopener'); // service has its own address (own domain/port)
      return;
    }
    // proxy (default): same portal origin via nginx's /<id>/ reverse proxy — never exposes the
    // internal localhost/IP to the user's browser; the portal domain + /<id>/ always reaches it.
    window.open(`/${s.id}/`, '_blank', 'noopener');
  };

  return (
    <div className="home">
      <section className="hero">
        <div className="hero-aurora" aria-hidden="true" />
        <div className="hero-grid" aria-hidden="true" />
        <div className="hero-inner">
          <span className="hero-kicker">HARDWARE ENGINEERING · AI TRANSFORMATION</span>
          <h1 className="hero-title">
            HWAX <span className="hero-grad">Platform Hub</span>
          </h1>
          <p className="hero-sub">
            사내 AI 자동화 시스템을 한 곳에서.
            {user?.display_name ? ` ${user.display_name}님, 환영합니다.` : ''}
          </p>
          <div className="hero-stats">
            <div>
              <b>{systems?.length ?? 6}</b>
              <span>Platforms</span>
            </div>
            <div className="sep" />
            <div>
              <b>AI-Native</b>
              <span>Workflows</span>
            </div>
          </div>
        </div>
      </section>

      <section className="home-wrap">
        <div className="section-head">
          <h2>플랫폼</h2>
          <p>원하는 시스템을 선택해 시작하세요</p>
        </div>

        {error && <ErrorBanner message={error} />}
        {systems === null && !error ? (
          <Spinner label="플랫폼 불러오는 중…" />
        ) : (
          <div className="pgrid">
            {systems?.map((s, i) => (
              <PlatformCard key={s.id} system={s} index={i} onOpen={onOpen} />
            ))}
          </div>
        )}
      </section>

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
