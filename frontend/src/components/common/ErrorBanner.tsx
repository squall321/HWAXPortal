export function ErrorBanner({ message }: { message: string }) {
  return (
    <div
      role="alert"
      style={{
        background: '#3a1d1d',
        border: '1px solid #6b2b2b',
        color: '#ffd7d7',
        padding: '0.75rem 1rem',
        borderRadius: 8,
        margin: '1rem 0',
      }}
    >
      {message}
    </div>
  );
}
