// 외부 연결 카드 — 박스 권한표의 connect: 선언마다 토큰 등록 카드를 설정대로 그린다(플랫폼 이름 · 문구가 코드에 없어 플랫폼이 늘어도 빌드가 없다, docs/ext-connect)
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch, errorDetail } from '../api/client';
import '../styles/tokenpage.css';

interface ExtMeta {
  tail: string;
  workspace?: string | null;
  created_at: number;
}

/** GET /auth/connections/ext 의 platforms[] — 주소 · 확인 주소 · 목록 자격은 오지 않는다. */
interface ExtPlatform {
  service: string;
  label: string;
  token_hint: string;
  issue: string;
  issue_url: string;
  note: string;
  verify: string;
  workspace_label: string;
  /** owner_field 를 켠 플랫폼 — '주인을 확인하지 않습니다' 가 틀린 말이 된다. 필드가 없으면(이 칸 이전 백엔드) 확인하지 않는 쪽 */
  owner_checked?: boolean;
  entitled: boolean;
  need: string;
  requestable: boolean;
  connected: ExtMeta | null;
}

/** 선언이 사라진 서비스에 남은 내 토큰 — 지우는 것만 할 수 있다. */
interface ExtOrphan {
  service: string;
  tail: string;
  created_at: number | null;
}

type Msg = { ok: boolean; text: string } | null;

const extPath = (service: string) => `/auth/connections/ext/${encodeURIComponent(service)}`;
// 설정 값이라도 javascript: 같은 주소는 링크로 만들지 않는다
const WEB_URL = /^https?:\/\//i;

function day(sec: number | null | undefined): string {
  return sec ? new Date(sec * 1000).toLocaleDateString() : '';
}

/** 지우기 — 실패를 '해제했습니다' 로 보이면 토큰이 남아 계속 그 명의로 불린다. */
async function removeConnection(service: string): Promise<void> {
  const r = await apiFetch(extPath(service), { method: 'DELETE' });
  if (!r.ok) {
    const b = (await r.json().catch(() => ({}))) as { detail?: unknown };
    throw new Error(errorDetail(b.detail, '해제에 실패했습니다.'));
  }
}

function ExtCard({ p, reload }: { p: ExtPlatform; reload: () => void }) {
  const [token, setToken] = useState('');
  const [workspace, setWorkspace] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<Msg>(null);
  const id = `ext-${p.service}`;
  const checks = p.verify !== 'none';

  const save = async () => {
    if (!token.trim() || busy) return;
    setBusy(true);
    setMsg(null);
    try {
      const r = await apiFetch(extPath(p.service), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        // 부서 칸은 선언된 플랫폼에만 보낸다 — 선언이 없는 플랫폼은 그 값을 받지 않는다
        body: JSON.stringify({ token: token.trim(), ...(p.workspace_label ? { workspace: workspace.trim() } : {}) }),
      });
      const b = (await r.json().catch(() => ({}))) as { detail?: unknown; verify?: string };
      if (!r.ok) throw new Error(errorDetail(b.detail, '등록에 실패했습니다.'));
      setMsg({
        ok: true,
        text:
          (b.verify ?? p.verify) === 'none'
            ? '저장했습니다 — 토큰을 미리 확인하지 않습니다. 틀리면 첫 호출에서 그쪽이 거절합니다.'
            : '확인하고 연결했습니다.',
      });
      setToken('');
      setWorkspace('');
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
      await removeConnection(p.service);
      setMsg({ ok: true, text: '연결을 해제했습니다.' });
      reload();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : '해제에 실패했습니다.' });
    } finally {
      setBusy(false);
    }
  };

  const c = p.connected;
  return (
    <div className="ra-card">
      <h2>{p.label} 연결</h2>
      {(p.issue || WEB_URL.test(p.issue_url)) && (
        <p className="ra-lead">
          {p.issue}
          {WEB_URL.test(p.issue_url) && (
            <>
              {p.issue ? ' ' : ''}
              <a href={p.issue_url} target="_blank" rel="noopener noreferrer">
                토큰 발급 화면 열기 ↗
              </a>
            </>
          )}
        </p>
      )}
      {p.note && <p className="ra-hint ra-note">{p.note}</p>}
      <p className="ra-notice">
        {p.owner_checked
          ? `포털 계정과 같은 이메일의 ${p.label} 계정 토큰만 연결됩니다.`
          : '이 토큰의 주인은 확인하지 않습니다 — 등록한 토큰의 계정 명의로 기록됩니다. 남의 토큰이나 HWAX 포털 토큰은 넣지 마세요.'}
      </p>
      {/* 권한을 잃었어도 남은 토큰은 보이고 지울 수 있다(백엔드가 그 사람의 행이면 지운다) */}
      {c && (
        <p className="ra-status">
          연결됨 — 토큰 끝자리 <code>…{c.tail}</code>
          {p.workspace_label && c.workspace ? ` · ${p.workspace_label} ${c.workspace}` : ''} · {day(c.created_at)}{' '}
          <button className="btn-secondary tok-btn-sm" onClick={() => void remove()} disabled={busy}>
            해제
          </button>
        </p>
      )}
      {!p.entitled ? (
        <p className="ra-hint ra-below">
          {p.requestable ? (
            <Link to={`/access?need=${encodeURIComponent(p.need)}`}>권한 요청 →</Link>
          ) : (
            '이 연결을 쓰려면 권한이 필요합니다 — 관리자에게 문의하세요.'
          )}
        </p>
      ) : (
        !c && (
          <>
            {p.workspace_label && (
              <div className="ra-row ra-ws">
                <label htmlFor={`${id}-ws`}>{p.workspace_label}</label>
                <input id={`${id}-ws`} value={workspace} onChange={(e) => setWorkspace(e.target.value)} />
              </div>
            )}
            <div className="ra-row ra-paste">
              <input
                id={`${id}-token`}
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder={`${p.token_hint} 로 시작하는 ${p.label} 토큰`}
                aria-label={`${p.label} 토큰`}
              />
              <button className="btn-primary" onClick={() => void save()} disabled={busy || !token.trim()}>
                {busy ? (checks ? '확인 중…' : '저장 중…') : '등록'}
              </button>
            </div>
          </>
        )
      )}
      {msg && <p className={`ra-msg${msg.ok ? '' : ' is-err'}`}>{msg.text}</p>}
    </div>
  );
}

function OrphanCard({ o, reload }: { o: ExtOrphan; reload: () => void }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const remove = async () => {
    setBusy(true);
    setErr('');
    try {
      await removeConnection(o.service);
      reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : '해제에 실패했습니다.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="ra-card">
      <p className="ra-status">
        더 이상 연결하지 않는 서비스(<code>{o.service}</code>) — 저장된 토큰 <code>…{o.tail}</code>
        <button className="btn-secondary tok-btn-sm" onClick={() => void remove()} disabled={busy}>
          해제
        </button>
      </p>
      {err && <p className="ra-msg is-err">{err}</p>}
    </div>
  );
}

export function ExternalConnectionCards() {
  const [data, setData] = useState<{ platforms: ExtPlatform[]; orphans: ExtOrphan[] } | null>(null);

  const reload = useCallback(() => {
    apiFetch('/auth/connections/ext')
      .then(async (r) => {
        // 404 = 이 기능 이전 백엔드 — 아무것도 그리지 않는다
        if (!r.ok) return;
        const b = (await r.json()) as { platforms?: ExtPlatform[]; orphans?: ExtOrphan[] };
        setData({ platforms: b.platforms ?? [], orphans: b.orphans ?? [] });
      })
      .catch(() => {});
  }, []);
  useEffect(() => reload(), [reload]);

  if (!data) return null;
  return (
    <>
      {data.platforms.map((p) => (
        <ExtCard key={p.service} p={p} reload={reload} />
      ))}
      {data.orphans.map((o) => (
        <OrphanCard key={o.service} o={o} reload={reload} />
      ))}
    </>
  );
}
