// Report Archive 연결 카드 — 위임(sso)이면 포털 로그인으로 본인 명의라 안내만, 아니면 RA PAT 를 등록해 챗·심의의 보고서를 내 명의로 저장한다.
import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../api/client';
import '../styles/tokenpage.css';

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

/** sso = 포털·게이트웨이가 공유 비밀로 그 사람의 RA 토큰을 그때그때 받는다(ste 방식) — 붙여넣을 것이 없다.
 *  필드가 없으면(이 커밋 이전 백엔드) token 이다 — 위임이 켜졌다고 단정하면 등록 칸이 사라진다. */
type RaMode = 'sso' | 'token';

export function RaConnectionCard() {
  const [meta, setMeta] = useState<RaMeta | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [spaces, setSpaces] = useState<RaWorkspace[] | null>(null);
  const [mode, setMode] = useState<RaMode>('token');

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
          const b = (await r.json()) as {
            reportarchive: RaMeta | null;
            reportarchive_mode?: RaMode;
          };
          const conn = b.reportarchive;
          const m: RaMode = b.reportarchive_mode === 'sso' ? 'sso' : 'token';
          setMode(m);
          setMeta(conn);
          // 위임이면 조직 고르기를 보이지 않으니 후보도 RA 에 묻지 않는다.
          if (conn && m === 'token') loadSpaces();
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
      // 위임에서 '연결을 해제했습니다' 라고 하면 RA 가 끊긴 것으로 읽힌다 — 지운 것은 옛 토큰뿐이다.
      setMsg({ ok: true, text: mode === 'sso' ? '예전 토큰을 지웠습니다.' : '연결을 해제했습니다.' });
      reload();
    } finally {
      setBusy(false);
    }
  };

  if (!loaded) return null;
  // 위임 — 붙여넣기·조직 고르기를 숨긴다. 부서는 RA 가 그 사람 프로필(홈 부서)로 정한다(docs/sso-delegation).
  if (mode === 'sso')
    return (
      <div className="ra-card">
        <h2>Report Archive 연결</h2>
        <p className="ra-auto">
          Report Archive 는 <b>포털 로그인으로 본인 명의</b>로 연결됩니다 — 등록할 것이 없습니다.
          보고서는 RA 에서 고른 내 부서에 쌓입니다(부서는 RA 에서 바꿉니다).
        </p>
        {/* 옛 토큰이 남아 있으면 그 사실을 보인다 — 안 보이면 '아직 그 토큰으로 부르나?' 를 알 길이 없다. */}
        {meta ? (
          <p className="ra-status">
            예전에 등록한 토큰(<code>…{meta.tail}</code>) — 지금은 쓰지 않습니다
            <button className="btn-secondary tok-btn-sm" onClick={() => void remove()} disabled={busy}>
              해제
            </button>
          </p>
        ) : (
          <p className="ra-hint ra-below">
            RA 토큰(<code>rat_…</code>)을 붙여 넣던 예전 방식은 쓰지 않습니다.
          </p>
        )}
        {msg && <p className={`ra-msg${msg.ok ? '' : ' is-err'}`}>{msg.text}</p>}
      </div>
    );
  return (
    <div className="ra-card">
      <h2>Report Archive 연결</h2>
      <p className="ra-lead">
        Report Archive에서 발급한 토큰(<code>rat_…</code>)을 등록하면, 챗·심의가 만드는 보고서가
        공용 계정이 아니라 <b>내 RA 계정 명의</b>로 저장됩니다. RA 프로필 → 토큰 발급에서 만들어
        붙여넣으세요. 같은 이메일의 RA 계정이어야 합니다.
      </p>
      {meta ? (
        <>
          <p className="ra-status">
            연결됨 — 토큰 끝자리 <code>…{meta.tail}</code> ·{' '}
            {new Date(meta.created_at * 1000).toLocaleDateString()}{' '}
            <button className="btn-secondary tok-btn-sm" onClick={() => void remove()} disabled={busy}>
              해제
            </button>
          </p>
          {/* 어디로 저장되는지 늘 한 줄로 보인다 — '지정 안 함'과 '조직 지정'은 다른 상태다. */}
          <div className="ra-row">
            <label htmlFor="ra-ws">보고서를 저장할 조직</label>
            <select
              id="ra-ws"
              value={meta.workspace}
              disabled={busy || spaces === null}
              onChange={(e) => void changeWorkspace(e.target.value)}
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
              <span className="ra-hint">목록 불러오는 중…</span>
            )}
          </div>
          <p className="ra-hint ra-below">
            {meta.workspace
              ? '챗·심의가 만드는 보고서가 이 조직의 게시판에 쌓입니다.'
              : '조직을 지정하지 않으면 RA 계정의 기본 워크스페이스(대개 개인함)로 갑니다.'}
          </p>
        </>
      ) : (
        <div className="ra-row ra-paste">
          <input
            id="ra-token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="rat_ 로 시작하는 RA 토큰 붙여넣기"
            aria-label="RA 토큰"
          />
          <button className="btn-primary" onClick={() => void save()} disabled={busy || !token.trim()}>
            {busy ? '검증 중…' : '등록'}
          </button>
        </div>
      )}
      {/* 조직 선택 칸은 등록 뒤에 생긴다 — 후보를 그 토큰으로 RA 에 물어와야 하기 때문이다.
          그 사실을 안 적어 두면 "워크스페이스 고르는 데가 없는데?" 가 된다(실제 질문). */}
      {loaded && !meta && (
        <p className="ra-hint ra-below">
          등록하면 바로 아래에 <b>보고서를 저장할 조직</b>을 고르는 칸이 생깁니다 — 고를 수 있는
          조직 목록을 이 토큰으로 RA 에 물어오기 때문에 등록이 먼저입니다.
          안 고르면 RA 계정의 기본 워크스페이스(대개 개인함)로 갑니다.
        </p>
      )}
      {msg && (
        <p className={`ra-msg${msg.ok ? '' : ' is-err'}`}>
          {msg.text}
        </p>
      )}
    </div>
  );
}
