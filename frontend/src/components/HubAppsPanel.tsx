// 허브에 보일 앱 — 개인 Claude(Code·Desktop 등)의 허브 도구 목록·검색에서 관심 없는 앱을 끄는 표(docs/mcp-app-toggle)
import { useEffect, useState } from 'react';
import { fetchHubApps, saveHubApps, type HubApps } from '../api/access.api';

export default function HubAppsPanel() {
  const [data, setData] = useState<HubApps | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    fetchHubApps()
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  const toggle = async (app: string) => {
    if (!data || saving) return;
    const muted = new Set(data.muted);
    if (muted.has(app)) muted.delete(app);
    else muted.add(app);
    setSaving(app);
    setError(null);
    try {
      setData(await saveHubApps([...muted]));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(null);
    }
  };

  return (
    <section style={{ marginBottom: '1.75rem' }}>
      <h2 style={{ fontSize: '1.05rem', marginBottom: '0.3rem' }}>허브에 보일 앱</h2>
      <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: '0 0 0.6rem' }}>
        관심 없는 앱을 끄면 개인 Claude 의 허브 도구 목록과 도구 검색에서 빠집니다. 권한과는 별개이고, 포털 웹 챗·심의에는 영향이
        없습니다. 도구 검색은 바로 바뀌고, 열려 있는 Claude 의 도구 목록은 다시 연결해야 바뀝니다 — Claude Code 는 <code>/mcp</code>
        에서 hwax 재연결(또는 재시작), Desktop 은 완전히 종료한 뒤 다시 실행하세요.
      </p>
      {error && (
        <p role="alert" style={{ color: 'var(--danger, #b42318)', fontSize: '0.88rem', margin: '0 0 0.5rem' }}>
          {error}
        </p>
      )}
      {!data ? (
        !error && <p style={{ color: 'var(--muted)', fontSize: '0.88rem' }}>불러오는 중…</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
            <thead>
              <tr style={{ textAlign: 'left', color: 'var(--muted)' }}>
                <th style={cell}>앱</th>
                <th style={{ ...cell, textAlign: 'right' }}>도구</th>
                <th style={cell}>상태</th>
                <th style={cell}>허브에 보이기</th>
              </tr>
            </thead>
            <tbody>
              {data.apps.map((a) => (
                <tr key={a.app} style={{ borderTop: '1px solid var(--border, #e4e4e7)' }}>
                  <td style={cell} title={a.description || a.app}>
                    {a.label}
                    <span style={{ color: 'var(--muted)', fontSize: '0.78rem', marginLeft: '0.4rem' }}>{a.app}</span>
                  </td>
                  <td style={{ ...cell, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{a.tool_count}</td>
                  <td style={{ ...cell, color: 'var(--muted)' }}>
                    {a.absent ? '지금 없음' : !a.allowed ? '권한 없음' : a.reachable ? '연결됨' : '연결 끊김'}
                  </td>
                  <td style={cell}>
                    <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer' }}>
                      <input
                        id={`hub-app-${a.app}`}
                        type="checkbox"
                        checked={!a.muted}
                        disabled={saving !== null}
                        onChange={() => toggle(a.app)}
                      />
                      {saving === a.app ? '저장 중…' : a.muted ? '꺼짐' : '보임'}
                    </label>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

const cell = { padding: '0.35rem 0.5rem' } as const;
