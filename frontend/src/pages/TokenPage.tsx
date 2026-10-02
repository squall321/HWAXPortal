// 홈에서 AI 토큰(PAT)을 발급하고 개인 Claude 등록 스니펫을 그 자리에서 복사하는 페이지
import { type CSSProperties, type FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { createPat, listPats, revokePat, type PatCreated, type PatMeta } from '../api/pat.api';
import { fetchMyAccess, type MyAccess } from '../api/access.api';
import HubAppsPanel from '../components/HubAppsPanel';
import { Page, PageHeader } from '../components/ui/Page';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { RaConnectionCard } from '../components/RaConnectionCard';
import { useCan } from '../auth/useCan';
import { makeSnippets } from '../lib/setupBat';

// 스니펫 값의 <host>는 현재 접속 중인 포털 origin을 그대로 사용한다.
const ORIGIN = window.location.origin;
// 배치·스니펫 생성기는 src/lib/setupBat.ts 에 있다(브라우저 없이 시험하기 위해 떼어 냈다).
const SNIP = makeSnippets(ORIGIN);

function fmtDate(sec: number): string {
  return new Date(sec * 1000).toLocaleString('ko-KR', { dateStyle: 'medium', timeStyle: 'short' });
}

const CERT_URL = `${ORIGIN}/tls/portal.crt`;
// 발급 CA 체인 — 리프 대신 이것을 심으면 인증서를 갱신해도 사용자 PC 를 다시 안 만진다.
const CA_URL = `${ORIGIN}/tls/ca.crt`;

const chipStyle: CSSProperties = {
  padding: '0.25rem 0.6rem',
  borderRadius: 999,
  border: '1px solid var(--border)',
  background: 'var(--card)',
  fontSize: '0.82rem',
};

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
  // 이 페이지는 PAT 발급과 Report Archive 연결을 함께 담는다 — 권한에 맞는 것만 보인다.
  const canToken = useCan()('feat:api-token');
  const [name, setName] = useState('');
  // 0 = 무기한. 만료로는 안 죽고 폐기로만 죽으므로 기본값으로 두지 않는다.
  const [ttlDays, setTtlDays] = useState(90);
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<PatCreated | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pats, setPats] = useState<PatMeta[] | null>(null);
  // 포털 인증서 체인이 공개 루트에 닿지 않는가(자체서명·사내 CA) — 그때만 인증서 안내를 띄운다.
  // 공개 CA 인증서로 교체되면 서버가 needs_ca=false 를 돌려주므로 이 블록은 저절로 사라진다.
  const [needsCa, setNeedsCa] = useState(false);
  // 서버가 발급 CA 체인(/tls/ca.crt)을 갖고 있고 그 체인이 리프를 검증하는가. 없으면 **연결 불가**다 —
  // 사내 CA 가 발급한 리프는 신뢰 목록에 넣어도 Node 가 발급자를 요구해 실패한다(실측). 리프로 대신하지 않는다.
  const [caAvailable, setCaAvailable] = useState(false);
  // 심을 파일의 주소 — 새 백엔드는 /tls/ca.crt, 이 커밋 이전 백엔드(새 dist 가 먼저 뜬 창)는 리프뿐이다.
  const [caUrl, setCaUrl] = useState(CERT_URL);
  const [expired, setExpired] = useState(false);
  const [verifyError, setVerifyError] = useState('');
  const [caError, setCaError] = useState('');
  // 판정을 못 한 이유 — null 이면 판정했다. "모름" 은 "정상" 과 같은 화면이면 안 된다(2라운드 검토):
  // 사내 CA 포털에서 판정이 빠지면 인증서 없는 등록이 나가고 Node 는 그대로 죽는다.
  const [tlsUnknown, setTlsUnknown] = useState<string | null>(null);
  // 내 권한 — "이 토큰으로 지금 열리는 플랫폼" 은 권한표에서 도구가 딸린 항목이다.
  const [access, setAccess] = useState<MyAccess | null>(null);
  const [batBusy, setBatBusy] = useState(false);
  const [batError, setBatError] = useState<string | null>(null);

  // 배치파일은 브라우저에서 만든다 — 평문 토큰을 가진 곳이 여기뿐이라, 서버에 한 번만
  // 내려받게 하는 별도 상태를 두지 않아도 '발급 순간에만 가능'이 자연히 성립한다.
  const downloadBat = async () => {
    if (!created || batBusy) return;
    setBatBusy(true);
    setBatError(null);
    try {
      let pem: string | null = null;
      if (needsCa) {
        if (!caAvailable) throw new Error('서버에 발급 CA 체인이 없어 연결 설정을 만들 수 없습니다 — 운영자 조치가 필요합니다.');
        const r = await fetch(caUrl);
        if (!r.ok) throw new Error(`인증서를 받지 못했습니다 (HTTP ${r.status}).`);
        pem = await r.text();
      }
      const blob = new Blob([SNIP.buildSetupBat(created.token, created.name, pem)], {
        type: 'application/octet-stream',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'hwax-claude-setup.bat';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setBatError(err instanceof Error ? err.message : '배치파일을 만들지 못했습니다.');
    } finally {
      setBatBusy(false);
    }
  };

  const refresh = () => {
    listPats()
      .then(setPats)
      .catch(() => setError('토큰 목록을 불러오지 못했습니다.'));
  };

  useEffect(() => {
    refresh();
    // 실패는 무시한다 — 안내가 안 뜰 뿐이고 토큰 발급 자체를 막을 이유가 없다.
    fetch(`${ORIGIN}/tls/info`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) {
          setTlsUnknown('서버가 인증서 정보를 주지 않았습니다');
          return;
        }
        // 옛 백엔드(ca_available 없음)에는 /tls/ca.crt 가 없다 — 자체서명 리프를 그대로 쓴다.
        const legacy = d.ca_available === undefined;
        setNeedsCa(Boolean(legacy ? d.self_signed : d.needs_ca));
        setCaAvailable(Boolean(legacy ? d.self_signed : d.ca_available));
        setCaUrl(legacy ? CERT_URL : CA_URL);
        setExpired(Boolean(d.expired));
        setVerifyError(String(d.verify_error || ''));
        setCaError(String(d.ca_error || ''));
        setTlsUnknown(
          !legacy && d.verified === false
            ? `서버가 인증서 체인을 판정하지 못했습니다${d.verify_error ? ` (${String(d.verify_error)})` : ''}`
            : null,
        );
      })
      .catch(() => setTlsUnknown('인증서 정보를 불러오지 못했습니다'));
    fetchMyAccess()
      .then(setAccess)
      .catch(() => {});
  }, []);

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError(null);
    try {
      // 청중(audiences)을 **보내지 않는다.** 서버 기본값(config.pat_default_audiences)이 실리고,
      // 그 한 장이 MCP 도구와 하위 사이트 REST 를 함께 덮는다. 여기서 목록을 적으면 서버가
      // 사이트를 늘려도 이 화면이 낸 토큰만 옛 범위에 갇힌다 — 종전에 `['mcp-gateway']` 를
      // 박아 두어서 이미 살아 있던 REST 프록시를 아무도 쓸 수 없었다.
      const pat = await createPat({
        name: trimmed,
        scopes: ['read', 'write'],
        ttl_days: ttlDays,
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

  // 운영자 조치 전에는 어떤 등록도 연결되지 않는 상태 — 배치파일·스니펫을 함께 잠근다. 잠근 채로
  // 스니펫만 남기면 "연결 불가" 바로 아래에 존재하지 않을 인증서 경로를 든 명령이 나간다(2라운드 검토).
  // "모름"(판정 못 함·응답 없음)도 잠근다 — 모름 상태에서 낸 등록은 검증 안 된 인증서나 인증서 없는 등록이라
  // 경고문과 실제 동작이 서로 반대였다(3라운드 검토). 판정이 되면 다시 열면 된다.
  const blocked = tlsUnknown !== null || expired || (needsCa && !caAvailable);

  // API 토큰 권한 없이 Report Archive 권한으로 들어온 사람 — PAT 발급부는 감추고 연결만 남긴다.
  // (이 페이지가 RA 연결·내 조직 선택을 함께 담고 있어서 열어 준 것이다.)
  if (!canToken) {
    return (
      <Page>
        <PageHeader title="연결 설정" desc="Report Archive 계정을 연결하고, 보고서를 쌓을 내 조직(워크스페이스)을 고릅니다." />
        <p style={{ fontSize: '0.88rem', margin: '0.6rem 0 1rem' }}>
          개인 Claude·스크립트용 API 토큰(PAT)은 <b>API 토큰 · MCP 개인 연결</b> 권한이 있어야
          발급됩니다. <Link to="/access?need=feat:api-token">내 권한에서 요청 →</Link>
        </p>
        <RaConnectionCard />
      </Page>
    );
  }

  return (
    <Page>
      <PageHeader
        title="개인 토큰"
        desc={
          <>
            개인 Claude(Claude Code · Claude Desktop)와 챗을 HWAX에 연결할 개인 접근 토큰(PAT)을 발급합니다.
            토큰은 발급 직후 <b>한 번만</b> 표시되니 그 자리에서 복사해 두세요.
          </>
        }
      />

      {error && <ErrorBanner message={error} />}

      <form
        onSubmit={onCreate}
        style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem', alignItems: 'center', margin: '1.25rem 0' }}
      >
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="토큰 이름 (예: my-laptop-claude)"
          maxLength={80}
          style={{ flex: '1 1 14rem', minWidth: 0 }}
        />
        <select
          value={ttlDays}
          onChange={(e) => setTtlDays(Number(e.target.value))}
          title="토큰 수명"

        >
          <option value={30}>30일</option>
          <option value={90}>90일</option>
          <option value={365}>1년</option>
          <option value={0}>무기한</option>
        </select>
        <button type="submit" className="btn-primary" disabled={busy || !name.trim()}>
          {busy ? '발급 중…' : '토큰 발급'}
        </button>
      </form>
      {ttlDays === 0 && (
        <div style={{ fontSize: '0.82rem', color: 'var(--muted)', margin: '-0.7rem 0 1rem' }}>
          무기한 토큰은 <b>스스로 만료되지 않습니다</b>. 유출되면 아래 목록에서 <b>폐기</b>하는 것이
          유일한 차단 수단이니, 배치파일·설정에 넣어 두는 용도로만 쓰고 안 쓰게 되면 바로 폐기하세요.
        </div>
      )}

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
          <div
            style={{
              background: 'var(--card)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '0.85rem 0.95rem',
              margin: '0.9rem 0 0.6rem',
              fontSize: '0.85rem',
              color: 'var(--fg)',
            }}
          >
            <b>윈도우라면 이것만 받아서 실행하세요.</b> 인증서 설치와 Claude 등록을 한 번에
            끝냅니다. 이 파일에는 위 토큰이 들어 있어 <b>지금 이 화면에서만</b> 만들 수 있습니다.
            {tlsUnknown && (
              <div style={{ color: '#ffd27a', marginTop: '0.45rem' }}>
                <b>인증서 판정을 못 했습니다</b> — {tlsUnknown}. 판정이 될 때까지 연결 설정(배치파일·등록
                명령)을 만들지 않습니다 — 모르는 채로 만든 등록은 인증서가 빠지거나 검증 안 된 것이 들어갑니다.
                잠시 뒤 이 화면을 새로 고쳐 다시 확인하세요.
              </div>
            )}
            {!tlsUnknown && needsCa && !expired && (
              <div style={{ color: 'var(--muted)', marginTop: '0.45rem' }}>
                이 포털의 인증서는 공개 루트에 닿지 않습니다(자체서명 또는 사내 CA). 브라우저는
                경고를 눌러 넘어갈 수 있지만 Claude(Node)는 그러지 못해, 인증서 없이 등록하면{' '}
                <code>SELF_SIGNED_CERT_IN_CHAIN</code>·<code>UNABLE_TO_VERIFY_LEAF_SIGNATURE</code> 로
                연결이 실패합니다. 배치파일이 발급 CA 체인을 <code>%USERPROFILE%\.hwax</code> 에 심고
                그 경로를 등록에 함께 넣습니다. 통신은 그대로 HTTPS 입니다.
                {verifyError && (
                  <div style={{ fontSize: '0.8rem', marginTop: '0.3rem' }}>
                    판정 근거: <code>{verifyError}</code>
                  </div>
                )}
              </div>
            )}
            {expired && (
              <div style={{ color: '#ff9b9b', marginTop: '0.45rem' }}>
                <b>포털 인증서가 만료됐습니다.</b> CA 를 심어도 연결되지 않습니다 — 운영자가 인증서를
                갱신해야 합니다. 그때까지 아래 배치파일은 만들지 않습니다.
              </div>
            )}
            {!tlsUnknown && needsCa && !caAvailable && !expired && (
              <div style={{ color: '#ff9b9b', marginTop: '0.45rem' }}>
                <b>서버에 발급 CA 체인이 없어 개인 Claude(Node)는 지금 이 포털에 연결할 수 없습니다.</b>{' '}
                사내 CA 가 발급한 리프 인증서는 신뢰 목록에 넣어도 Node 가 발급자를 요구해 실패하므로
                리프로 대신하지 않습니다. 운영자가 <code>TLS_CERT_PATH</code> 를 fullchain 으로 두거나{' '}
                <code>TLS_CA_PATH</code> 를 주면 이 화면이 CA 체인을 심는 배치파일을 냅니다.
                {caError && (
                  <>
                    {' '}
                    서버 사유: <code>{caError}</code>
                  </>
                )}
              </div>
            )}
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.7rem' }}>
              <button
                type="button"
                className="btn-primary"
                onClick={() => void downloadBat()}
                disabled={batBusy || blocked}
                title={blocked ? (tlsUnknown ? '인증서 판정이 될 때까지 만들지 않습니다' : '운영자 조치 전에는 연결되지 않습니다') : undefined}
              >
                {batBusy ? '만드는 중…' : '설정 배치파일 내려받기 (.bat)'}
              </button>
              {needsCa && caAvailable && (
                <a href={caUrl} download="hwax-portal.crt" style={{ fontSize: '0.82rem' }}>
                  인증서만 따로 받기
                </a>
              )}
            </div>
            {batError && (
              <div style={{ color: '#ff9b9b', marginTop: '0.5rem' }}>{batError}</div>
            )}
          </div>
          {blocked ? (
            <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: '0.9rem 0 0' }}>
              {tlsUnknown
                ? '인증서 판정이 되면 이 화면을 다시 열어 등록 명령을 받으세요.'
                : '운영자 조치 뒤 이 화면을 다시 열면 등록 명령이 나옵니다.'}{' '}
              토큰 자체는 유효합니다 — 등록만 뒤로 미룹니다.
            </p>
          ) : (
            <>
              <CopyBlock
                label={needsCa ? 'Claude Code (터미널 — 직접 실행할 때)' : 'Claude Code (터미널)'}
                text={
                  needsCa
                    ? SNIP.claudeCodeSnippetSelfSigned(created.token, '%USERPROFILE%\\.hwax\\hwax-portal.crt')
                    : SNIP.claudeCodeSnippet(created.token)
                }
              />
              {/* ⚠ Desktop 은 설정 값의 %USERPROFILE% 을 **풀지 않는다** — JSON 에 그대로 들어가 없는 경로가 된다.
                  배치는 확장된 실제 경로를 써 주지만, 손으로 붙여넣는 이 조각은 사람이 바꿀 수 있게 자리표시자로 보여 준다. */}
              <CopyBlock
                label={needsCa ? 'Claude Desktop (claude_desktop_config.json — 인증서 경로를 본인 것으로 바꾸세요)' : 'Claude Desktop (claude_desktop_config.json)'}
                text={SNIP.claudeDesktopSnippet(created.token, needsCa ? String.raw`C:\Users\<사용자>\.hwax\hwax-portal.crt` : null)}
              />
            </>
          )}

          <h3 style={{ color: 'var(--fg)', fontSize: '0.95rem', margin: '1.4rem 0 0' }}>
            챗을 토큰으로 호출 (curl)
          </h3>
          <CopyBlock label="POST /agent/chat" text={SNIP.chatCurlSnippet(created.token)} />
        </section>
      )}

      {access &&
        (() => {
          // 도구가 딸린 항목만 — 타일뿐인 플랫폼은 토큰과 무관하다. 기능도 하나 있다(전문가 심의).
          // tools 필드가 없으면(이 커밋 이전 백엔드가 새 dist 를 내는 창) '모름' 이다 — "없다" 로 단정하지 않는다.
          const allRows = [...access.platforms, ...access.features];
          if (!allRows.every((r) => typeof r.tools === 'boolean')) return null;
          const rows = allRows.filter((r) => r.tools);
          const opened = rows.filter((r) => r.allowed);
          const closed = rows.filter((r) => !r.allowed);
          return (
            <section style={{ marginBottom: '1.75rem' }}>
              <h2 style={{ fontSize: '1.05rem', marginBottom: '0.3rem' }}>
                이 토큰으로 지금 열리는 플랫폼
              </h2>
              <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: '0 0 0.6rem' }}>
                토큰은 하나고 범위는 내 권한이 정합니다 — 권한이 늘면 이미 발급한 토큰에도 그대로
                붙습니다.
              </p>
              {opened.length === 0 ? (
                <p style={{ color: 'var(--muted)', fontSize: '0.88rem', margin: 0 }}>
                  지금은 열리는 플랫폼이 없습니다 — 토큰을 받아도 도구가 붙지 않습니다.
                </p>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                  {opened.map((r) => (
                    <span key={r.key} title={r.reason} style={chipStyle}>
                      {r.label}
                    </span>
                  ))}
                </div>
              )}
              {closed.length > 0 && (
                <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: '0.6rem 0 0' }}>
                  닫힌 것 {closed.length}개 — {closed.map((r) => r.label).join(' · ')}.{' '}
                  {/* need= 는 그 행을 강조하고 "○○ 권한이 없어 이 화면으로 왔습니다" 배너를 띄운다 —
                      닫힌 것이 여럿이면 첫 항목을 집어 주는 것은 거짓말이 된다(실측으로 봤다). 하나일 때만 집는다. */}
                  <Link to={closed.length === 1 ? `/access?need=${encodeURIComponent(closed[0].key)}` : '/access'}>
                    내 권한에서 요청 →
                  </Link>
                </p>
              )}
            </section>
          );
        })()}

      <HubAppsPanel />

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
                  <td style={tdStyle}>
                    {/* 무기한은 100년 뒤 만료로 발급된다 — 2126년 날짜를 그대로 보여주면
                        읽는 사람이 오작동으로 읽는다. 10년 넘게 남았으면 무기한이다. */}
                    {p.exp - Date.now() / 1000 > 10 * 365 * 86400 ? '무기한' : fmtDate(p.exp)}
                  </td>
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
      <RaConnectionCard />
    </Page>
  );
}

const thStyle: CSSProperties = { padding: '0.5rem 0.6rem', fontWeight: 500 };
const tdStyle: CSSProperties = { padding: '0.55rem 0.6rem', verticalAlign: 'top' };
