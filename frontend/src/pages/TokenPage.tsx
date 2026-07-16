// 홈에서 AI 토큰(PAT)을 발급하고 개인 Claude 등록 스니펫을 그 자리에서 복사하는 페이지
import { type CSSProperties, type FormEvent, useEffect, useState } from 'react';
import { createPat, listPats, revokePat, type PatCreated, type PatMeta } from '../api/pat.api';
import { ErrorBanner } from '../components/common/ErrorBanner';

// 스니펫 값의 <host>는 현재 접속 중인 포털 origin을 그대로 사용한다.
const ORIGIN = window.location.origin;
const MCP_URL = `${ORIGIN}/mcp-gw/mcp`;
const CHAT_URL = `${ORIGIN}/agent/chat`;

function fmtDate(sec: number): string {
  return new Date(sec * 1000).toLocaleString('ko-KR', { dateStyle: 'medium', timeStyle: 'short' });
}

function claudeCodeSnippet(token: string): string {
  return `claude mcp add --transport http hwax ${MCP_URL} --header "Authorization: Bearer ${token}"`;
}

function claudeDesktopSnippet(token: string): string {
  return JSON.stringify(
    {
      mcpServers: {
        hwax: { type: 'http', url: MCP_URL, headers: { Authorization: `Bearer ${token}` } },
      },
    },
    null,
    2,
  );
}

function chatCurlSnippet(token: string): string {
  return [
    `curl -N -X POST ${CHAT_URL} \\`,
    `  -H "Authorization: Bearer ${token}" \\`,
    `  -H "Content-Type: application/json" \\`,
    `  -d '{"message":"안녕하세요"}'`,
  ].join('\n');
}

const preStyle: CSSProperties = {
  margin: 0,
  background: 'var(--bg)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  padding: '0.75rem',
  overflowX: 'auto',
  fontSize: '0.8rem',
  color: 'var(--fg)',
  whiteSpace: 'pre',
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
};

// 복사 버튼이 딸린 코드 블록. 각 블록이 스스로 '복사됨' 상태를 관리한다.
function CopyBlock({ label, text }: { label: string; text: string }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div style={{ marginTop: '0.9rem' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '0.35rem',
        }}
      >
        <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{label}</span>
        <button
          className="btn-secondary"
          style={{ padding: '0.25rem 0.7rem', fontSize: '0.8rem' }}
          onClick={onCopy}
        >
          {copied ? '복사됨' : '복사'}
        </button>
      </div>
      <pre style={preStyle}>{text}</pre>
    </div>
  );
}

export default function TokenPage() {
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<PatCreated | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pats, setPats] = useState<PatMeta[] | null>(null);

  const refresh = () => {
    listPats()
      .then(setPats)
      .catch(() => setError('토큰 목록을 불러오지 못했습니다.'));
  };

  useEffect(() => {
    refresh();
  }, []);

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError(null);
    try {
      // AI 접근용 PAT: audiences에 반드시 mcp-gateway를 포함해야 챗·개인 Claude MCP 둘 다 된다.
      const pat = await createPat({
        name: trimmed,
        audiences: ['mcp-gateway'],
        scopes: ['read', 'write'],
      });
      setCreated(pat);
      setName('');
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : '토큰 발급에 실패했습니다.');
    } finally {
      setBusy(false);
    }
  };

  const onRevoke = async (jti: string) => {
    setError(null);
    try {
      await revokePat(jti);
      if (created?.jti === jti) setCreated(null); // 방금 발급한 토큰을 폐기하면 표시도 지운다
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : '토큰 폐기에 실패했습니다.');
    }
  };

  return (
    <div className="container">
      <h1 style={{ fontSize: '1.4rem', marginBottom: '0.4rem' }}>AI 토큰 (PAT)</h1>
      <p style={{ color: 'var(--muted)', marginTop: 0, fontSize: '0.9rem' }}>
        개인 Claude(Claude Code · Claude Desktop)와 챗을 HWAX에 연결할 개인 접근 토큰을 발급합니다.
        토큰은 발급 직후 <b>한 번만</b> 표시되니 그 자리에서 복사해 두세요.
      </p>

      {error && <ErrorBanner message={error} />}

      <form
        onSubmit={onCreate}
        style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', margin: '1.25rem 0' }}
      >
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="토큰 이름 (예: my-laptop-claude)"
          maxLength={80}
          style={{
            flex: 1,
            padding: '0.55rem 0.8rem',
            background: 'var(--card)',
            color: 'var(--fg)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            fontSize: '0.9rem',
          }}
        />
        <button type="submit" className="btn-primary" disabled={busy || !name.trim()}>
          {busy ? '발급 중…' : '토큰 발급'}
        </button>
      </form>

      {created && (
        <section
          style={{
            background: '#3a2e14',
            border: '1px solid #6b551f',
            borderRadius: 10,
            padding: '1rem 1.1rem',
            marginBottom: '1.75rem',
          }}
        >
          <div style={{ color: '#ffe9b3', fontWeight: 600, marginBottom: '0.5rem' }}>
            지금만 보이는 토큰 — 이 화면을 벗어나면 다시 볼 수 없습니다. 반드시 복사하세요.
          </div>
          <CopyBlock label={`토큰 (${created.name})`} text={created.token} />

          <h3 style={{ color: 'var(--fg)', fontSize: '0.95rem', margin: '1.4rem 0 0' }}>
            개인 Claude에 등록
          </h3>
          <CopyBlock label="Claude Code (터미널)" text={claudeCodeSnippet(created.token)} />
          <CopyBlock
            label="Claude Desktop (claude_desktop_config.json)"
            text={claudeDesktopSnippet(created.token)}
          />

          <h3 style={{ color: 'var(--fg)', fontSize: '0.95rem', margin: '1.4rem 0 0' }}>
            챗을 토큰으로 호출 (curl)
          </h3>
          <CopyBlock label="POST /agent/chat" text={chatCurlSnippet(created.token)} />
        </section>
      )}

      <h2 style={{ fontSize: '1.05rem', marginBottom: '0.6rem' }}>내 토큰</h2>
      {pats === null ? (
        <p style={{ color: 'var(--muted)' }}>불러오는 중…</p>
      ) : pats.length === 0 ? (
        <p style={{ color: 'var(--muted)' }}>발급된 토큰이 없습니다.</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ color: 'var(--muted)', textAlign: 'left' }}>
                <th style={thStyle}>이름</th>
                <th style={thStyle}>생성</th>
                <th style={thStyle}>만료</th>
                <th style={thStyle}>jti</th>
                <th style={thStyle}></th>
              </tr>
            </thead>
            <tbody>
              {pats.map((p) => (
                <tr key={p.jti} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={tdStyle}>
                    {p.name}
                    {p.revoked && (
                      <span style={{ color: '#ffb3b3', marginLeft: '0.4rem', fontSize: '0.75rem' }}>
                        폐기됨
                      </span>
                    )}
                  </td>
                  <td style={tdStyle}>{fmtDate(p.created)}</td>
                  <td style={tdStyle}>{fmtDate(p.exp)}</td>
                  <td
                    style={{
                      ...tdStyle,
                      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                      color: 'var(--muted)',
                      wordBreak: 'break-all',
                    }}
                  >
                    {p.jti}
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>
                    {!p.revoked && (
                      <button
                        className="btn-secondary"
                        style={{ padding: '0.25rem 0.7rem', fontSize: '0.8rem' }}
                        onClick={() => void onRevoke(p.jti)}
                      >
                        폐기
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const thStyle: CSSProperties = { padding: '0.5rem 0.6rem', fontWeight: 500 };
const tdStyle: CSSProperties = { padding: '0.55rem 0.6rem', verticalAlign: 'top' };
