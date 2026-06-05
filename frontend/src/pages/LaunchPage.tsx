import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { launchSystem, type HandoffPayload } from '../api/launch.api';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { Spinner } from '../components/common/Spinner';

export default function LaunchPage() {
  const { systemId } = useParams<{ systemId: string }>();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [handoff, setHandoff] = useState<HandoffPayload | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (!systemId) return;
    launchSystem(systemId)
      .then((p) => {
        if (p.mode === 'redirect' && p.url) {
          // Token in the query string — navigate straight to the downstream system.
          window.location.assign(p.url);
        } else {
          setHandoff(p); // auto_post: render a hidden form and submit it (token stays out of URLs)
        }
      })
      .catch((e) => setError(e.message));
  }, [systemId]);

  // Submit the auto-POST form once it's in the DOM.
  useEffect(() => {
    if (handoff?.mode === 'auto_post') formRef.current?.submit();
  }, [handoff]);

  if (error) {
    return (
      <div className="container">
        <ErrorBanner message={error} />
        <button className="btn-secondary" onClick={() => navigate('/')}>
          Back to portal
        </button>
      </div>
    );
  }

  return (
    <div className="container">
      <Spinner label="Launching…" />
      {handoff?.mode === 'auto_post' && (
        <form ref={formRef} method="POST" action={handoff.action} style={{ display: 'none' }}>
          {Object.entries(handoff.fields).map(([k, v]) => (
            <input key={k} type="hidden" name={k} value={v} />
          ))}
        </form>
      )}
    </div>
  );
}
