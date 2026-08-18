// 홈에서 AI 토큰(PAT)을 발급하고 개인 Claude 등록 스니펫을 그 자리에서 복사하는 페이지
import { type CSSProperties, type FormEvent, useEffect, useState } from 'react';
import { createPat, listPats, revokePat, type PatCreated, type PatMeta } from '../api/pat.api';
import { ErrorBanner } from '../components/common/ErrorBanner';

// 스니펫 값의 <host>는 현재 접속 중인 포털 origin을 그대로 사용한다.
const ORIGIN = window.location.origin;
const MCP_URL = `${ORIGIN}/mcp-gw/mcp`;
// NO_PROXY 는 호스트(:포트)만 받는다 — 스킴이 붙으면 무시된다.
const HOSTONLY = ORIGIN.replace(/^https?:\/\//, '');
// 사내 프록시. 다른 서비스들이 쓰는 값과 같다(infra/.env.example HWAX_FALLBACK_PROXY,
// AIDataHub _common.sh DEFAULT_FALLBACK_PROXY). npm 레지스트리는 이걸 타야 나간다.
const CORP_PROXY = 'http://168.219.61.252:8080';
const CHAT_URL = `${ORIGIN}/agent/chat`;

function fmtDate(sec: number): string {
  return new Date(sec * 1000).toLocaleString('ko-KR', { dateStyle: 'medium', timeStyle: 'short' });
}

const CERT_URL = `${ORIGIN}/tls/portal.crt`;

function claudeCodeSnippet(token: string): string {
  return `claude mcp add --transport http hwax ${MCP_URL} --header "Authorization: Bearer ${token}"`;
}

// 자체서명 인증서를 쓰는 동안의 등록 명령.
// ⚠ `NODE_EXTRA_CA_CERTS=... claude mcp add --transport http ...` 는 듣지 않는다(실측).
// --transport http 는 설정에 URL·헤더만 저장하고 환경변수를 담지 않아서, 등록 시점의 변수는
// 정작 연결하는 시점(나중에 뜨는 Claude 프로세스)에 사라진다. stdio(mcp-remote) 형태는
// -e 로 준 환경변수를 설정에 저장해 매 실행마다 적용하므로 이쪽을 쓴다.
function claudeCodeSnippetSelfSigned(token: string, certPath: string): string {
  return [
    `claude mcp add hwax ^`,
    `  -e AUTH="Bearer ${token}" ^`,
    `  -e NODE_EXTRA_CA_CERTS=${certPath} ^`,
    `  -- npx -y mcp-remote ${MCP_URL} --header "Authorization:\${AUTH}"`,
  ].join('\n');
}

/**
 * 윈도우 설치 배치파일 — 인증서를 심고 Claude 에 등록까지 한 번에 끝낸다.
 * 인증서 PEM 을 파일 안에 그대로 넣어 첨부파일이 하나로 끝나게 한다(PEM 은 텍스트다).
 * 이 파일은 토큰이 화면에 보이는 그 순간에만 만들 수 있다 — 서버는 평문 토큰을 보관하지 않는다.
 */
function buildSetupBat(token: string, name: string, pem: string | null): string {
  const certDir = '%USERPROFILE%\\.hwax';
  const certFile = `${certDir}\\hwax-portal.crt`;
  const L: string[] = [
    '@echo off',
    'setlocal',
    'chcp 65001 >nul',
    'echo.',
    'echo  HWAX 포털 - 개인 Claude 연결 설정',
    `echo  토큰 이름: ${name}`,
    'echo.',
    'set HWAX_DONE=0',
    '',
    // ── [0] 네트워크 점검 ───────────────────────────────────────────────────
    // 사내 PC 는 프록시가 걸려 있는 경우가 많다. 그러면 두 곳이 막히는데 증상이 둘 다
    // "MCP 등록 실패" 로만 보여서 원인을 못 찾는다.
    //   ① 포털(사내 주소) — 프록시를 타면 막히거나 TLS 가 프록시 인증서로 바뀐다
    //   ② npx 가 npm 레지스트리에서 mcp-remote 를 받을 때 — 여긴 반대로 프록시가 있어야 한다
    // 그래서 스스로 확인하고 포털만 NO_PROXY 에 넣는다. 레지스트리는 프록시를 계속 쓴다.
    'echo  [0] 네트워크 점검...',
    'if defined HTTP_PROXY echo      HTTP_PROXY=%HTTP_PROXY%',
    'if defined HTTPS_PROXY echo      HTTPS_PROXY=%HTTPS_PROXY%',
    'if defined NO_PROXY echo      NO_PROXY=%NO_PROXY%',
    'if not defined HTTPS_PROXY if not defined HTTP_PROXY echo      프록시 환경변수 없음',
    // 포털에 프록시 없이 붙어 본다. DefaultWebProxy=$null 이 PowerShell 5 에서도 통한다.
    // ⚠ 인증서 검증을 끈다. 포털이 자체 서명이면 TLS 에서 걸려 '직결 불가'로 잘못 판정하고,
    // 그러면 프록시 문제가 아닌데 프록시 안내를 띄운다. 이건 도달성 확인이지 보안 경계가 아니다
    // (실제 통신은 아래 등록된 설정이 NODE_EXTRA_CA_CERTS 로 정상 검증한다).
    'powershell -NoProfile -Command "$ErrorActionPreference=\'SilentlyContinue\';' +
      '[System.Net.ServicePointManager]::ServerCertificateValidationCallback={$true};' +
      'try{[System.Net.WebRequest]::DefaultWebProxy=$null;' +
      `$r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 8 -Uri \'${ORIGIN}/\';` +
      'if($r.StatusCode -ge 200){exit 0}else{exit 1}}catch{exit 1}"',
    'if errorlevel 1 goto :px_need',
    // 기존 값을 먼저 잡고 분기한다 — 바로 이어 붙이면 NO_PROXY 가 비었을 때 ',host' 가 된다.
    'set _NP=%NO_PROXY%',
    `if not defined _NP set NO_PROXY=${HOSTONLY}`,
    `if defined _NP set NO_PROXY=%_NP%,${HOSTONLY}`,
    'set no_proxy=%NO_PROXY%',
    'echo      포털 직결 확인 - 이 창에서는 포털을 프록시 없이 씁니다',
    'goto :px_npm',
    ':px_need',
    'echo      [!] 포털에 직접 붙지 못했습니다.',
    'echo          사내망^(VPN^) 연결을 확인하세요. 등록은 계속 진행합니다.',
    ':px_npm',
    // npx 는 레지스트리를 타야 mcp-remote 를 받는다. 프록시가 안 잡혀 있으면 여기서 죽는데,
    // 에러가 'MCP 등록 실패' 로만 보인다. 미리 확인하고 없으면 사내 프록시를 이 창에 세운다.
    'where npx >nul 2>nul',
    'if errorlevel 1 goto :px_done',
    'call npx -y mcp-remote --version >nul 2>nul',
    'if not errorlevel 1 goto :px_done',
    'if defined HTTPS_PROXY goto :px_npmfail',
    `echo      npm 레지스트리에 못 나갑니다 - 사내 프록시^(${CORP_PROXY}^)를 이 창에 적용합니다`,
    `set HTTPS_PROXY=${CORP_PROXY}`,
    `set HTTP_PROXY=${CORP_PROXY}`,
    'call npx -y mcp-remote --version >nul 2>nul',
    'if not errorlevel 1 goto :px_done',
    ':px_npmfail',
    'echo      [!] npx 가 mcp-remote 를 받지 못했습니다.',
    'echo          프록시 뒤라면 관리자에게 npm 레지스트리 허용을 요청하세요.',
    'echo          ^(이 단계가 실패해도 Claude Desktop 등록 자체는 진행됩니다^)',
    ':px_done',
    'echo.',
    '',
  ];
  if (pem) {
    L.push(
      'echo  [1] 포털 인증서 설치...',
      `if not exist "${certDir}" mkdir "${certDir}"`,
      `if exist "${certFile}" del "${certFile}"`,
    );
    // PEM 한 줄씩 append. base64 와 -----BEGIN----- 은 배치 특수문자(^ & < > |)를 포함하지 않는다.
    for (const line of pem.split('\n')) {
      if (line.trim()) L.push(`>>"${certFile}" echo ${line.trim()}`);
    }
    L.push(`echo      ${certFile}`, '');
  }

  // ⚠ 아래는 일부러 괄호 블록( if ... ( ... ) )을 쓰지 않고 goto 로 흐름을 만든다.
  // 괄호 안에 PowerShell 한 줄처럼 (, ), | 가 섞인 긴 명령을 넣으면 cmd 의 괄호 매칭이
  // 어긋나 "예기치 않음" 으로 죽는 사고가 잦다. 라벨 방식이 장황해도 깨지지 않는다.

  // ── Claude Code (CLI) — 있을 때만 ──────────────────────────────────────────
  L.push(
    'echo  [2] Claude Code (CLI) 확인...',
    'where claude >nul 2>nul',
    'if errorlevel 1 goto :no_cli',
    'claude mcp remove hwax -s local >nul 2>nul',
  );
  L.push(
    pem
      ? `claude mcp add hwax -e AUTH="Bearer ${token}" -e NODE_EXTRA_CA_CERTS=${certFile} -- npx -y mcp-remote ${MCP_URL} --header "Authorization:${'${AUTH}'}"`
      : `claude mcp add --transport http hwax ${MCP_URL} --header "Authorization: Bearer ${token}"`,
  );
  L.push(
    'if errorlevel 1 goto :cli_fail',
    // 등록됐다는 것과 설정에 남았다는 것은 다르다 — 되읽어서 확인해야 "완료"라고 말할 수 있다.
    'claude mcp get hwax >nul 2>nul',
    'if errorlevel 1 goto :cli_fail',
    'set HWAX_DONE=1',
    'echo      Claude Code 등록 완료',
    'goto :desktop',
    ':cli_fail',
    'echo      [X] Claude Code 등록 실패',
    'goto :desktop',
    ':no_cli',
    'echo      claude 명령 없음 - 건너뜀 ^(Claude Desktop 만 쓰신다면 정상^)',
    '',
  );

  // ── Claude Desktop — 설정 JSON 에 병합 ────────────────────────────────────
  // 기존 mcpServers 의 다른 서버는 보존하고 hwax 만 덮어쓴다. 원본은 .bak 으로 백업.
  //
  // ⚠ 항목 JSON 을 배치의 echo 로 내보내지 않는다(실사고). JSON.stringify 로 이스케이프해 둔
  //    "%USERPROFILE%\\.hwax\\..." 를 echo 하면 cmd 가 %USERPROFILE% 을 **이스케이프 뒤에**
  //    확장해 "C:\Users\Sonic\\.hwax\\..." 처럼 홑/겹 백슬래시가 섞인다. \U 는 JSON 이스케이프가
  //    아니라서 ConvertFrom-Json 이 "Unrecognized escape sequence" 로 죽는다.
  //    → 경로는 환경변수로 넘기고 JSON 조립은 PowerShell 이 한다(ConvertTo-Json 이 알아서 이스케이프).
  //
  // ⚠ powershell.exe 는 cmdlet 이 에러를 뱉어도 **종료코드 0** 으로 끝난다. errorlevel 만 보면
  //    실패가 성공으로 보인다(위 사고에서 "등록 완료" 가 찍혔다). ErrorActionPreference=Stop +
  //    try/catch + exit 1 로 실패를 errorlevel 에 실어 보낸다.
  const psEntry = pem
    ? `$e=[pscustomobject]@{command='npx';args=@('-y','mcp-remote','${MCP_URL}','--header','Authorization:$\{AUTH}');env=[pscustomobject]@{AUTH=$env:HWAX_AUTH;NODE_EXTRA_CA_CERTS=$env:HWAX_CERT}};`
    : `$e=[pscustomobject]@{type='http';url='${MCP_URL}';headers=[pscustomobject]@{Authorization=$env:HWAX_AUTH}};`;
  // PowerShell 조각 안에서는 큰따옴표를 쓰지 않는다 — cmd 의 "..." 안에 들어가기 때문.
  const ps = [
    "$ErrorActionPreference='Stop';",
    'try{',
    '$c=$env:HWAX_CFG;',
    psEntry,
    "if(Test-Path $c){Copy-Item $c ($c+'.bak') -Force; $j=Get-Content $c -Raw | ConvertFrom-Json}else{$j=[pscustomobject]@{}};",
    'if(-not $j.mcpServers){$j | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{}) -Force};',
    '$j.mcpServers | Add-Member -NotePropertyName hwax -NotePropertyValue $e -Force;',
    '[System.IO.File]::WriteAllText($c, ($j | ConvertTo-Json -Depth 20), (New-Object System.Text.UTF8Encoding($false)));',
    // 쓴 뒤 되읽어 확인한다. 파일이 깨졌으면 여기서 걸린다.
    "if(-not ((Get-Content $c -Raw | ConvertFrom-Json).mcpServers.hwax)){throw 'config verify failed'};",
    'exit 0}catch{[Console]::Error.WriteLine($_.Exception.Message);exit 1}',
  ].join(' ');
  L.push(
    ':desktop',
    'echo  [3] Claude Desktop 확인...',
    'set "HWAX_CFG=%APPDATA%\\Claude\\claude_desktop_config.json"',
    'if not exist "%APPDATA%\\Claude" goto :no_desktop',
    `set "HWAX_AUTH=Bearer ${token}"`,
    ...(pem ? [`set "HWAX_CERT=${certFile}"`] : []),
    `powershell -NoProfile -ExecutionPolicy Bypass -Command "${ps}"`,
    'if errorlevel 1 goto :desktop_fail',
    'set HWAX_DONE=1',
    'echo      Claude Desktop 등록 완료 ^(기존 설정은 .bak 으로 백업^)',
    'goto :desktop_done',
    ':desktop_fail',
    'echo      [X] Desktop 설정 수정 실패 - 위 메시지 확인 ^(원본은 .bak 에 그대로 있습니다^)',
    'goto :desktop_done',
    ':no_desktop',
    'echo      Claude Desktop 설정 폴더 없음 - 건너뜀',
    ':desktop_done',
    '',
  );

  // ── Gemini CLI ────────────────────────────────────────────────────────────
  // ⚠ `gemini mcp add` 는 --header 를 **자기 옵션으로 먹는다**(실측: args 에서 통째로 사라져
  // 인증 없이 등록됨 → 401). npx 뒤에 `--` 를 넣어야 나머지가 서버 인자로 넘어간다(실측 확인).
  const gemEnv = pem
    ? `-e AUTH="Bearer ${token}" -e NODE_EXTRA_CA_CERTS=${certFile}`
    : `-e AUTH="Bearer ${token}"`;
  L.push(
    ':gemini',
    'echo  [4] Gemini CLI 확인...',
    'where gemini >nul 2>nul',
    'if errorlevel 1 goto :no_gemini',
    'gemini mcp remove hwax -s user >nul 2>nul',
    `gemini mcp add -s user -t stdio ${gemEnv} hwax npx -- -y mcp-remote ${MCP_URL} --header "Authorization:${'${AUTH}'}"`,
    'if errorlevel 1 goto :gemini_fail',
    'set HWAX_DONE=1',
    'echo      Gemini CLI 등록 완료',
    'goto :codex',
    ':gemini_fail',
    'echo      [X] Gemini CLI 등록 실패',
    'goto :codex',
    ':no_gemini',
    'echo      gemini 명령 없음 - 건너뜀',
    '',
  );

  // ── Codex CLI ─────────────────────────────────────────────────────────────
  // 형식 출처: https://learn.chatgpt.com/docs/extend/mcp?surface=cli
  //   config.toml → [mcp_servers.<name>] { command, args, env }
  //   CLI         → codex mcp add <name> --env K=V -- <command> [args...]
  // TOML 을 직접 고치지 않고 CLI 를 쓴다 — 남의 설정 파일을 파싱/재작성하지 않는 쪽이 안전하다.
  // gemini 와 같은 이유로 `--` 뒤에 서버 명령을 둬야 --header 가 codex 옵션으로 먹히지 않는다.
  // 실패하면 붙여넣을 TOML 조각을 남긴다(이 환경에 codex 가 없어 실행 검증은 못 했다).
  const codexEnv = pem
    ? `--env AUTH="Bearer ${token}" --env NODE_EXTRA_CA_CERTS=${certFile}`
    : `--env AUTH="Bearer ${token}"`;
  const codexToml = [
    '[mcp_servers.hwax]',
    'command = "npx"',
    `args = ["-y", "mcp-remote", "${MCP_URL}", "--header", "Authorization:\${AUTH}"]`,
    '',
    '[mcp_servers.hwax.env]',
    `AUTH = "Bearer ${token}"`,
    // TOML 리터럴 문자열(홑따옴표)은 이스케이프를 처리하지 않으므로 경로를 그대로 쓴다.
    // 큰따옴표 + 백슬래시 이중화는 Desktop JSON 과 똑같은 함정에 빠진다 — 배치가 echo 할 때
    // %USERPROFILE% 이 확장되면서 홑/겹 백슬래시가 섞여 \U 가 되고 TOML 파싱이 깨진다.
    ...(pem ? [`NODE_EXTRA_CA_CERTS = '${certFile}'`] : []),
  ];
  L.push(
    ':codex',
    'echo  [5] Codex CLI 확인...',
    'where codex >nul 2>nul',
    'if errorlevel 1 goto :no_codex',
    'codex mcp remove hwax >nul 2>nul',
    `codex mcp add hwax ${codexEnv} -- npx -y mcp-remote ${MCP_URL} --header "Authorization:${'${AUTH}'}"`,
    'if errorlevel 1 goto :codex_manual',
    'set HWAX_DONE=1',
    'echo      Codex CLI 등록 완료',
    'goto :codex_done',
    ':codex_manual',
    'set "HWAX_TOML=%USERPROFILE%\\hwax-codex-snippet.toml"',
    'if exist "%HWAX_TOML%" del "%HWAX_TOML%"',
    ...codexToml.map((l) => (l ? `>>"%HWAX_TOML%" echo ${l}` : '>>"%HWAX_TOML%" echo.')),
    'echo      [X] codex mcp add 실패 - 아래 파일을 직접 붙여넣으세요:',
    'echo        %HWAX_TOML%  ^-^-^>  %USERPROFILE%\\.codex\\config.toml',
    'goto :codex_done',
    ':no_codex',
    'echo      codex 명령 없음 - 건너뜀',
    ':codex_done',
    '',
  );

  L.push(
    'echo.',
    'if not "%HWAX_DONE%"=="0" goto :ok',
    'echo  [X] Claude Code / Desktop / Gemini / Codex 중 어느 것도 설정하지 못했습니다.',
    'echo      하나라도 설치한 뒤 이 파일을 다시 실행하세요.',
    'pause',
    'exit /b 1',
    ':ok',
    'echo  [O] 완료. Claude 를 완전히 종료한 뒤 다시 실행하세요.',
    'echo      Desktop: 설정 - 커넥터에 hwax 가 보이면 정상',
    'echo      CLI    : claude mcp get hwax  ^| gemini mcp list  ^| codex mcp list',
    'echo.',
    'pause',
  );
  // 윈도우 배치는 CRLF 여야 안전하다(LF 만이면 일부 환경에서 마지막 인자에 CR 이 섞인다).
  // UTF-8 BOM 을 붙인다 — cmd.exe 는 .bat 을 시스템 코드페이지로 읽어서, BOM 이 없으면
  // 위 한글 안내가 전부 깨진다. BOM 이 있으면 UTF-8 로 인식한다(chcp 65001 은 출력 쪽 보정).
  return '﻿' + L.join('\r\n') + '\r\n';
}

// Claude Desktop 에 넣을 서버 항목. 자체서명 구간에는 CLI 와 같은 이유로 mcp-remote 를 쓴다 —
// type:'http' 로는 CA 인증서를 지정할 방법이 없어 SELF_SIGNED_CERT_IN_CHAIN 으로 죽는다.
// ${AUTH} 치환은 mcp-remote 가 자기 환경변수로 수행한다(토큰이 프로세스 인자에 안 남는다).
function desktopServerEntry(token: string, certPath: string | null): object {
  if (!certPath) {
    return { type: 'http', url: MCP_URL, headers: { Authorization: `Bearer ${token}` } };
  }
  return {
    command: 'npx',
    args: ['-y', 'mcp-remote', MCP_URL, '--header', 'Authorization:${AUTH}'],
    env: { AUTH: `Bearer ${token}`, NODE_EXTRA_CA_CERTS: certPath },
  };
}

function claudeDesktopSnippet(token: string, certPath: string | null): string {
  return JSON.stringify({ mcpServers: { hwax: desktopServerEntry(token, certPath) } }, null, 2);
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
  // 포털이 자체서명 인증서로 떠 있는가 — 그때만 인증서 안내를 띄운다. 사내 CA 인증서로
  // 교체되면 서버가 self_signed=false 를 돌려주므로 이 블록은 저절로 사라진다.
  const [selfSigned, setSelfSigned] = useState(false);
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
      if (selfSigned) {
        const r = await fetch(CERT_URL);
        if (!r.ok) throw new Error(`인증서를 받지 못했습니다 (HTTP ${r.status}).`);
        pem = await r.text();
      }
      const blob = new Blob([buildSetupBat(created.token, created.name, pem)], {
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
      .then((d) => setSelfSigned(Boolean(d?.self_signed)))
      .catch(() => {});
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
            {selfSigned && (
              <div style={{ color: 'var(--muted)', marginTop: '0.45rem' }}>
                이 포털은 아직 자체서명 인증서를 씁니다. 브라우저는 경고를 눌러 넘어갈 수 있지만
                Claude(Node)는 그러지 못해, 인증서 없이 등록하면{' '}
                <code>SELF_SIGNED_CERT_IN_CHAIN</code> 으로 연결이 실패합니다. 배치파일이 인증서를{' '}
                <code>%USERPROFILE%\.hwax</code> 에 심고 그 경로를 등록에 함께 넣습니다. 통신은
                그대로 HTTPS 입니다.
              </div>
            )}
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.7rem' }}>
              <button type="button" className="btn-primary" onClick={() => void downloadBat()}>
                {batBusy ? '만드는 중…' : '설정 배치파일 내려받기 (.bat)'}
              </button>
              {selfSigned && (
                <a href={CERT_URL} download="hwax-portal.crt" style={{ fontSize: '0.82rem' }}>
                  인증서만 따로 받기
                </a>
              )}
            </div>
            {batError && (
              <div style={{ color: '#ff9b9b', marginTop: '0.5rem' }}>{batError}</div>
            )}
          </div>
          <CopyBlock
            label={selfSigned ? 'Claude Code (터미널 — 직접 실행할 때)' : 'Claude Code (터미널)'}
            text={
              selfSigned
                ? claudeCodeSnippetSelfSigned(created.token, '%USERPROFILE%\\.hwax\\hwax-portal.crt')
                : claudeCodeSnippet(created.token)
            }
          />
          <CopyBlock
            label="Claude Desktop (claude_desktop_config.json)"
            text={claudeDesktopSnippet(created.token, selfSigned ? String.raw`%USERPROFILE%\.hwax\hwax-portal.crt` : null)}
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
