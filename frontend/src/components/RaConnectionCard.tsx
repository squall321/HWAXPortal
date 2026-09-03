// Report Archive 연결 카드 — RA 에서 발급한 PAT 를 등록하면 챗·심의의 보고서가 내 명의로 저장된다.
import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../api/client';

interface RaMeta {
  tail: string;
  workspace: string;
  created_at: number;
}

export function RaConnectionCard() {
  const [meta, setMeta] = useState<RaMeta | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const reload = useCallback(() => {
    apiFetch('/auth/connections')
      .then(async (r) => {
        if (r.ok) setMeta(((await r.json()) as { reportarchive: RaMeta | null }).reportarchive);
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
  }, []);
  useEffect(() => reload(), [reload]);

  const save = async () => {
    if (!token.trim() || busy) return;
    setBusy(true);
    setMsg(null);
    try {
      const r = await apiFetch('/auth/connections/reportarchive', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token.trim() }),
      });
      const body = (await r.json().catch(() => ({}))) as {
        ok?: boolean;
        workspace_name?: string;
        workspace?: string;
        department_filled?: string;
        detail?: unknown;
      };
      if (!r.ok) {
        throw new Error(typeof body.detail === 'string' ? body.detail : '등록에 실패했습니다.');
      }
      const ws = body.workspace_name || body.workspace || '';
      setMsg({
        ok: true,
        text:
          `연결됐습니다${ws ? ` (부서: ${ws})` : ''}.` +
          (body.department_filled ? ' 포털 부서 정보도 채웠습니다.' : ''),
      });
      setToken('');
      reload();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : '등록에 실패했습니다.' });
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    setMsg(null);
    try {
      await apiFetch('/auth/connections/reportarchive', { method: 'DELETE' });
      setMsg({ ok: true, text: '연결을 해제했습니다.' });
      reload();
    } finally {
      setBusy(false);
    }
  };

  if (!loaded) return null;
  return (
    <div
      style={{
        marginTop: '2rem',
        padding: '1rem 1.2rem',
        border: '1px solid var(--border)',
        borderRadius: 8,
        background: 'var(--card)',
      }}
    >
      <h2 style={{ fontSize: '1.05rem', margin: '0 0 0.35rem' }}>Report Archive 연결</h2>
      <p style={{ color: 'var(--muted)', fontSize: '0.85rem', marginTop: 0 }}>
        Report Archive에서 발급한 토큰(<code>rat_…</code>)을 등록하면, 챗·심의가 만드는 보고서가
        공용 계정이 아니라 <b>내 RA 계정 명의</b>로 저장됩니다. RA 프로필 → 토큰 발급에서 만들어
        붙여넣으세요. 같은 이메일의 RA 계정이어야 합니다.
      </p>
      {meta ? (
        <p style={{ fontSize: '0.9rem' }}>
          연결됨 — 토큰 끝자리 <code>…{meta.tail}</code>
          {meta.workspace && <> · 부서 <b>{meta.workspace}</b></>} ·{' '}
          {new Date(meta.created_at * 1000).toLocaleDateString()}{' '}
          <button className="btn-secondary" style={{ marginLeft: '0.6rem' }} onClick={() => void remove()} disabled={busy}>
            해제
          </button>
        </p>
      ) : (
        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
          <input
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="rat_ 로 시작하는 RA 토큰 붙여넣기"
            style={{
              flex: 1,
              padding: '0.5rem 0.65rem',
              border: '1px solid var(--border)',
              borderRadius: 6,
              background: 'var(--bg)',
              color: 'var(--fg)',
            }}
          />
          <button className="btn-primary" onClick={() => void save()} disabled={busy || !token.trim()}>
            {busy ? '검증 중…' : '등록'}
          </button>
        </div>
      )}
      {msg && (
        <p style={{ fontSize: '0.85rem', color: msg.ok ? 'var(--muted)' : 'var(--danger-fg, #b91c1c)' }}>
          {msg.text}
        </p>
      )}
    </div>
  );
}
