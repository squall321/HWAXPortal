// 404 — 셸 안에서(헤더 유지) 다음 행동 둘을 준다
import { Link, useLocation } from 'react-router-dom';
import { Page, PageHeader } from '../components/ui/Page';

export default function NotFoundPage() {
  const { pathname } = useLocation();
  return (
    <Page>
      <PageHeader title="페이지를 찾을 수 없습니다" desc={<>주소가 바뀌었거나 없는 화면입니다 — <code>{pathname}</code></>} />
      <p style={{ display: 'flex', gap: 'var(--sp-2)' }}>
        <Link to="/" className="btn-primary" style={{ textDecoration: 'none', padding: '0.55rem 1.1rem', borderRadius: 'var(--r-md)' }}>
          챗으로
        </Link>
        <Link to="/apps" className="btn-secondary" style={{ textDecoration: 'none', padding: '0.55rem 1.1rem', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
          앱 목록
        </Link>
      </p>
    </Page>
  );
}
