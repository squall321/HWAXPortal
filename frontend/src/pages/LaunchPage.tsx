import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Page, PageHeader } from '../components/ui/Page';
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
      <Page>
        <PageHeader title="앱을 열 수 없습니다" />
        {/* 서버 원문(영문)을 그대로 보이지 않는다 — 흔한 경우는 한국어로, 나머지는 원문을 함께 */}
        <ErrorBanner
          message={
            /system not found/i.test(error)
              ? '없는 앱이거나 주소가 바뀌었습니다. 앱 목록에서 다시 여세요.'
              : `앱을 여는 중 문제가 생겼습니다 — ${error}`
          }
        />
        <button className="btn-secondary" onClick={() => navigate('/apps')}>
          앱 목록으로
        </button>
      </Page>
    );
  }

  return (
    <Page>
      <Spinner label="앱을 여는 중…" />
      {handoff?.mode === 'auto_post' && (
        <form ref={formRef} method="POST" action={handoff.action} style={{ display: 'none' }}>
          {Object.entries(handoff.fields).map(([k, v]) => (
            <input key={k} type="hidden" name={k} value={v} />
          ))}
        </form>
      )}
    </Page>
  );
}
