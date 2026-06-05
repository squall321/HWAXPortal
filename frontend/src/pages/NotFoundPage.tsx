import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <main className="app-shell" style={{ textAlign: 'center', paddingTop: '6rem' }}>
      <h1>404</h1>
      <p style={{ color: 'var(--muted)' }}>Page not found.</p>
      <Link to="/" style={{ color: 'var(--accent)' }}>
        Back to portal
      </Link>
    </main>
  );
}
