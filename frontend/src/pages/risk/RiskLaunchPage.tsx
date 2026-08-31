// HEAX 앱 hwax_risk(리스크 심사) 를 여는 얇은 셸 — HEAX SSO 1단, 앱 새 탭 2단
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listSystems, type SystemTile } from '../../api/systems.api';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';

// 앱 UI 경로. 포털 nginx 의 /apps/ 가 HEAX Caddy 의 /apps/ 로 그대로 넘어간다.
const APP_URL = '/apps/hwax_risk/';

// 앱 등록 여부. 타일 status 로는 판정할 수 없다 — CatalogRegistry._apply_route 가
// url 있는 handoff 타일을 항상 available 로 덮어써서 coming_soon 이 런타임에 남지 않는다.
// 2026-08-31 HEAX Hub 등록·기동 완료(SIF·Caddy 라우트·게이트웨이 흡수 실측)라 true 다.
const APP_REGISTERED = true;

export default function RiskLaunchPage() {
  const navigate = useNavigate();
  const [tile, setTile] = useState<SystemTile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 포털 카탈로그만 읽는다. 앱 REST(/apps/hwax_risk/api)는 부르지 않는다 —
  // 포털 SPA 는 heax bearer 를 갖지 않고 그 수명도 관리하지 않는다.
  useEffect(() => {
    listSystems()
      .then((systems) => setTile(systems.find((s) => s.id === 'hwax-risk') ?? null))
      .catch(() => setError('플랫폼 카탈로그를 불러오지 못했습니다.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="리스크 심사 준비 중…" />;

  const ready = APP_REGISTERED && tile !== null;
  const disabledStyle = ready ? undefined : { opacity: 0.45, cursor: 'not-allowed' };

  return (
    <div className="container" style={{ maxWidth: 720, margin: '0 auto', padding: '2rem 1.5rem' }}>
      <h1 style={{ color: 'var(--fg)', marginBottom: '0.25rem' }}>리스크 심사</h1>
      <p style={{ color: 'var(--muted)', marginTop: 0 }}>
        설계 IR·diff 위에서 전문가 패널이 리스크·개선·성격을 판정합니다. 이 화면은 앱 창을 여는
        역할만 합니다.
      </p>

      {error && <ErrorBanner message={error} />}

      {!error && !tile && (
        <ErrorBanner message="카탈로그에 리스크 심사 타일이 없습니다. 관리자에게 문의하세요." />
      )}

      {!error && tile && !ready && (
        <div
          style={{
            border: '1px solid var(--border)',
            background: 'var(--card)',
            borderRadius: 10,
            padding: '1rem 1.15rem',
            margin: '1rem 0',
            color: 'var(--muted)',
          }}
        >
          <strong style={{ color: 'var(--fg)' }}>앱 등록 전입니다.</strong>
          <p style={{ margin: '0.5rem 0 0' }}>
            리스크 심사 앱(hwax_risk)이 아직 HEAX Hub 에 등록되지 않아 지금은 열 수 없습니다. 앱이
            등록되면 아래 두 단계가 활성화됩니다.
          </p>
        </div>
      )}

      <div style={{ margin: '1.2rem 0 0.6rem' }}>
        <button
          className="btn-primary"
          disabled={!ready}
          style={disabledStyle}
          onClick={() => window.open(APP_URL, '_blank', 'noopener')}
        >
          리스크 심사 열기
        </button>
      </div>

      <p style={{ color: 'var(--muted)', fontSize: '0.88rem' }}>
        포털에 로그인하면 앱 접근 자격이 자동으로 준비됩니다. 혹시 새 탭이 401 로 막히면 아래로 한 번
        연결한 뒤 다시 여세요.
      </p>
      <button
        className="btn-secondary"
        disabled={!ready}
        style={{ ...(disabledStyle ?? {}), fontSize: '0.85rem', padding: '0.35rem 0.7rem' }}
        onClick={() => navigate('/launch/hwax-risk')}
      >
        HEAX 연결 다시 하기
      </button>
    </div>
  );
}
