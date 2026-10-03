// TestScope 연결 카드 — 다른 조직의 포털이라 그쪽 개인 토큰(tsc_pat_…)을 등록해 Claude·챗이 TestScope 를 내 명의로 부르게 한다.
import { useCallback, useEffect, useState } from 'react';
import { apiFetch, errorDetail } from '../api/client';
import '../styles/tokenpage.css';

interface TsMeta {
  tail: string;
  created_at: number;
}

export function TestScopeConnectionCard() {
  const [meta, setMeta] = useState<TsMeta | null>(null);
  // 켜진 박스에서만 보인다 — 필드가 없으면(이 커밋 이전 백엔드) 꺼진 것으로 읽는다.
  const [enabled, setEnabled] = useState(false);
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const reload = useCallback(() => {
    apiFetch('/auth/connections')
      .then(async (r) => {
        if (!r.ok) return;
        const b = (await r.json()) as { testscope?: TsMeta | null; testscope_enabled?: boolean };
        setEnabled(b.testscope_enabled === true);
        setMeta(b.testscope ?? null);
      })
      .catch(() => {});
  }, []);
  useEffect(() => reload(), [reload]);

  const save = async () => {
    if (!token.trim() || busy) return;
    setBusy(true);
    setMsg(null);
    try {
      const r = await apiFetch('/auth/connections/testscope', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token.trim() }),
      });
      const b = (await r.json().catch(() => ({}))) as { detail?: unknown };
      if (!r.ok) throw new Error(errorDetail(b.detail, '등록에 실패했습니다.'));
      setMsg({ ok: true, text: '연결됐습니다.' });
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
      const r = await apiFetch('/auth/connections/testscope', { method: 'DELETE' });
      // 실패를 '해제했습니다' 로 보이면 토큰이 남아 계속 내 명의로 불린다.
      if (!r.ok) {
        const b = (await r.json().catch(() => ({}))) as { detail?: unknown };
        throw new Error(errorDetail(b.detail, '해제에 실패했습니다.'));
      }
      setMsg({ ok: true, text: '연결을 해제했습니다.' });
      reload();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : '해제에 실패했습니다.' });
    } finally {
      setBusy(false);
    }
  };

  if (!enabled) return null;
  return (
    <div className="ra-card">
      <h2>TestScope 연결</h2>
      <p className="ra-lead">
        TestScope 는 다른 조직의 포털이라 그쪽에서 발급한 개인 토큰(<code>tsc_pat_…</code>)을 등록하면
        Claude·챗이 TestScope 를 <b>내 계정으로</b> 씁니다. 토큰은 TestScope 의 내 정보 › 토큰에서
        만들고, 범위는 <b>read</b>(조회)가 꼭 있어야 하며 쓰기 도구를 쓰려면 equipment:write·catalog:write
        도 고릅니다. 같은 이메일의 TestScope 계정이어야 합니다.
      </p>
      {meta ? (
        <p className="ra-status">
          연결됨 — 토큰 끝자리 <code>…{meta.tail}</code> ·{' '}
          {new Date(meta.created_at * 1000).toLocaleDateString()}{' '}
          <button className="btn-secondary tok-btn-sm" onClick={() => void remove()} disabled={busy}>
            해제
          </button>
        </p>
      ) : (
        <div className="ra-row ra-paste">
          <input
            id="ts-token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="tsc_pat_ 로 시작하는 TestScope 토큰 붙여넣기"
            aria-label="TestScope 토큰"
          />
          <button className="btn-primary" onClick={() => void save()} disabled={busy || !token.trim()}>
            {busy ? '검증 중…' : '등록'}
          </button>
        </div>
      )}
      {msg && <p className={`ra-msg${msg.ok ? '' : ' is-err'}`}>{msg.text}</p>}
    </div>
  );
}
