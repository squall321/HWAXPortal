export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="app-shell" role="status" aria-live="polite">
      <p style={{ color: 'var(--muted)' }}>{label}</p>
    </div>
  );
}
