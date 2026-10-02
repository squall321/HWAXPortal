import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <main className="app-shell" style={{ textAlign: 'center', paddingTop: '6rem' }}>
      <h1>페이지를 찾을 수 없습니다</h1>
      <p style={{ color: 'var(--muted)' }}>주소가 바뀌었거나 없는 화면입니다.</p>
      <p style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', marginTop: '1.5rem' }}>
        <Link to="/" className="btn-primary" style={{ textDecoration: 'none', padding: '0.55rem 1.1rem', borderRadius: 8 }}>챗으로</Link>
        <Link to="/apps" className="btn-secondary" style={{ textDecoration: 'none', padding: '0.55rem 1.1rem', borderRadius: 8, border: '1px solid var(--border)' }}>앱 목록</Link>
      </p>
    </main>
  );
}
