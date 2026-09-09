// Report Archive 연결 카드 — RA 에서 발급한 PAT 를 등록하면 챗·심의의 보고서가 내 명의로 저장된다.
import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../api/client';

interface RaMeta {
  tail: string;
  workspace: string;
  created_at: number;
}

/** 고를 수 있는 RA 워크스페이스. personal 은 개인함이라 기본값이 되지 않는다. */
interface RaWorkspace {
  slug: string;
  name: string;
  personal: boolean;
  role?: string;
}

export function RaConnectionCard() {
  const [meta, setMeta] = useState<RaMeta | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [spaces, setSpaces] = useState<RaWorkspace[] | null>(null);

  // 후보는 **저장된 토큰으로** 서버가 RA 에 물어 온다 — 조직만 바꾸려고 PAT 를 다시
  // 붙여넣게 하지 않는다. 연결이 없으면 404 라 조용히 비운다.
  const loadSpaces = useCallback(() => {
    apiFetch('/auth/connections/reportarchive/workspaces')
      .then(async (r) => {
        if (!r.ok) return setSpaces(null);
        const b = (await r.json()) as { workspaces?: RaWorkspace[] };
        setSpaces(b.workspaces ?? []);
      })
      .catch(() => setSpaces(null));
  }, []);

  const reload = useCallback(() => {
    apiFetch('/auth/connections')
      .then(async (r) => {
        if (r.ok) {
          const conn = ((await r.json()) as { reportarchive: RaMeta | null }).reportarchive;
          setMeta(conn);
          if (conn) loadSpaces();
          else setSpaces(null);
        }
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
  }, [loadSpaces]);
  useEffect(() => reload(), [reload]);

  const changeWorkspace = async (slug: string) => {
    setBusy(true);
    setMsg(null);
    try {
      const r = await apiFetch('/auth/connections/reportarchive/workspace', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace: slug }),
      });
      const b = (await r.json().catch(() => ({}))) as {
        workspace?: string;
        workspace_name?: string;
        detail?: unknown;
      };
      if (!r.ok) throw new Error(typeof b.detail === 'string' ? b.detail : '변경에 실패했습니다.');
      setMsg({
        ok: true,
        text: b.workspace
          ? `이제 보고서가 ${b.workspace_name || b.workspace} 에 저장됩니다.`
          : '조직 지정을 해제했습니다 — RA 계정의 기본 워크스페이스로 저장됩니다.',
      });
      reload();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : '변경에 실패했습니다.' });
    } finally {
      setBusy(false);
    }
  };

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
        <>
          <p style={{ fontSize: '0.9rem' }}>
            연결됨 — 토큰 끝자리 <code>…{meta.tail}</code> ·{' '}
            {new Date(meta.created_at * 1000).toLocaleDateString()}{' '}
            <button className="btn-secondary" style={{ marginLeft: '0.6rem' }} onClick={() => void remove()} disabled={busy}>
              해제
            </button>
          </p>
          {/* 어디로 저장되는지 늘 한 줄로 보인다 — '지정 안 함'과 '조직 지정'은 다른 상태다. */}
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <label style={{ fontSize: '0.85rem' }} htmlFor="ra-ws">보고서를 저장할 조직</label>
            <select
              id="ra-ws"
              value={meta.workspace}
              disabled={busy || spaces === null}
              onChange={(e) => void changeWorkspace(e.target.value)}
              style={{
                padding: '0.35rem 0.5rem',
                border: '1px solid var(--border)',
                borderRadius: 6,
                background: 'var(--bg)',
                color: 'var(--fg)',
              }}
            >
              <option value="">지정 안 함 (RA 기본 워크스페이스)</option>
              {/* 저장된 값이 후보에 없으면(부서에서 나갔거나 RA 쪽이 바뀐 경우) 그 사실을 보인다.
                  조용히 빈칸으로 두면 어디에 쌓이는지 화면이 거짓말을 한다. */}
              {meta.workspace && !(spaces ?? []).some((w) => w.slug === meta.workspace) && (
                <option value={meta.workspace}>{meta.workspace} (지금 값 — 멤버십에 없음)</option>
              )}
              {(spaces ?? []).map((w) => (
                <option key={w.slug} value={w.slug}>
                  {w.name} ({w.slug}){w.personal ? ' · 개인함' : ''}
                </option>
              ))}
            </select>
            {spaces === null && (
              <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>목록 불러오는 중…</span>
            )}
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--muted)', margin: '0.4rem 0 0' }}>
            {meta.workspace
              ? '챗·심의가 만드는 보고서가 이 조직의 게시판에 쌓입니다.'
              : '조직을 지정하지 않으면 RA 계정의 기본 워크스페이스(대개 개인함)로 갑니다.'}
          </p>
        </>
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
