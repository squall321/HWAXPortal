// 윈도우 설치 배치와 등록 스니펫을 만드는 순수 생성기 — 브라우저 없이 시험할 수 있게 페이지에서 떼어 냈다
//
// 왜 페이지에서 떼어 냈나: 이 배치는 실사고가 여섯 번 났는데(PAT 평문 노출·http 스니펫 무연결·npm 점검 무한대기·
// Desktop JSON 이스케이프·`claude mcp add` 가 배치를 끊음·PATH 미반영) 그동안 **시험이 하나도 없었다**. TokenPage.tsx
// 안에 있으면 React·DOM 없이 실행할 수 없어서다. 여기 있으면 origin 만 넘겨 산출물을 그대로 검사할 수 있다
// (backend/tests/test_setup_bat.py 가 tsc 로 이 파일만 컴파일해 node 로 돌린다).
//
// window·document 를 **참조하지 않는다** — origin 은 인자로 받는다.

/** 배치 없이 인증서로 직접 설정하는 한 단계 — 화면이 복사 상자 하나와 설명 한 줄로 그린다. */
export interface CertStep {
  label: string;
  text: string;
  note: string;
}

export interface Snippets {
  // proxy — 포털이 PAT 발급 응답(fallback_proxy)으로 준 사내 프록시. 비면 npm 레지스트리 폴백 없이 직결만 본다.
  // offload — 토큰 화면의 '서버 LLM 에 일 맡기기' 칸(기본 끔, docs/token-saving/offload-v2.md 3-4) — Claude Code 명령 둘 · CLAUDE.md 규칙. 끄면 전에 넣은 것을 걷는다.
  //   결과 손잡이 머리(X-HWAX-Result: ref)는 이 칸과 상관없이 늘 단다(사용자 결정 11-28 — docs/request-1125 P-1).
  // share — '내 Claude 대화를 포털에 공유' 칸(기본 off, docs/interaction-data contract §5) — command(/hwax-share) · auto(+ SessionEnd 훅). off 면 걷는다.
  buildSetupBat: (
    token: string,
    name: string,
    pem: string | null,
    proxy: string | null,
    offload?: boolean,
    share?: 'off' | 'command' | 'auto',
    view?: string | null,
  ) => string;
  // view — 이 등록을 목적 보기로 고정(`purpose:<키>,…` — docs/mcp-modernize M3 PC 킷 목적 고르기). 비거나 꼴이 틀리면 포털 설정을 따른다(머리 portal).
  claudeCodeSnippet: (token: string, view?: string | null) => string;
  claudeCodeSnippetSelfSigned: (token: string, certPath: string, view?: string | null) => string;
  claudeDesktopSnippet: (token: string, certPath: string | null, view?: string | null) => string;
  chatCurlSnippet: (token: string) => string;
  certGuide: (token: string | null) => CertStep[];
}

export function makeSnippets(origin: string): Snippets {
  const ORIGIN = origin;
  const MCP_URL = `${ORIGIN}/mcp-gw/mcp`;
  // NO_PROXY 는 호스트(:포트)만 받는다 — 스킴이 붙으면 무시된다.
  const HOSTONLY = ORIGIN.replace(/^https?:\/\//, '');
  // 사내 프록시 — 공개 리포에 실제 주소를 두지 않는다(사용자 결정 11-24). 박스의 infra/.env HWAX_FALLBACK_PROXY 를 포털이 PAT 발급 응답
  // (fallback_proxy)으로 주고, 화면이 buildSetupBat 에 넘긴다. 값은 배치의 echo · PowerShell 홑따옴표 · set 에 그대로 들어가므로
  // 'http(s)://호스트[:포트]' 모양만 받는다 — 비었거나 모양이 틀리면 null(폴백 없이 직결만 본다).
  const fallbackProxy = (p: string | null): string | null => {
    const v = (p ?? '').trim();
    return /^https?:\/\/[A-Za-z0-9.-]+(:\d{1,5})?\/?$/.test(v) ? v : null;
  };
  const CHAT_URL = `${ORIGIN}/agent/chat`;
  // 이 페이지가 만들어 주는 것에는 전부 평문 PAT 가 들어간다. 지금 접속한 origin 이 http 면
  // 그 PAT 가 네트워크를 그대로 건너간다 — 게다가 인증서 설치(NODE_EXTRA_CA_CERTS)는
  // http 에서 아무 일도 하지 않아 사용자는 '보안 조치를 했다'고 오해한다.
  // localhost 는 예외다(같은 기계 안이라 나가지 않는다).
  // mcp-remote 는 https 가 아니면 즉시 종료한다("Non-HTTPS URLs are only allowed for localhost
  // or when --allow-http flag is provided"). 그래서 http origin 에서 만든 스니펫은 등록은
  // 되는데 연결은 100% 실패한다 — 사용자는 '등록 완료' 를 보고 도구가 왜 안 뜨는지 모른다
  // (실측: 배치가 만든 명령 그대로 돌려 이 에러로 죽었고, --allow-http 하나 붙이니
  //  "Proxy established successfully" 로 붙었다).
  // 아래 두 상수를 mcp-remote 인자를 만드는 모든 자리에 쓴다 — 일곱 군데다.
  const IS_PLAINTEXT =
    ORIGIN.startsWith('http://') &&
    !/^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(:|$)/.test(ORIGIN);
  // localhost 는 mcp-remote 가 원래 허용하므로 IS_PLAINTEXT 와 같은 조건이면 충분하다.
  const ALLOW_HTTP = IS_PLAINTEXT ? ' --allow-http' : '';
  const ALLOW_HTTP_ARR = IS_PLAINTEXT ? "'--allow-http'," : '';
  const ALLOW_HTTP_TOML = IS_PLAINTEXT ? ', "--allow-http"' : '';
  // hwax env 의 NO_PROXY 기본값(10-20 요청 3) — 포털 호스트(포트 없이) · localhost · 127.0.0.1. 사내 프록시가 잡힌 PC 에서
  // mcp-remote 가 포털까지 프록시로 가려다 막혔다(요청자 실측: 이 값과 회사 인증서를 넣자 붙었다).
  const HOSTNAME = (() => {
    try {
      return new URL(ORIGIN).hostname;
    } catch {
      return HOSTONLY.split(':')[0];
    }
  })();
  const NOPROXY = Array.from(new Set([HOSTNAME, 'localhost', '127.0.0.1'])).join(',');
  // 개인 Claude 보기(docs/request-1029 E-4 · C-41) — 게이트웨이는 이 연결 머리로 청한 연결에만 포털에서 고른 보기(전체 · 묶음 · 가벼운)를 얹는다.
  // 머리가 없는 연결(내 토큰으로 서버에서 도는 앱 · 스크립트)은 늘 전체다 — 보기를 모든 개인 토큰에 얹으면 리스크 심사 · 위키 앱이 그 사람의 보기로
  // 도구를 잃었다(검토 10-31). 그래서 Claude Code · Desktop 등록에만 단다(Gemini · Codex 는 달지 않는다). 값의 정본은 backend/app/access/hub_view.py
  // (HEADER_NAME · HEADER_PORTAL — 게이트웨이 VIEW_PORTAL 과 시험이 맞댄다). mcp-remote 는 머리를 'Name:value'(빈칸 없이)로 받는다 — Authorization 과 같다.
  const VIEW_NAME = 'X-HWAX-View';
  const VIEW_PORTAL = 'portal';
  // 목적 고정(docs/mcp-modernize M3 — PC 킷 목적 고르기) — 사람이 이 PC 등록을 목적 보기로 묶겠다고 고르면 머리 값이 `purpose:<키>,…` 다. 그 연결은
  // 포털 설정과 상관없이 그 목적이다(게이트웨이 — 머리가 보기 글이면 그것). C-41 은 그대로다 — 포털에서 고른 보기는 여전히 `portal` 머리 연결에만
  // 얹히고, 고정은 사람이 이 칸을 켤 때만 단다(기본은 portal). 꼴이 틀리면 portal 로 돌아간다 — 틀린 머리는 게이트웨이가 전체로 읽어 사람이 고른 것과
  // 달라진다. 키 꼴 · 상한은 backend/app/access/hub_view.py 의 AREA_RE · AREAS_MAX 와 같다(값은 cmd echo · PowerShell 홑따옴표에 그대로 들어간다 —
  // 이 꼴의 글자는 둘 다에 안전하다).
  const VIEW_PIN_RE = /^purpose:[a-z][a-z0-9_-]{0,31}(,[a-z][a-z0-9_-]{0,31}){0,31}$/;
  const viewValue = (view?: string | null): string =>
    view && VIEW_PIN_RE.test(view) ? view : VIEW_PORTAL;
  const viewArg = (v: string) => ` --header "${VIEW_NAME}: ${v}"`;
  const viewArgRemote = (v: string) => ` --header "${VIEW_NAME}:${v}"`;
  // 결과 손잡이 머리(토큰 절감 2판 B — docs/token-saving/offload-v2.md 3-2) — Claude Code · Desktop 등록에 보기 머리 옆에 **늘** 단다(사용자 결정 11-28 —
  // docs/request-1125 P-1, 종전엔 '서버 LLM 에 일 맡기기' 칸을 켤 때만). 게이트웨이는 박스 스위치(GATEWAY_RESULT_REFS=1 — 기본 꺼짐, TS-6 · TS-7)와 이 머리가
  // 둘 다 있는 연결에만 큰 결과를 머리 + ref 로 준다(1판 TS-3). 스위치가 꺼진 박스에서는 아무 일도 없다 — 결과 · 목록이 머리 없는 연결과 바이트까지 같다.
  // Gemini · Codex 는 보기 머리처럼 달지 않는다('개인 Claude' 가 아니다).
  const RESULT_NAME = 'X-HWAX-Result';
  const RESULT_REF = 'ref';
  const RESULT_ARG = ` --header "${RESULT_NAME}: ${RESULT_REF}"`;
  const RESULT_ARG_REMOTE = ` --header "${RESULT_NAME}:${RESULT_REF}"`;
  // 칸이 켜졌을 때 Claude Code 에 까는 것 — 사용자 명령 둘과 사용자 CLAUDE.md 의 규칙 묶음. 끄고 다시 돌리면 걷는다.
  //   명령 파일은 끝 줄의 OFFLOAD_MARK 로 우리 것인지 가른다(같은 이름의 사람 파일은 덮지도 지우지도 않는다).
  //   CLAUDE.md 는 표지 두 줄 사이만 쓴다 — 그 밖의 줄은 바이트 그대로 둔다.
  const OFFLOAD_MARK = 'hwax-offload';
  const OFFLOAD_BEGIN = '<!-- hwax-offload:begin -->';
  const OFFLOAD_END = '<!-- hwax-offload:end -->';
  const OFFLOAD_FOOT = `<!-- ${OFFLOAD_MARK}: 포털 설정 배치가 만든 파일 — 토큰 화면의 '서버 LLM 에 일 맡기기' 칸을 끄고 배치를 다시 돌리면 지운다 -->`;
  const OFFLOAD_ASK = [
    '---',
    'description: 여러 도구를 도는 조사를 HWAX 서버 LLM 에 맡긴다(위임 — 토큰 절약)',
    'argument-hint: <맡길 조사 한 줄>',
    '---',
    '아래 조사를 직접 도구를 여러 번 불러 풀지 말고 HWAX 서버에 맡긴다 — hwax MCP 의 위임 도구를 쓴다.',
    '',
    '과제: $ARGUMENTS',
    '',
    '1. `delegate_start(task=<위 과제>)` 를 부른다 — 받은 job_id 를 적어 둔다. 범위를 좁힐 앱이 분명하면 `apps` 도 준다.',
    '2. `delegate_status(job_id, wait_s=120)` 을 끝날 때까지 되풀이한다 — 서버가 끝나거나 바뀔 때까지 기다렸다 답한다. 기다리는 동안 같은 조사를 직접 하지 않는다.',
    '3. 끝나면 `delegate_result(job_id)` 로 답 · 근거 · 숫자 대조를 받아 사람에게 전한다. 숫자 대조가 어긋났다는 표시(numbers.mismatched)는 고치거나 빼지 말고 그대로 전한다.',
    '4. 위임 도구가 없으면(그 박스에서 꺼져 있다) 그렇다고 말하고 멈춘다 — 직접 조사할지는 사람에게 묻는다.',
    '',
    OFFLOAD_FOOT,
    '',
  ].join('\n');
  const OFFLOAD_DRAFT = [
    '---',
    'description: 긴 글(보고서 · 메모 · 회의록의 절)을 HWAX 서버 LLM 이 쓰게 한다(토큰 절약)',
    'argument-hint: <개요 — 쓸 절 · 요점 · 문체>',
    '---',
    '아래 개요의 글을 직접 길게 쓰지 말고 hwax MCP 의 `draft_section` 으로 서버가 쓰게 한다.',
    '',
    '개요: $ARGUMENTS',
    '',
    '1. 근거는 원문을 다시 읽어 붙이지 말고 손잡이로 넘긴다 — 이 대화에서 받은 큰 결과의 ref 나 `{tool, args}` 를 `refs` 에 싣는다.',
    '2. `draft_section(outline=<개요>, refs=[...], style="report")` 를 부른다 — style 은 report · memo · minutes · plain 가운데 하나, 길이를 정하려면 target_chars.',
    '3. 받은 draft 를 사람에게 보인다. 숫자 대조가 어긋났다는 표시(numbers)는 고치거나 빼지 말고 그대로 전한다.',
    '4. `draft_section` 이 없으면(그 박스에서 꺼져 있다) 그렇다고 말하고 멈춘다 — 직접 쓸지는 사람에게 묻는다.',
    '',
    OFFLOAD_FOOT,
    '',
  ].join('\n');
  // CLAUDE.md 표지 사이의 본문 — 표지 줄은 배치의 PowerShell 이 붙인다(지울 때 같은 상수로 찾는다).
  const OFFLOAD_RULES = [
    '## HWAX — 서버 LLM 에 일 맡기기(토큰 절약)',
    '',
    "포털 설정 배치가 넣은 규칙이다 — 토큰 화면의 '서버 LLM 에 일 맡기기' 칸을 끄고 배치를 다시 돌리면 표지 두 줄 사이가 걷힌다. 이 사이를 고쳐도 다음 실행 때 덮인다.",
    '',
    '- 큰 결과는 ref 로 받는다 — hwax 도구 결과가 머리 + ref 로 오면 원문 전체를 받지 말고 `result_ask(ref, question)` 로 묻는다. 원문의 한 부분이 꼭 필요할 때만 `result_get(ref, page)` 로 쪽을 받는다.',
    '- 여러 도구를 도는 조사는 `delegate_start` 로 서버에 맡기고 `delegate_status(job_id, wait_s)` → `delegate_result(job_id)` 로 받는다(명령 `/hwax-ask`).',
    '- 긴 글(보고서 · 메모 · 회의록의 절)은 `draft_section` 으로 서버가 쓰게 한다(명령 `/hwax-draft`).',
    '- 숫자 대조가 어긋났다는 표시(numbers.mismatched 등)는 고치거나 빼지 말고 그대로 사람에게 전한다.',
    '- 이 도구들이 없으면(그 박스에서 꺼져 있다) 종전처럼 직접 한다.',
  ].join('\n');
  // 배치에 글을 싣는 길 — base64 는 [A-Za-z0-9+/=] 뿐이라 cmd 의 set 줄과 PowerShell 어디에도 걸리지 않는다(% ^ & " < > 와 줄바꿈을 걱정하지 않는다).
  //   UTF-8 바이트를 싣고 PowerShell 이 UTF-8 로 푼다 — 콘솔 코드페이지와 무관하다.
  const b64 = (s: string): string => {
    let bin = '';
    for (const c of new TextEncoder().encode(s)) bin += String.fromCharCode(c);
    return btoa(bin);
  };
  // 내 Claude 대화를 포털에 공유(docs/interaction-data contract §5 — 사람이 스스로 보낸다, IX-3) — 설정 배치의 선택 칸(기본 끔)을 켜면 올리는 작은
  // PowerShell(%USERPROFILE%\.hwax\hwax-share.ps1)과 Claude Code 명령 /hwax-share 를 두고, '세션 끝에 자동으로' 를 고르면 사용자 settings.json 에
  // SessionEnd 훅을 단다. 끄고 다시 돌리면 걷는다(위 서버 LLM 칸과 같은 표지 꼴 — 파일은 표지 낱말로 우리 것인지 가르고, 훅은 명령 글의 스크립트 이름으로).
  //   기록 파일 자리는 Claude Code 문서(sessions)의 규칙 — <설정 폴더>\projects\<프로젝트>\<세션 id>.jsonl, 설정 폴더는 CLAUDE_CONFIG_DIR 이 있으면 그것.
  //   토큰은 배치가 hwax 연결에 넣은 자리(.claude.json 의 mcpServers.hwax — headers.Authorization 또는 env.AUTH)에서 그때그때 읽는다(재발급해도 따라간다).
  const SHARE_MARK = 'hwax-share';
  const SHARE_HOOK_MARK = 'hwax-share.ps1';
  const SHARE_FOOT = `<!-- ${SHARE_MARK}: 포털 설정 배치가 만든 파일 — 토큰 화면의 '내 Claude 대화를 포털에 공유' 칸을 끄고 배치를 다시 돌리면 지운다 -->`;
  const SHARE_CMD = [
    '---',
    'description: 지금 이 Claude Code 대화를 HWAX 포털의 내 기록으로 공유한다(원문은 본인과 지정 분석가만 본다)',
    '---',
    '사람이 이 대화를 HWAX 포털에 공유하라고 했다. 아래 한 줄을 셸 도구(PowerShell · Bash 어느 쪽이든)로 그대로 실행하고, 나온 줄을 사람에게 그대로 전한다.',
    '',
    'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "@@HWAX_SHARE_PS1@@" -SessionId "${CLAUDE_SESSION_ID}"',
    '',
    "1. '[O] 공유했습니다' 가 나오면 끝이다.",
    '2. 실패했고 hwax MCP 에 share_conversation 도구가 있으면, 사람에게 그 도구로 보낼지 묻고 그렇다면 이 대화의 사람 · 어시스턴트 글을 보낸다(session_id 는 이 세션 id).',
    '3. 둘 다 안 되면 나온 까닭을 그대로 전하고 멈춘다. 토큰 · 키를 대화에 옮겨 적지 않는다.',
    '',
    SHARE_FOOT,
    '',
  ].join('\n');
  // 글 가림(contract §4) — 서버(backend/app/interactions/redact.py)와 같은 꼴 · 같은 차례(PEM → 칸 이름 → Bearer → JWT). 줄마다 건다 —
  // 기록 파일은 JSONL 이라 한 글이 줄을 넘지 않고, 끝 표지 없는 PEM 이 파일의 나머지를 지우지 않게 PEM 의 '끝까지' 는 줄 끝까지다.
  // 서버가 줄마다 다시 가린다 — 이 가림은 토큰이 PC 를 떠나기 전에 한 번 더 지우는 것이다.
  const SHARE_RX: [string, string][] = [
    ['Pem', '-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----(?:.*?-----END [A-Z0-9 ]*PRIVATE KEY-----|.*)'],
    ['Kv', '"((?:[^"\\\\]|\\\\.)*?(?:authorization|token|access_token|refresh_token|api_key|apikey|x-api-key|secret|client_secret|password|passwd|cookie|set-cookie|session|private_key))"(\\s*:\\s*)"(?:[^"\\\\]|\\\\.)*"'],
    ['Bearer', '\\b([Bb][Ee][Aa][Rr][Ee][Rr])[ \\t]+[A-Za-z0-9\\-._~+/]+=*'],
    ['Jwt', '\\beyJ[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+'],
  ];
  const psQ = (s: string): string => `'${s.split("'").join("''")}'`;
  // 올리는 스크립트 — 파일로 두는 PowerShell(줄 여럿 · UTF-8 BOM 으로 쓴다 — 5.1 은 BOM 없는 .ps1 을 ANSI 로 읽어 한글이 깨진다).
  //   /hwax-share 는 -SessionId 로, SessionEnd 훅은 -Hook(표준입력의 transcript_path · session_id)으로 부른다. 세션 id 가 없거나 꼴이 아니면 지금
  //   폴더의 프로젝트 폴더에서 가장 새 기록 파일을 고른다. 토큰은 화면 · 로그에 내지 않는다 — 예외는 단계와 종류만, HTTP 는 상태 코드만 말한다.
  //   훅에서는 화면이 없어 결과를 %USERPROFILE%\.hwax\hwax-share.log 에 한 줄씩 남긴다.
  const sharePs1 = (): string =>
    [
      `# ${SHARE_MARK} — 포털 설정 배치가 만든 파일(토큰 화면 '내 Claude 대화를 포털에 공유'). 칸을 끄고 배치를 다시 돌리면 지운다.`,
      '# 지금 Claude Code 세션의 기록 파일(JSONL)을 HWAX 포털의 내 기록으로 올린다(POST /interactions/share — docs/interaction-data contract §5).',
      "param([string]$SessionId = '', [string]$Path = '', [switch]$Hook)",
      "$ErrorActionPreference = 'Stop'",
      'try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}',
      `$Portal = ${psQ(ORIGIN)}`,
      '$MaxBytes = 50MB',
      ...SHARE_RX.map(([k, v]) => `$rx${k} = ${psQ(v)}`),
      "$Prof = [Environment]::GetFolderPath('UserProfile'); if (-not $Prof) { $Prof = $env:USERPROFILE }",
      "$Log = [System.IO.Path]::Combine($Prof, '.hwax', 'hwax-share.log')",
      'function Say([string]$m) {',
      "  if ($Hook) { try { Add-Content -LiteralPath $Log -Value ((Get-Date -Format s) + ' ' + $m) -Encoding UTF8 } catch {} } else { Write-Output $m }",
      '}',
      "$step = 'path'",
      'try {',
      "  $d = [System.IO.Path]::Combine($Prof, '.claude'); $o = $Prof",
      '  if ($env:CLAUDE_CONFIG_DIR) { $d = $env:CLAUDE_CONFIG_DIR; $o = $env:CLAUDE_CONFIG_DIR }',
      '  Add-Type -AssemblyName System.Web.Extensions',
      '  $js = New-Object System.Web.Script.Serialization.JavaScriptSerializer; $js.MaxJsonLength = [int]::MaxValue',
      '  if ($Hook) {',
      "    $step = 'hook'",
      '    $in = $js.DeserializeObject([Console]::In.ReadToEnd())',
      '    if ($in -is [System.Collections.IDictionary]) {',
      "      if (-not $Path -and $in['transcript_path']) { $Path = [string]$in['transcript_path'] }",
      "      if (-not $SessionId -and $in['session_id']) { $SessionId = [string]$in['session_id'] }",
      '    }',
      '  }',
      "  if ($SessionId -notmatch '^[0-9A-Za-z][0-9A-Za-z_-]{7,}$') { $SessionId = '' }",
      "  $step = 'find'",
      "  $proj = [System.IO.Path]::Combine($d, 'projects')",
      '  if (-not $Path -and (Test-Path -LiteralPath $proj)) {',
      '    $dirs = @(Get-ChildItem -LiteralPath $proj -Directory -EA SilentlyContinue)',
      "    if ($SessionId) { foreach ($x in $dirs) { $c = [System.IO.Path]::Combine($x.FullName, $SessionId + '.jsonl'); if (Test-Path -LiteralPath $c) { $Path = $c; break } } }",
      '    if (-not $Path) {',
      "      $here = [System.IO.Path]::Combine($proj, ((Get-Location).Path -replace '[^A-Za-z0-9]', '-'))",
      '      $pool = $dirs; if (Test-Path -LiteralPath $here) { $pool = @(Get-Item -LiteralPath $here) }',
      "      $f = @($pool | ForEach-Object { Get-ChildItem -LiteralPath $_.FullName -Filter '*.jsonl' -File -EA SilentlyContinue } | Sort-Object LastWriteTime -Descending | Select-Object -First 1)",
      '      if ($f.Count -gt 0) { $Path = $f[0].FullName }',
      '    }',
      '  }',
      "  if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { Say '[X] 이 세션의 기록 파일을 찾지 못해 공유하지 않았습니다.'; exit 1 }",
      "  if ((Get-Item -LiteralPath $Path).Length -gt $MaxBytes) { Say '[X] 기록 파일이 50 MB 를 넘어 올리지 않았습니다.'; exit 1 }",
      '  if (-not $SessionId) { $SessionId = [System.IO.Path]::GetFileNameWithoutExtension($Path) }',
      "  $step = 'token'",
      "  $cf = [System.IO.Path]::Combine($d, '.config.json'); if (-not (Test-Path -LiteralPath $cf)) { $cf = [System.IO.Path]::Combine($o, '.claude.json') }",
      '  $auth = $null',
      '  if (Test-Path -LiteralPath $cf) {',
      '    $cj = $js.DeserializeObject([System.IO.File]::ReadAllText($cf, [System.Text.Encoding]::UTF8))',
      "    $hw = $null; if ($cj -is [System.Collections.IDictionary] -and $cj['mcpServers'] -is [System.Collections.IDictionary]) { $hw = $cj['mcpServers']['hwax'] }",
      '    if ($hw -is [System.Collections.IDictionary]) {',
      "      if ($hw['headers'] -is [System.Collections.IDictionary]) { $auth = [string]$hw['headers']['Authorization'] }",
      "      if (-not $auth -and $hw['env'] -is [System.Collections.IDictionary]) { $auth = [string]$hw['env']['AUTH'] }",
      '    }',
      '  }',
      "  if (-not $auth -or $auth -notlike 'Bearer *') { Say '[X] hwax 연결의 토큰을 찾지 못했습니다 - 토큰 화면의 설정 배치를 다시 실행하세요.'; exit 1 }",
      "  $step = 'read'",
      '  $text = [System.IO.File]::ReadAllText($Path, (New-Object System.Text.UTF8Encoding($false)))',
      "  $step = 'mask'",
      '  $ic = [System.Text.RegularExpressions.RegexOptions]::IgnoreCase',
      "  $lines = $text -split \"`n\"",
      '  for ($i = 0; $i -lt $lines.Count; $i++) {',
      '    $t = $lines[$i]',
      "    $t = [regex]::Replace($t, $rxPem, '<가림:pem>')",
      "    $t = [regex]::Replace($t, $rxKv, { param($m) '\"' + $m.Groups[1].Value + '\"' + $m.Groups[2].Value + '\"<가림:' + $m.Groups[1].Value.ToLower() + '>\"' }, $ic)",
      "    $t = [regex]::Replace($t, $rxBearer, '$1 <가림:bearer>')",
      "    $lines[$i] = [regex]::Replace($t, $rxJwt, '<가림:jwt>')",
      '  }',
      "  $text = $lines -join \"`n\"",
      "  $step = 'send'",
      '  $body = [System.Text.Encoding]::UTF8.GetBytes($js.Serialize(@{ session_id = $SessionId; transcript = $text }))',
      "  if ($body.Length -gt $MaxBytes) { Say '[X] 올릴 본문이 50 MB 를 넘어 올리지 않았습니다.'; exit 1 }",
      '  [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12',
      "  $q = [System.Net.HttpWebRequest]::Create($Portal.TrimEnd('/') + '/interactions/share')",
      "  $q.Method = 'POST'; $q.ContentType = 'application/json; charset=utf-8'; $q.Timeout = 120000; $q.ReadWriteTimeout = 120000",
      '  $q.Proxy = $null',
      "  $q.Headers.Add('Authorization', $auth)",
      // 포털 인증서를 배치가 두었으면(사내 공개 루트에 닿지 않는 박스 — [1]) 그 인증서로 고정해 받는다. 윈도우가 믿는 인증서면 그대로 받는다.
      "  $pin = [System.IO.Path]::Combine($Prof, '.hwax', 'hwax-portal.crt')",
      '  if (Test-Path -LiteralPath $pin) {',
      "    $step = 'pin'",
      "    if (-not ('HwaxSharePin' -as [type])) {",
      "      Add-Type -TypeDefinition @'",
      'using System; using System.Net.Security; using System.Security.Cryptography.X509Certificates;',
      'public static class HwaxSharePin {',
      '  public static X509Certificate2Collection Pins = new X509Certificate2Collection();',
      '  public static bool Check(object s, X509Certificate c, X509Chain ch, SslPolicyErrors e) {',
      '    if (e == SslPolicyErrors.None) return true;',
      '    if (c == null || Pins.Count == 0 || (e & SslPolicyErrors.RemoteCertificateNameMismatch) != 0) return false;',
      '    X509Certificate2 leaf = new X509Certificate2(c);',
      '    foreach (X509Certificate2 p in Pins) if (p.Thumbprint == leaf.Thumbprint) return true;',
      '    X509Chain x = new X509Chain();',
      '    x.ChainPolicy.RevocationMode = X509RevocationMode.NoCheck;',
      '    x.ChainPolicy.VerificationFlags = X509VerificationFlags.AllowUnknownCertificateAuthority;',
      '    x.ChainPolicy.ExtraStore.AddRange(Pins);',
      '    if (!x.Build(leaf)) return false;',
      '    X509Certificate2 root = x.ChainElements[x.ChainElements.Count - 1].Certificate;',
      '    foreach (X509Certificate2 p in Pins) if (p.Thumbprint == root.Thumbprint) return true;',
      '    return false;',
      '  }',
      '}',
      "'@",
      '    }',
      '    [HwaxSharePin]::Pins.Clear()',
      "    foreach ($mm in [regex]::Matches([System.IO.File]::ReadAllText($pin), '-----BEGIN CERTIFICATE-----([A-Za-z0-9+/=\\s]+)-----END CERTIFICATE-----')) {",
      "      [void][HwaxSharePin]::Pins.Add((New-Object System.Security.Cryptography.X509Certificates.X509Certificate2(,[Convert]::FromBase64String(($mm.Groups[1].Value -replace '\\s', '')))))",
      '    }',
      '    $q.ServerCertificateValidationCallback = [System.Net.Security.RemoteCertificateValidationCallback][HwaxSharePin]::Check',
      "    $step = 'send'",
      '  }',
      '  $w = $q.GetRequestStream(); $w.Write($body, 0, $body.Length); $w.Close()',
      '  $r = $q.GetResponse(); $rd = New-Object System.IO.StreamReader($r.GetResponseStream(), [System.Text.Encoding]::UTF8)',
      '  $res = $js.DeserializeObject($rd.ReadToEnd()); $r.Close()',
      "  $what = '덮어씀'; if ($res['created']) { $what = '새로' }",
      "  Say ('[O] 공유했습니다 - 메시지 ' + $res['messages'] + '개 · 세션 ' + $res['session_id'] + ' · ' + $what + '. 포털의 내 기록에서 봅니다.')",
      '  exit 0',
      '} catch {',
      '  $ex = $_.Exception; while ($ex -and -not ($ex -is [System.Net.WebException])) { $ex = $ex.InnerException }',
      '  if ($ex) {',
      '    $code = 0; if ($ex.Response) { $code = [int]$ex.Response.StatusCode }',
      "    $why = '포털이 HTTP ' + $code + ' 로 답했습니다.'",
      "    if ($code -eq 0) { $why = '포털에 닿지 못했습니다(주소 · 방화벽 · 인증서).' }",
      "    elseif ($code -eq 401) { $why = '토큰이 거부됐습니다(만료 또는 폐기) - 토큰 화면에서 새 토큰으로 배치를 다시 실행하세요.' }",
      "    elseif ($code -eq 404) { $why = '이 포털 박스는 상호작용 기록을 켜지 않았습니다.' }",
      "    elseif ($code -eq 413) { $why = '50 MB 상한을 넘었습니다.' }",
      "    Say ('[X] 공유하지 못했습니다 - ' + $why); exit 1",
      '  }',
      "  Say ('[X] 공유하지 못했습니다 - ' + $step + ' 단계에서 ' + $_.Exception.GetType().Name); exit 1",
      '}',
      '',
    ].join('\r\n');
  // cmd 의 한 줄은 8191자까지다 — 스크립트는 그보다 길어 base64 를 6000자 조각으로 나눠 HWAX_SHARE_PS1_00 · _01 … 에 싣고 PowerShell 이 이름 차례로 잇는다.
  const b64Sets = (name: string, s: string): string[] => {
    const all = b64(s);
    const out: string[] = [];
    for (let i = 0; i * 6000 < all.length; i++) out.push(`set "${name}_${String(i).padStart(2, '0')}=${all.slice(i * 6000, (i + 1) * 6000)}"`);
    return out;
  };
  /** 설정 배치 [5c] 의 PowerShell 한 줄 — off(걷기) · command(스크립트 + /hwax-share, 전에 단 훅은 걷는다) · auto(그리고 SessionEnd 훅).
   * 자리는 Claude Code 의 규칙(CLAUDE_CONFIG_DIR 이 있으면 그 아래, 없으면 <프로필 폴더>\.claude — 위 [5b] 와 같은 판정), 스크립트는 <프로필 폴더>\.hwax.
   * 파일은 표지 낱말(hwax-share)이 있는 것만 우리 것이다 — 같은 이름의 사람 파일은 덮지도 지우지도 않는다. settings.json 은 엄격한 UTF-8 JSON 객체로
   * 읽고(아니면 건드리지 않는다), SessionEnd 의 훅 가운데 명령 글에 hwax-share.ps1 이 든 것만 빼거나 넣고 나머지는 그대로 둔다. 바꿀 때는 Code 설정과
   * 같은 순서(백업 .hwax-bak → 임시 파일에 쓰고 되읽어 확인 → 바꿔 넣기). 걷기는 걷을 것이 있을 때만 말한다(켠 적 없는 PC 의 화면은 종전과 같다).
   * cmd 의 "…" 안이라 큰따옴표 · % · ! 를 글자로 두지 않는다 — 훅 명령의 따옴표는 [char]34, 느낌표는 [char]33 으로 짓는다. */
  const sharePs = (mode: 'off' | 'command' | 'auto'): string => {
    const readSettings = (always: boolean) => [
      "$s='settings';$x='';$w=$u;$j=$null;",
      'if(Test-Path -LiteralPath $sf){$bb=[System.IO.File]::ReadAllBytes($sf);',
      always ? '' : 'if($u.GetString($bb).Contains($hm)){',
      '$o2=0;if($bb.Length -ge 3 -and $bb[0] -eq 239 -and $bb[1] -eq 187 -and $bb[2] -eq 191){$o2=3;$w=New-Object System.Text.UTF8Encoding($true)};',
      '$x=$v.GetString($bb,$o2,($bb.Length - $o2));if($x.Trim()){$j=$js.DeserializeObject($x)}',
      always ? '};' : '}};',
    ];
    const auto = mode === 'auto';
    const merge = [
      `if(($j -ne $null) -and -not ($j -is [System.Collections.IDictionary])){throw 'shape'};if($j -eq $null){$j=${PS_DICT}};`,
      "$hk=$null;if($j.ContainsKey('hooks')){$hk=$j['hooks']};if(($hk -ne $null) -and -not ($hk -is [System.Collections.IDictionary])){throw 'shape'};",
      '$keep=@();$rm=0;',
      "if(($hk -ne $null) -and $hk.ContainsKey('SessionEnd')){foreach($gr in @($hk['SessionEnd'])){",
      "if(($gr -is [System.Collections.IDictionary]) -and $gr.ContainsKey('hooks')){$hs=@();foreach($e in @($gr['hooks'])){",
      "if(($e -is [System.Collections.IDictionary]) -and ([string]$e['command']).Contains($hm)){$rm++}else{$hs+=,$e}};",
      "if($hs.Count -gt 0){$gr['hooks']=[object[]]$hs;$keep+=,$gr}}else{$keep+=,$gr}}};",
      auto
        ? `$e=${PS_DICT};$e['type']='command';$e['command']='powershell.exe -NoProfile -ExecutionPolicy Bypass -File '+$q+$spf+$q+' -Hook';$e['timeout']=30;$gr=${PS_DICT};$gr['hooks']=[object[]]@($e);$keep+=,$gr;`
        : '',
      `if(($rm -gt 0) -or ${auto ? '$true' : '$false'}){`,
      `if($hk -eq $null){$hk=${PS_DICT};$j['hooks']=$hk};if($keep.Count -gt 0){$hk['SessionEnd']=[object[]]$keep}else{[void]$hk.Remove('SessionEnd')};if($hk.Count -eq 0){[void]$j.Remove('hooks')};`,
      "$y=$js.Serialize($j);$s='backup';if(Test-Path -LiteralPath $sf){Copy-Item -LiteralPath $sf -Destination ($sf+'.hwax-bak') -Force};[void][System.IO.Directory]::CreateDirectory($d);",
      "$t=$sf+'.hwax-tmp';$s='write';[System.IO.File]::WriteAllText($t,$y,$w);",
      "$s='verify';$r=$js.DeserializeObject([System.IO.File]::ReadAllText($t,$u));if($r.Count -ne $j.Count){throw 'mismatch'};",
      "$s='replace';[System.IO.File]::Copy($t,$sf,$true);Remove-Item -LiteralPath $t -Force -EA SilentlyContinue;$t=$null;",
      auto ? "Write-Host ('          세션 끝 훅: '+$sf)};" : '$g+=$sf};',
    ];
    const head = [
      "$ErrorActionPreference='Stop';$s='path';$t=$null;$bg=[string][char]33;$q=[string][char]34;$g=@();",
      'try{',
      "$h=[Environment]::GetFolderPath('UserProfile');if(-not $h){$h=$env:USERPROFILE};",
      "$d=[System.IO.Path]::Combine($h,'.claude');if($env:CLAUDE_CONFIG_DIR){$d=$env:CLAUDE_CONFIG_DIR};",
      "$cd=[System.IO.Path]::Combine($d,'commands');$hd=[System.IO.Path]::Combine($h,'.hwax');",
      "$sp=[System.IO.Path]::Combine($hd,'hwax-share.ps1');$cf=[System.IO.Path]::Combine($cd,'hwax-share.md');$sf=[System.IO.Path]::Combine($d,'settings.json');",
      '$u=New-Object System.Text.UTF8Encoding($false);$v=New-Object System.Text.UTF8Encoding($false,$true);',
      `$mk='${SHARE_MARK}';$hm='${SHARE_HOOK_MARK}';$spf=$sp.Replace([string][char]92,'/');`,
      PS_JSON,
    ];
    const body =
      mode === 'off'
        ? [
            "$s='script';if((Test-Path -LiteralPath $sp) -and ([System.IO.File]::ReadAllText($sp,$u).Contains($mk))){Remove-Item -LiteralPath $sp -Force;$g+=$sp};",
            "$s='command';if((Test-Path -LiteralPath $cf) -and ([System.IO.File]::ReadAllText($cf,$u).Contains($mk))){Remove-Item -LiteralPath $cf -Force;$g+=$cf};",
            ...readSettings(false),
            'if($j -ne $null){',
            ...merge,
            '};',
            "if($g.Count -gt 0){Write-Host '  [5c] 내 Claude 대화 공유 - 칸이 꺼져 있어 전에 넣은 스크립트 · 명령 · 훅을 걷었습니다';foreach($z in $g){Write-Host ('          '+$z)}};exit 0",
          ]
        : [
            "$s='script';",
            "if((Test-Path -LiteralPath $sp) -and -not ([System.IO.File]::ReadAllText($sp,$u).Contains($mk))){Write-Host ('          ['+$bg+'] 같은 이름의 다른 파일이 있어 두었습니다: '+$sp);exit 1};",
            "$b=(@(Get-ChildItem env: | Where-Object {$_.Name -like 'HWAX_SHARE_PS1_*'} | Sort-Object Name) | ForEach-Object {$_.Value}) -join '';",
            '[void][System.IO.Directory]::CreateDirectory($hd);',
            '[System.IO.File]::WriteAllText($sp,[System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b)),(New-Object System.Text.UTF8Encoding($true)));',
            "Write-Host ('          스크립트: '+$sp);",
            "$s='command';",
            "if((Test-Path -LiteralPath $cf) -and -not ([System.IO.File]::ReadAllText($cf,$u).Contains($mk))){Write-Host ('          ['+$bg+'] 같은 이름의 다른 파일이 있어 두었습니다: '+$cf)}",
            "else{[void][System.IO.Directory]::CreateDirectory($cd);[System.IO.File]::WriteAllText($cf,[System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:HWAX_SHARE_CMD)).Replace('@@HWAX_SHARE_PS1@@',$spf),$u);Write-Host ('          명령: '+$cf)};",
            ...readSettings(auto),
            auto ? '' : 'if($j -ne $null){',
            ...merge,
            auto ? '' : '};',
            "if($g.Count -gt 0){Write-Host '          전에 단 세션 끝 훅을 걷었습니다(자동 올리기 칸이 꺼져 있다)';foreach($z in $g){Write-Host ('          '+$z)}};exit 0",
          ];
    return [
      ...head,
      ...body,
      '}catch{if($t){Remove-Item -LiteralPath $t -Force -EA SilentlyContinue};',
      "if($s -eq 'settings'){Write-Host ('     ['+$bg+'] settings.json 을 UTF-8 JSON 객체로 읽지 못해 건드리지 않았습니다: '+$sf)}",
      "else{Write-Host ('     '+$s+' failed: '+$_.Exception.GetType().Name)};exit 1}",
    ]
      .filter((l) => l)
      .join(' ');
  };

  // 인증서 자리 — 배치와 화면의 '직접 설정' 안내가 같은 파일을 가리킨다(%USERPROFILE% 은 cmd 가 푼다).
  const CERT_DIR = '%USERPROFILE%\\.hwax';
  const CERT_FILE = `${CERT_DIR}\\hwax-portal.crt`;
  // NODE_EXTRA_CA_CERTS 가 가리키는 파일 — 포털 인증서 + 이 PC 의 윈도우 신뢰 저장소(회사 루트 인증서 포함). 파일 하나만 받으므로 묶는다.
  const CA_BUNDLE = `${CERT_DIR}\\hwax-ca-bundle.pem`;
  // 묶음 만드는 PowerShell 본문 — 배치([1])와 안내 ②가 같은 문장을 쓴다(10-20 요청 3, TB-D1). 경로는 환경변수
  //   HWAX_PORTAL_CRT(읽을 포털 인증서)로 받는다. 지문으로 겹침을 빼고 64자 줄로 PEM 을 쓴다. 끝에서 $seen.Count 가 0 이면 저장소를 못 읽은 것이다.
  const PS_BUNDLE_BODY = [
    // Cert: 드라이브는 이 모듈이 낸다 — -NoProfile 창에서 아직 안 올라왔을 수 있어 먼저 부른다(배치는 실패하면 catch → 포털 인증서만).
    'Import-Module Microsoft.PowerShell.Security;',
    '$sb=New-Object System.Text.StringBuilder;',
    '[void]$sb.Append([System.IO.File]::ReadAllText($env:HWAX_PORTAL_CRT));[void]$sb.Append([char]10);',
    '$seen=@{};',
    "foreach($st in @('Cert:\\LocalMachine\\Root','Cert:\\CurrentUser\\Root')){foreach($x in @(Get-ChildItem -Path $st -EA SilentlyContinue)){",
    'if($seen.ContainsKey($x.Thumbprint)){continue};$seen[$x.Thumbprint]=1;',
    "$b=[Convert]::ToBase64String($x.RawData);[void]$sb.Append('-----BEGIN CERTIFICATE-----'+[char]10);",
    'for($i=0;$i -lt $b.Length;$i+=64){[void]$sb.Append($b.Substring($i,[Math]::Min(64,$b.Length-$i))+[char]10)};',
    "[void]$sb.Append('-----END CERTIFICATE-----'+[char]10)}};",
  ];
  // BOM 없는 UTF-8 로 쓴다(종전 그대로).
  const PS_WRITE_BUNDLE =
    '[System.IO.File]::WriteAllText($env:HWAX_CA_FILE,$sb.ToString(),(New-Object System.Text.UTF8Encoding($false)));';

  // 설정 JSON 을 대소문자를 구분해 읽고 쓴다(10-20 요청 2, docs/token-bat TB-D2). 5.1 의 ConvertFrom-Json 은 NO_PROXY 와 no_proxy 처럼
  // 대소문자만 다른 키를 중복으로 보고 멈춘다. JavaScriptSerializer 는 .NET Framework 라 5.1 에 늘 있다 — 대신 한 줄 JSON 으로 쓴다.
  const PS_JSON =
    'Add-Type -AssemblyName System.Web.Extensions;$js=New-Object System.Web.Script.Serialization.JavaScriptSerializer;$js.MaxJsonLength=[int]::MaxValue;';
  const PS_DICT = "(New-Object 'System.Collections.Generic.Dictionary[string,object]')";

  /** `$m`(mcpServers 사전)의 hwax 항목을 고친다 — 이미 있으면 그것을 바탕으로(10-20 요청 4, TB-D3).
   * 토큰(AUTH)과 우리가 정하는 칸(명령 · 주소)만 바꾸고 손으로 넣은 env 는 남긴다. NO_PROXY · NODE_EXTRA_CA_CERTS 를 이미 적어 뒀으면 그 값을
   * 쓰되, 예전 배치가 넣은 포털 인증서 경로만 회사 인증서 묶음으로 바꾼다. 토큰 · 경로는 환경변수로만 받는다(HWAX_AUTH · HWAX_CERT ·
   * HWAX_NOPROXY) — 명령줄에 실으면 프로세스 목록에 남는다. withType 은 Claude Code 항목(`type: stdio`)이고 Desktop 항목에는 없다.
   * 결과 손잡이 머리는 늘 단다(P-1) — stdio 는 인자를 통째로 다시 쓰고, http 는 대소문자만 다른 옛 머리를 걷은 뒤 단다(손으로 남긴 다른 머리는 그대로). */
  function psMergeHwax(pem: boolean, withType: boolean, vv: string = VIEW_PORTAL): string {
    const copy = (src: string, dst: string) => `foreach($k in @(${src}.Keys)){${dst}[$k]=${src}[$k]};`;
    const head = [
      "$o=$null;if($m.ContainsKey('hwax')){$o=$m['hwax']};",
      `$e=${PS_DICT};if($o -is [System.Collections.IDictionary]){${copy('$o', '$e')}};`,
    ];
    if (pem) {
      return [
        ...head,
        withType ? "$e['type']='stdio';" : "if($e.ContainsKey('type')){[void]$e.Remove('type')};",
        "$e['command']='npx';",
        // [object[]] — 배열을 PowerShell 이 감싼 채로 넣으면 JavaScriptSerializer 가 배열이 아니라 객체로 쓴다. 맨 .NET 배열로 못 박는다.
        `$e['args']=[object[]]@('-y','mcp-remote','${MCP_URL}',${ALLOW_HTTP_ARR}'--header','Authorization:$\{AUTH}','--header','${VIEW_NAME}:${vv}','--header','${RESULT_NAME}:${RESULT_REF}');`,
        "foreach($k in @('url','headers')){if($e.ContainsKey($k)){[void]$e.Remove($k)}};",
        `$v=${PS_DICT};if($e.ContainsKey('env') -and ($e['env'] -is [System.Collections.IDictionary])){${copy("$e['env']", '$v')}};`,
        "$v['AUTH']=$env:HWAX_AUTH;",
        "$ca=@($v.Keys | Where-Object {$_ -ieq 'NODE_EXTRA_CA_CERTS'});",
        "if($ca.Count -eq 0){$v['NODE_EXTRA_CA_CERTS']=$env:HWAX_CERT}else{foreach($k in $ca){if([string]$v[$k] -like '*\\.hwax\\hwax-portal.crt'){$v[$k]=$env:HWAX_CERT}}};",
        "if(@($v.Keys | Where-Object {$_ -ieq 'NO_PROXY'}).Count -eq 0){$v['NO_PROXY']=$env:HWAX_NOPROXY};",
        "$e['env']=$v;$m['hwax']=$e;",
      ].join('');
    }
    return [
      ...head,
      "$e['type']='http';",
      `$e['url']='${MCP_URL}';`,
      "foreach($k in @('command','args','env')){if($e.ContainsKey($k)){[void]$e.Remove($k)}};",
      `$h=${PS_DICT};if($e.ContainsKey('headers') -and ($e['headers'] -is [System.Collections.IDictionary])){${copy("$e['headers']", '$h')}};`,
      // 보기 머리는 손으로 넣은 것(대소문자 무시)이 있으면 그대로 둔다 — 그 연결만의 보기를 고른 것이다. 목적 고정을 켰으면 사람이 이 화면에서 고른
      // 것이라 대소문자만 다른 것까지 걷고 그 값을 단다(고정을 끄고 다시 돌리면 남은 고정 머리는 그대로다 — 화면이 말한다).
      vv === VIEW_PORTAL
        ? `if(@($h.Keys | Where-Object {$_ -ieq '${VIEW_NAME}'}).Count -eq 0){$h['${VIEW_NAME}']='${VIEW_PORTAL}'};`
        : `foreach($k in @($h.Keys | Where-Object {$_ -ieq '${VIEW_NAME}'})){[void]$h.Remove($k)};$h['${VIEW_NAME}']='${vv}';`,
      // 결과 손잡이 머리 — 대소문자만 다른 것까지 먼저 걷고(사전이 대소문자를 가른다 — 둘이 겹쳐 남지 않게) 단다.
      `foreach($k in @($h.Keys | Where-Object {$_ -ieq '${RESULT_NAME}'})){[void]$h.Remove($k)};$h['${RESULT_NAME}']='${RESULT_REF}';`,
      "$h['Authorization']=$env:HWAX_AUTH;$e['headers']=$h;$m['hwax']=$e;",
    ].join('');
  }

  function claudeCodeSnippet(token: string, view?: string | null): string {
    return `claude mcp add -s user --transport http hwax ${MCP_URL} --header "Authorization: Bearer ${token}"${viewArg(viewValue(view))}${RESULT_ARG}`;
  }

  // 자체서명 인증서를 쓰는 동안의 등록 명령.
  // ⚠ `NODE_EXTRA_CA_CERTS=... claude mcp add --transport http ...` 는 듣지 않는다(실측).
  // --transport http 는 설정에 URL·헤더만 저장하고 환경변수를 담지 않아서, 등록 시점의 변수는
  // 정작 연결하는 시점(나중에 뜨는 Claude 프로세스)에 사라진다. stdio(mcp-remote) 형태는
  // -e 로 준 환경변수를 설정에 저장해 매 실행마다 적용하므로 이쪽을 쓴다.
  function claudeCodeSnippetSelfSigned(token: string, certPath: string, view?: string | null): string {
    return [
      `claude mcp add -s user hwax ^`,
      `  -e AUTH="Bearer ${token}" ^`,
      `  -e NODE_EXTRA_CA_CERTS=${certPath} ^`,
      `  -e NO_PROXY=${NOPROXY} ^`,
      `  -- npx -y mcp-remote ${MCP_URL}${ALLOW_HTTP} --header "Authorization:\${AUTH}"${viewArgRemote(viewValue(view))}${RESULT_ARG_REMOTE}`,
    ].join('\n');
  }

  /**
   * 윈도우 설치 배치파일 — 인증서를 심고 Claude 에 등록까지 한 번에 끝낸다.
   * 인증서 PEM 을 파일 안에 그대로 넣어 첨부파일이 하나로 끝나게 한다(PEM 은 텍스트다).
   * 이 파일은 토큰이 화면에 보이는 그 순간에만 만들 수 있다 — 서버는 평문 토큰을 보관하지 않는다.
   */
  // cmd 의 echo 로 **파일에 글자를 쓸 때** 리다이렉트·파이프·앰퍼샌드는 이스케이프해야 한다.
  // 안 하면 그 줄이 파일에 안 들어가고 지금 여기서 실행돼 버린다.
  const echoEsc = (s: string) => s.replace(/([&<>|^])/g, '^$1');

  /** `claude|gemini|codex mcp add` 를 **별도 .cmd 로 분리해 start /wait 로 격리 실행**한다.
   *
   * ⚠ 이게 없으면 배치가 그 줄에서 조용히 죽는다. 사내 PC 실측(2026-09-04 리포트): `claude mcp
   * add` 는 성공해서 ~/.claude.json 도 정상 수정되는데, **그것을 호출한 배치 프로세스가 다음
   * 줄로 못 넘어가고 끝난다.** 그래서 이후 [3] Desktop·[4] Gemini·[5] Codex·[6] 연결확인이
   * 통째로 실행되지 않는데 에러도 안 뜨고 프롬프트로 돌아가, 사용자는 "조용히 끝났나 보다"로
   * 오해한다. PAT 재발급 때 옛 토큰이 그대로 남는 사고가 여기서 나온다.
   * 원인은 claude(Node CLI)가 콘솔 모드를 건드리는 것으로 추정되며, 같은 명령을 터미널에
   * 직접 타이핑하면 100% 정상이다 — 즉 "배치 안에서 직접 호출"만 문제다.
   * 해결책은 실측으로 검증됐다: 임시 .cmd 로 떼어내 `start "" /wait cmd /c` 로 부르면 통과한다.
   *
   * 종료코드는 `%HWAX_RC%` 로 받는다(호출부가 이 변수를 읽는다). 임시 파일에는 PAT 가 평문으로
   * 들어가므로 실행 직후 지운다 — %TEMP% 에 토큰 사본을 남기지 않는다.
   */
  const isolatedCli = (varName: string, tmpFile: string, lines: string[]): string[] => [
    `set "${varName}=${tmpFile}"`,
    `if exist "%${varName}%" del "%${varName}%" >nul 2>nul`,
    ...lines.map((l) => `>>"%${varName}%" echo ${echoEsc(l)}`),
    `start "" /wait cmd /c "%${varName}%"`,
    'set "HWAX_RC=%errorlevel%"',
    `del "%${varName}%" >nul 2>nul`,
  ];

  function buildSetupBat(
    token: string,
    name: string,
    pem: string | null,
    proxy: string | null,
    offload = false,
    share: 'off' | 'command' | 'auto' = 'off',
    view: string | null = null,
  ): string {
    const CORP_PROXY = fallbackProxy(proxy);
    const vv = viewValue(view);
    const certDir = CERT_DIR;
    const certFile = CERT_FILE;
    const caFile = CA_BUNDLE;
    // 등록 뒤 "이 토큰으로 갱신됐는지" 를 되읽어 확인할 표식. 재발급했는데 옛 토큰이 그대로
    // 남는 것이 이 스크립트의 가장 조용한 실패라, 존재 확인만으로는 부족하다.
    const tokenTail = token.slice(-8);
    const L: string[] = [
      // ⚠ 첫 줄은 희생용이다. 아래에서 UTF-8 BOM 을 붙이는데, cmd.exe 가 그걸 첫 줄에
      // 섞어 읽으면 그 줄의 명령이 죽는다. 그게 '@echo off' 면 배치 전체가 echo 된 채로
      // 돌아 화면과 스크롤백에 PAT 평문이 두 번 찍힌다(실측: 사용자 콘솔 전량 노출).
      // 죽어도 무해한 rem 을 앞에 두고 '@echo off' 를 둘째 줄로 내린다.
      '@rem HWAX Portal setup',
      '@echo off',
      'setlocal',
      'chcp 65001 >nul',
      'echo.',
      'echo  HWAX 포털 - 개인 Claude 연결 설정',
      `echo  토큰 이름: ${name}`,
      // 목적 고정을 켰을 때만 — 이 PC 등록이 포털 설정을 따르지 않는다는 것을 돌리는 사람이 보게(끄면 종전 출력과 같다)
      ...(vv !== VIEW_PORTAL ? [`echo  개인 Claude 보기: 목적 고정(${vv}) — 포털 설정과 상관없이 이 목적만 싣는다`] : []),
      'echo.',
      // 평문 origin 이면 배치 첫머리에서 못 박는다. 조용히 진행하면 사용자는 인증서까지
      // 깔았으니 암호화된 줄 안다 — 실제로는 PAT 가 그대로 네트워크를 건넌다.
      ...(IS_PLAINTEXT
        ? [
            'echo  [!] 경고: 이 포털에 http 로 접속했습니다.',
            `echo      ${ORIGIN}`,
            'echo      아래 토큰이 암호화되지 않은 채 네트워크를 지나갑니다.',
            'echo      https 주소로 다시 접속해 새 토큰을 받는 것을 권합니다.',
            'echo.',
          ]
        : []),
      // ⚠ 관리자 권한으로 실행하면 %APPDATA%·%USERPROFILE%·%LOCALAPPDATA% 가 **관리자 프로필**을 가리킨다.
      //   그러면 Desktop 설정 폴더가 '없는 것' 으로 보이고(그 프로필엔 Claude 를 쓴 적이 없다), Claude Code 도
      //   못 찾고, 등록이 되더라도 평소 쓰는 계정에서는 보이지 않는다. 이 배치는 관리자 권한이 필요 없다 —
      //   인증서도 내 홈 폴더에만 쓴다. S-1-16-12288 은 High Mandatory Level SID 라 언어와 무관하다.
      'whoami /groups 2>nul | find "S-1-16-12288" >nul 2>nul',
      'if errorlevel 1 goto :not_admin',
      'echo  [!] 관리자 권한으로 실행 중입니다.',
      'echo      설정이 지금 사용자^(%USERNAME%^) 프로필에 들어갑니다. 평소 Claude 를 쓰는 계정과 다르면',
      'echo      등록해도 보이지 않습니다 - 관리자 권한 없이 그냥 더블클릭해 다시 실행하는 것을 권합니다.',
      'echo.',
      ':not_admin',
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
      // ⚠ 찌르는 곳은 무인증 /health 다. 종전엔 `/` 를 찔렀는데, 로그인이 필요한 루트가
      //   4xx/302 를 주면 Invoke-WebRequest 는 **예외를 던지고** catch 가 무조건 실패로
      //   처리해 "직접 연결 실패 → VPN 확인" 오탐이 매번 났다(리포트 §2: curl/openssl 로는
      //   붙는데 여기만 실패). 게다가 HTTP 응답을 받았다는 것 자체가 '연결됨' 의 증거이므로,
      //   catch 에서도 Response 가 있으면 도달로 판정한다.
      'powershell -NoProfile -Command "$ErrorActionPreference=\'SilentlyContinue\';' +
        '[System.Net.ServicePointManager]::ServerCertificateValidationCallback={$true};' +
        'try{[System.Net.WebRequest]::DefaultWebProxy=$null;' +
        `$r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 8 -Uri '${ORIGIN}/health';` +
        'if($r.StatusCode -ge 200){exit 0}else{exit 1}}' +
        'catch{if($_.Exception.Response){exit 0}else{exit 1}}"',
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
      // 에러가 'MCP 등록 실패' 로만 보인다. 미리 확인하고 없으면 사내 프록시(포털이 준 값)를 이 창에 세운다.
      'where npx >nul 2>nul',
      // 종전엔 npx 가 없으면 아무 말 없이 다음 단계로 갔다 — Node.js 없는 PC 에서는 이후
      // 등록이 전부 "왜 실패하는지 모르는 채로" 실패한다(리포트 §3). 사유를 알려 준다.
      'if errorlevel 1 goto :px_nonode',
      // ⚠ mcp-remote 로 레지스트리를 재지 않는다. `npx -y mcp-remote --version` 은
      // mcp-remote 가 --version 을 서버 URL 로 해석해 "Invalid URL" 로 죽는다 — 네트워크가
      // 멀쩡하고 패키지가 이미 받아져 있어도 종료코드 1 이다(실측). 그래서 이 검사는 항상
      // 실패했고, 늘 '레지스트리에 못 나갑니다' 를 찍고 사내 프록시를 강제로 걸었다.
      // 그 프록시에 닿지 못하는 PC 에서는 이어지는 npx 가 타임아웃 없이 매달렸고, 출력도
      // >nul 로 버려서 화면이 그냥 멈춘 것처럼 보였다(실사고).
      // 레지스트리에 직접, 시간 상한을 걸고 묻는다 — npx 를 안 쓰니 하위 도구의 CLI 취향에
      // 좌우되지 않고 응답이 없어도 반드시 끝난다.
      'powershell -NoProfile -Command "$ErrorActionPreference=\'SilentlyContinue\';' +
        'try{$r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 ' +
        '-Uri \'https://registry.npmjs.org/mcp-remote/latest\';' +
        'if($r.StatusCode -eq 200){exit 0}else{exit 1}}catch{exit 1}"',
      'if not errorlevel 1 goto :px_done',
      'if defined HTTPS_PROXY goto :px_npmfail',
      // 프록시를 세우기 전에 그 프록시로 실제로 나가지는지 먼저 본다. 안 되는데 세우면 이 창의
      // 이후 모든 npx 가 그 프록시로 끌려가 더 나빠진다 — 등록도 연결 시험도 같이 죽는다.
      // 포털이 사내 프록시를 주지 않았으면(박스에 HWAX_FALLBACK_PROXY 없음) 이 시도를 빼고 그렇다고 한 줄 남긴다.
      ...(CORP_PROXY
        ? [
            `echo      npm 레지스트리 직결 실패 - 사내 프록시^(${CORP_PROXY}^)로 시도합니다`,
            'powershell -NoProfile -Command "$ErrorActionPreference=\'SilentlyContinue\';' +
              `try{$px=New-Object System.Net.WebProxy('${CORP_PROXY}');` +
              '$r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 -Proxy $px ' +
              '-Uri \'https://registry.npmjs.org/mcp-remote/latest\';' +
              'if($r.StatusCode -eq 200){exit 0}else{exit 1}}catch{exit 1}"',
            'if errorlevel 1 goto :px_npmfail',
            `set HTTPS_PROXY=${CORP_PROXY}`,
            `set HTTP_PROXY=${CORP_PROXY}`,
            'echo      사내 프록시로 레지스트리 확인 - 이 창에 적용합니다',
            'goto :px_done',
          ]
        : [
            'echo      npm 레지스트리 직결 실패 - 포털이 준 사내 프록시 주소가 없거나 모양이 틀려 프록시로 다시 시도하지 않습니다',
          ]),
      ':px_npmfail',
      'echo      [!] npx 가 mcp-remote 를 받지 못했습니다.',
      'echo          프록시 뒤라면 관리자에게 npm 레지스트리 허용을 요청하세요.',
      'echo          ^(이 단계가 실패해도 Claude Desktop 등록 자체는 진행됩니다^)',
      'goto :px_done',
      ':px_nonode',
      'echo      [!] Node.js^(npx^)가 설치돼 있지 않습니다.',
      // 자체서명 구간은 mcp-remote 경유가 유일한 길이라 여기서 멈춘다. https 직결 구간은
      // Claude Code/Desktop 이 npx 없이도 붙으므로 경고만 하고 계속한다(등록을 막지 않는다).
      ...(pem
        ? [
            'echo          이 설정은 mcp-remote^(npx^)가 있어야 동작합니다.',
            'echo          Node.js 20 이상을 설치한 뒤 이 파일을 다시 실행하세요.',
            'echo          https://nodejs.org/',
            'echo.',
            'pause',
            'exit /b 1',
          ]
        : [
            'echo          Claude Code/Desktop 은 http 직결이라 없어도 등록됩니다.',
            'echo          Gemini/Codex 를 쓰신다면 Node.js 20 이상이 필요합니다. https://nodejs.org/',
          ]),
      'goto :px_done',
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
      // 회사 인증서(10-20 요청 3, TB-D1) — 사람마다 다른 경로를 묻지 않고 윈도우 신뢰 저장소에서 꺼낸다(Node 의 --use-system-ca 와 같은 효과).
      //   지문으로 겹침을 빼고 64자 줄로 PEM 을 쓴다. 못 읽으면 포털 인증서만 담아 종전과 같게 간다.
      const caPs = [
        "$ErrorActionPreference='Stop';",
        'try{',
        ...PS_BUNDLE_BODY,
        'if($seen.Count -eq 0){exit 1};',
        PS_WRITE_BUNDLE,
        "Write-Host ('     윈도우 신뢰 인증서 '+$seen.Count+'개를 포털 인증서와 묶었습니다');exit 0",
        '}catch{exit 1}',
      ].join(' ');
      L.push(
        `echo      ${certFile}`,
        `set "HWAX_PORTAL_CRT=${certFile}"`,
        `set "HWAX_CA_FILE=${caFile}"`,
        `powershell -NoProfile -ExecutionPolicy Bypass -Command "${caPs}"`,
        'if errorlevel 1 goto :ca_portal_only',
        `echo      ${caFile}`,
        'goto :ca_done',
        ':ca_portal_only',
        `copy /y "${certFile}" "${caFile}" >nul`,
        'echo      [!] 윈도우 인증서 저장소를 읽지 못해 포털 인증서만 씁니다 - 사내 프록시 뒤라면 npx 가 실패할 수 있습니다',
        ':ca_done',
        '',
      );
    }

    // ── 실행 중인 Claude Desktop 이면 아무것도 바꾸지 않고 멈춘다(10-20 요청 5) ─────────
    // 창만 닫으면 트레이에 남고, 종료될 때 자기 메모리의 옛 설정으로 파일을 덮어써 등록이 되돌아간다. Claude Code 사용자 설정도 같은 앱이 쓴다.
    // 경로로 Desktop 만 고른다 — 이름이 같은 Claude Code CLI(claude.exe)는 %USERPROFILE%\.local 아래라 걸리지 않는다. 남의 · 권한 높은
    // 프로세스는 경로가 비어 걸리지 않는다(그때는 아래 '켜져 있으면 끄고 다시' 안내가 남는다).
    L.push(
      `powershell -NoProfile -Command "$p=@(Get-Process -Name claude -EA SilentlyContinue | Where-Object {$_.Path -and ($_.Path -like '*\\AnthropicClaude\\*' -or $_.Path -like '*\\WindowsApps\\*')});if($p.Count -gt 0){exit 1};exit 0"`,
      'if not errorlevel 1 goto :desk_closed',
      'echo  [!] Claude Desktop 이 실행 중입니다 - 아무 설정도 바꾸지 않고 멈춥니다.',
      'echo      창만 닫으면 트레이^(작업 표시줄 오른쪽 아래^)에 남아 있다가, 종료할 때 예전 설정으로 다시 덮어씁니다.',
      'echo      트레이의 Claude 아이콘을 오른쪽 클릭해 종료^(Quit^)까지 한 뒤 이 파일을 다시 실행하세요.',
      'echo.',
      'pause',
      'exit /b 1',
      ':desk_closed',
      '',
    );

    // ⚠ 아래는 일부러 괄호 블록( if ... ( ... ) )을 쓰지 않고 goto 로 흐름을 만든다.
    // 괄호 안에 PowerShell 한 줄처럼 (, ), | 가 섞인 긴 명령을 넣으면 cmd 의 괄호 매칭이
    // 어긋나 "예기치 않음" 으로 죽는 사고가 잦다. 라벨 방식이 장황해도 깨지지 않는다.

    // ── Claude Code 사용자 설정(~/.claude.json) — claude 명령이 없을 때 직접 쓴다 ──────────
    // 데스크톱 앱 안에서 도는 Claude Code 는 Desktop 설정이 아니라 Claude Code 사용자 설정의 mcpServers 를 읽는다
    // (docs/sso-delegation D-9). 앱만 깐 사람은 PATH 에 claude 가 없어서 종전 판은 Code 등록을 건너뛰었다.
    // 항목 모양은 `claude mcp add -s user` 가 쓰는 것과 같게 한다(type 이 있는 것이 Desktop 항목과 다르다).
    //
    // 자리는 하나로 단정하지 않는다(D-11). Claude Code CLI(2.0.74 바이너리에서 확인)와 같은 규칙이다.
    //   폴더 D = CLAUDE_CONFIG_DIR, 없으면 <홈>\.claude. D\.config.json 이 있으면 그 파일(옛 위치),
    //   아니면 (CLAUDE_CONFIG_DIR, 없으면 <홈>)\.claude.json.
    // <홈> 은 %USERPROFILE% 를 그대로 믿지 않고 GetFolderPath('UserProfile') 로 묻는다(축소·관리자 환경 전례), 비면 %USERPROFILE%.
    // Claude Code 의 homedir 는 USERPROFILE 을 먼저 본다 — 이 창에서 둘이 다르면 그 사실을 찍는다(앱은 보통 프로필 폴더 쪽이다).
    // 이 판정을 cmd 에서 하지 않고 병합하는 PowerShell 안에서 한다 — 값을 cmd 로 되돌려 받으려면 `for /f … in (…)` 나
    // 임시 파일이 필요한데, 둘 다 Desktop 쪽에서 일부러 뺀 함정이다(괄호 파싱·한글 사용자명 코드페이지, bba1bd8).
    const ccjAuth = pem ? '$r.mcpServers.hwax.env.AUTH' : '$r.mcpServers.hwax.headers.Authorization';
    // Desktop 병합과 같은 방식(경로·토큰은 환경변수, 조립은 PowerShell, Stop + exit 1)에 넷을 더한다.
    // 이 파일은 Claude Code 의 큰 전역 상태라 깨지면 잃는 것이 많다.
    //   ① 읽기를 UTF-8 로 못 박는다 — 5.1 의 Get-Content 는 BOM 없는 파일을 ANSI 로 읽어 한글 경로 키를 깨뜨린 채 다시 쓴다.
    //      쓰기는 BOM 없는 UTF-8(Desktop 쪽과 같다) — Claude Code 가 JSON 으로 읽는 파일이다(2.0.74 는 BOM 을 떼고 읽지만 다른 판까지 믿지 않는다).
    //   ② 깊이는 100(5.1 의 상한) — 기본값 2 면 projects 아래가 문자열로 잘려 저장된다.
    //   ③ 임시 파일에 쓰고 되읽어 확인(최상위 키 수·토큰)한 뒤에야 원본을 바꾼다 — 실패하면 원본은 그대로다.
    //      5.1 의 ConvertFrom-Json 은 대소문자만 다른 키(projects 의 C:/… 와 c:/…)를 중복으로 보고 실패하는데, 그때도 읽기에서 멈춘다.
    //   ④ 예외 메시지를 찍지 않는다 — 5.1 의 ConvertFrom-Json 은 파싱 오류에 입력 전체를 붙여, 파일 속 토큰이 콘솔에 나온다.
    //      어느 단계에서 무슨 종류로 실패했는지만 찍는다. 화면에 나가는 것은 경로·판단·단계뿐이다.
    const ccjPs = [
      "$ErrorActionPreference='Stop';",
      "$s='path';$t=$null;$b=$null;",
      'try{',
      "$h=[Environment]::GetFolderPath('UserProfile');if(-not $h){$h=$env:USERPROFILE};",
      "$o=$h;$d=[System.IO.Path]::Combine($h,'.claude');",
      "if($env:CLAUDE_CONFIG_DIR){$o=$env:CLAUDE_CONFIG_DIR;$d=$o;Write-Host '          CLAUDE_CONFIG_DIR 가 있어 그 아래를 씁니다.'}",
      "elseif($env:USERPROFILE -and $env:USERPROFILE -ne $h){Write-Host ('          USERPROFILE('+$env:USERPROFILE+') 이 프로필 폴더와 달라 프로필 폴더 쪽을 씁니다.')};",
      "$c=[System.IO.Path]::Combine($d,'.config.json');",
      "if(Test-Path -LiteralPath $c){$w='옛 위치(.config.json)가 있어 Claude Code 가 그 파일을 읽습니다.'}",
      "else{$c=[System.IO.Path]::Combine($o,'.claude.json');",
      "if(Test-Path -LiteralPath $c){$w='있는 파일에 hwax 만 더합니다(다른 설정은 그대로).'}",
      "elseif(Test-Path -LiteralPath $d){$w='파일은 없고 .claude 폴더가 있어 새로 만듭니다.'}",
      "else{$w='Claude Code 를 쓴 흔적이 없어 새로 만듭니다 - 처음 켤 때 이 파일을 읽습니다.'}};",
      "Write-Host ('          설정 파일: '+$c);Write-Host ('          '+$w);",
      "$t=$c+'.hwax-tmp';$u=New-Object System.Text.UTF8Encoding($false);$s='read';",
      PS_JSON,
      "$j=$null;if(Test-Path -LiteralPath $c){$s='backup';$b=$c+'.hwax-bak';Copy-Item -LiteralPath $c -Destination $b -Force;Write-Host ('          백업: '+$b);$s='read';$x=[System.IO.File]::ReadAllText($c,$u);if($x.Trim()){$j=$js.DeserializeObject($x)}};",
      `if(-not ($j -is [System.Collections.IDictionary])){$j=${PS_DICT}};`,
      `if(-not $j.ContainsKey('mcpServers') -or -not ($j['mcpServers'] -is [System.Collections.IDictionary])){$j['mcpServers']=${PS_DICT}};`,
      "$m=$j['mcpServers'];",
      psMergeHwax(!!pem, true, vv),
      "$n=$j.Count;$s='write';",
      '[System.IO.File]::WriteAllText($t, $js.Serialize($j), $u);',
      "$s='verify';$r=$js.DeserializeObject([System.IO.File]::ReadAllText($t,$u));",
      `if($r.Count -ne $n -or ${ccjAuth} -cne $env:HWAX_AUTH){throw 'mismatch'};`,
      // 바꿔 넣은 뒤의 임시 파일 정리는 실패로 치지 않는다 — 이미 바뀌었는데 '실패' 라고 하면 거짓이다.
      "$s='replace';[System.IO.File]::Copy($t,$c,$true);Remove-Item -LiteralPath $t -Force -EA SilentlyContinue;",
      // $t 가 아직 없으면(자리 판정에서 실패) 지우지 않는다 — null 로 Remove-Item 을 부르면 catch 안에서 또 던져 아래 안내가 안 나간다.
      // 바꿔 넣기(Copy) 중에 멈췄을 때만 원본이 덜 바뀌었을 수 있다 — 그때는 '그대로' 라고 하지 않고 백업 자리를 준다.
      "exit 0}catch{if($t){Remove-Item -LiteralPath $t -Force -EA SilentlyContinue};",
      "Write-Host ('     '+$s+' failed: '+$_.Exception.GetType().Name);",
      "if($s -eq 'replace'){Write-Host '     파일을 바꾸다 멈췄을 수 있습니다.';if($b){Write-Host ('     원래 내용: '+$b)}}",
      "else{Write-Host '     원본 파일은 바꾸지 않았습니다.'};exit 1}",
    ].join(' ');

    // ── Claude Code — CLI 가 있으면 claude mcp add, 없으면 ~/.claude.json 에 직접 ─────────
    L.push(
      'echo  [2] Claude Code (CLI) 확인...',
      // ⚠ `where` 는 **PATH 에 있는 것만** 찾는다. 설치 프로그램은 실행 파일을 사용자 PATH 에
      //   넣는데, 그 변경은 **이미 열려 있던 셸·Explorer 세션에는 반영되지 않는다**(새 터미널이
      //   필요하다 — 공식 설치 문서). 그래서 방금 설치하고 배치를 더블클릭한 사람은 `where` 가
      //   실패하고, 예전 판은 그 상황에서 "Claude Desktop 만 쓰신다면 정상" 이라고 말했다.
      //   설치해 둔 사용자에게 정반대 안내다 — 실패가 성공처럼 보이는 그 부류다.
      //   PATH 가 아니라 **파일이 있느냐**로 다시 본다.
      'set "HWAX_CLAUDE="',
      'where claude >nul 2>nul',
      'if not errorlevel 1 set "HWAX_CLAUDE=claude"',
      'if defined HWAX_CLAUDE goto :cli_go',
      // 네이티브 설치 표준 위치(문서 명시). 실제 바이너리는 .local\\share\\claude\\versions 에
      // 버전별로 있고 이 경로가 그것을 가리킨다.
      'if exist "%USERPROFILE%\\.local\\bin\\claude.exe" set "HWAX_CLAUDE=%USERPROFILE%\\.local\\bin\\claude.exe"',
      'if defined HWAX_CLAUDE goto :cli_found',
      // npm 전역 설치(prefix 기본값). prefix 를 바꾼 사람은 여기 없고, 그건 PATH 에 있을 것이다.
      'if exist "%APPDATA%\\npm\\claude.cmd" set "HWAX_CLAUDE=%APPDATA%\\npm\\claude.cmd"',
      'if defined HWAX_CLAUDE goto :cli_found',
      'if exist "%APPDATA%\\npm\\claude.exe" set "HWAX_CLAUDE=%APPDATA%\\npm\\claude.exe"',
      'if defined HWAX_CLAUDE goto :cli_found',
      'goto :no_cli',
      ':cli_found',
      'echo      PATH 에는 없지만 설치돼 있습니다 - 그 경로로 진행합니다.',
      'echo          %HWAX_CLAUDE%',
      'echo          ^(설치 직후라면 새 터미널을 열어야 PATH 에 반영됩니다.^)',
      ':cli_go',
      // ⚠ 스코프는 user 다. `claude mcp add` 의 기본값은 local(그 폴더 전용)이라,
      // 배치를 다운로드 폴더에서 더블클릭하면 그 폴더에서만 hwax 가 뜬다 — 사용자는
      // '등록 완료' 를 보고 다른 데서 왜 안 보이는지 모른다(실사고). 같은 배치의
      // gemini 는 이미 -s user 였다 — 또 한쪽에만 적용된 원칙이다.
      // 이전 판이 local 에 남긴 것도 함께 치운다(안 그러면 그 폴더에서 둘이 겹친다).
      // ⚠ remove·add·get 은 전부 격리 .cmd 안에서 돈다 — isolatedCli 주석 참조.
      //   등록됐다는 것과 설정에 남았다는 것은 다르므로 되읽어 확인하고, 토큰 꼬리까지
      //   대조해 "갱신됐다" 를 구분한다(3 = 등록은 됐는데 갱신 확인 실패).
      ...isolatedCli('HWAX_CLI_CMD', '%TEMP%\\hwax-cli-setup.cmd', [
        '@echo off',
        // ⚠ `%%…%%` 로 쓴다 — 부모가 echo 할 때 확장하지 않고 **자식이 런타임에** 푼다.
        //   부모가 확장하면 경로에 & 같은 문자가 섞였을 때 echo 가 그 자리에서 깨진다.
        //   자식은 start 로 뜨므로 부모 환경을 그대로 물려받는다.
        '"%%HWAX_CLAUDE%%" mcp remove hwax -s local >nul 2>nul',
        '"%%HWAX_CLAUDE%%" mcp remove hwax -s user >nul 2>nul',
        pem
          ? `"%%HWAX_CLAUDE%%" mcp add -s user hwax -e AUTH="Bearer ${token}" -e NODE_EXTRA_CA_CERTS=${caFile} -e NO_PROXY=${NOPROXY} -- npx -y mcp-remote ${MCP_URL}${ALLOW_HTTP} --header "Authorization:${'${AUTH}'}"${viewArgRemote(vv)}${RESULT_ARG_REMOTE}`
          : `"%%HWAX_CLAUDE%%" mcp add -s user --transport http hwax ${MCP_URL} --header "Authorization: Bearer ${token}"${viewArg(vv)}${RESULT_ARG}`,
        'if errorlevel 1 exit /b 2',
        '"%%HWAX_CLAUDE%%" mcp get hwax >nul 2>nul',
        'if errorlevel 1 exit /b 1',
        `"%%HWAX_CLAUDE%%" mcp get hwax | findstr /C:"${tokenTail}" >nul`,
        'if errorlevel 1 exit /b 3',
        'exit /b 0',
      ]),
      'if "%HWAX_RC%"=="0" goto :cli_ok',
      'if "%HWAX_RC%"=="3" goto :cli_stale',
      'goto :cli_fail',
      ':cli_ok',
      'set HWAX_DONE=1',
      'echo      Claude Code 등록 완료 ^(토큰 갱신 확인됨^)',
      'goto :desktop',
      ':cli_stale',
      'set HWAX_DONE=1',
      'echo      Claude Code 등록됨 - 다만 토큰 갱신은 확인하지 못했습니다',
      'echo          확인: claude mcp get hwax',
      'goto :desktop',
      ':cli_fail',
      'echo      [X] Claude Code 등록 실패',
      'goto :desktop',
      ':no_cli',
      // 예전엔 여기서 "Claude Desktop 만 쓰신다면 이대로 정상" 이라고 하고 건너뛰었다. 데스크톱 앱 안의 Code 탭을 쓰는
      // 사람에게는 거짓이다 — 그 Code 는 이 파일을 읽는다(위 ccjPs 주석). 그래서 CLI 대신 파일에 직접 넣는다.
      // 터미널용 CLI 도 같은 파일의 사용자 범위를 읽으므로, 나중에 설치해도 다시 등록할 필요가 없다.
      // 토큰은 절대 화면에 찍지 않는다 — 환경변수로만 PowerShell 에 넘긴다.
      'echo      claude 명령을 찾지 못했습니다 - 설정 파일에 직접 등록합니다.',
      'echo          PATH 와 아래 위치를 모두 확인했습니다:',
      'echo            %USERPROFILE%\\.local\\bin\\claude.exe',
      'echo            %APPDATA%\\npm\\claude.cmd ^| claude.exe',
      // 어느 파일에 왜 쓰는지(설정 파일·판단·백업)는 PowerShell 이 고른 뒤 찍는다 — 위 ccjPs 주석.
      'echo          Claude Desktop 안에서 쓰는 Claude Code 는 Desktop 설정이 아니라 아래 파일을 읽습니다.',
      `set "HWAX_AUTH=Bearer ${token}"`,
      ...(pem ? [`set "HWAX_CERT=${caFile}"`, `set "HWAX_NOPROXY=${NOPROXY}"`] : []),
      `powershell -NoProfile -ExecutionPolicy Bypass -Command "${ccjPs}"`,
      'if errorlevel 1 goto :ccj_fail',
      'set HWAX_DONE=1',
      'echo      Claude Code 사용자 설정에 등록 완료',
      'echo          터미널용 Claude Code 를 나중에 설치해도 같은 파일을 읽어 hwax 가 그대로 보입니다.',
      // 켜져 있는 앱은 종료하면서 자기 메모리의 설정으로 이 파일을 덮어쓸 수 있다 — Desktop 설정과 같은 이유다.
      'echo          Claude Desktop 이나 Claude Code 가 켜져 있으면 완전히 종료한 뒤 다시 실행하세요.',
      'echo          ^(켜 둔 채 종료하면 예전 내용으로 덮일 수 있습니다 - 그때는 끈 상태에서 이 파일을 다시 실행하세요.^)',
      'goto :desktop',
      ':ccj_fail',
      // 원본이 그대로인지는 PowerShell 이 멈춘 단계로 말한다 — 여기서 단정하지 않는다.
      'echo      [X] Claude Code 사용자 설정 등록 실패 - 위 메시지 확인',
      'echo          Claude Desktop 과 Claude Code 를 완전히 종료한 뒤 이 파일을 다시 실행하세요.',
      'echo          그래도 안 되면 터미널용 Claude Code 를 설치하고^(https://claude.ai/install.ps1^)',
      'echo          새 터미널에서 토큰 페이지의 Claude Code 명령을 붙여넣으세요.',
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
    const deskAuth = pem ? '$r.mcpServers.hwax.env.AUTH' : '$r.mcpServers.hwax.headers.Authorization';
    // PowerShell 조각 안에서는 큰따옴표를 쓰지 않는다 — cmd 의 "..." 안에 들어가기 때문.
    // 자리 — cmd 가 고른 설치판 자리(HWAX_CFG) + Store 판 자리 `%LOCALAPPDATA%\Packages\Claude*\LocalCache\Roaming\Claude`(10-20 요청 1).
    //   Store 판은 설치판 자리를 읽지 않아 종전엔 '완료' 인데 hwax 가 안 보였다. 설정 폴더가 있는 곳마다 반영하고 어디를 고쳤는지 찍는다.
    // 파일마다 Claude Code 쪽과 같은 순서다 — 백업(.bak) → 대소문자 구분으로 읽기 → 병합 → 임시 파일에 쓰고 되읽어 확인 → 바꿔 넣기.
    //   예외 메시지는 찍지 않는다(파싱 오류에 파일 내용 · 토큰이 붙을 수 있다) — 단계와 종류만.
    const ps = [
      "$ErrorActionPreference='Stop';",
      'try{',
      PS_JSON,
      '$u=New-Object System.Text.UTF8Encoding($false);',
      "$cs=@($env:HWAX_CFG);$pk=$null;if($env:LOCALAPPDATA){$pk=[System.IO.Path]::Combine($env:LOCALAPPDATA,'Packages')};",
      "if($pk -and (Test-Path -LiteralPath $pk)){foreach($p in @(Get-ChildItem -LiteralPath $pk -Directory -Filter 'Claude*' -EA SilentlyContinue)){$d=[System.IO.Path]::Combine($p.FullName,'LocalCache','Roaming','Claude');if(Test-Path -LiteralPath $d){$cs+=[System.IO.Path]::Combine($d,'claude_desktop_config.json')}}};",
      '$bad=0;',
      "foreach($c in $cs){$s='read';$t=$null;try{",
      "Write-Host ('          '+$c);",
      "$j=$null;if(Test-Path -LiteralPath $c){$s='backup';Copy-Item -LiteralPath $c -Destination ($c+'.bak') -Force;$s='read';$x=[System.IO.File]::ReadAllText($c,$u);if($x.Trim()){$j=$js.DeserializeObject($x)}};",
      `if(-not ($j -is [System.Collections.IDictionary])){$j=${PS_DICT}};`,
      `if(-not $j.ContainsKey('mcpServers') -or -not ($j['mcpServers'] -is [System.Collections.IDictionary])){$j['mcpServers']=${PS_DICT}};`,
      "$m=$j['mcpServers'];",
      psMergeHwax(!!pem, false, vv),
      "$n=$j.Count;$t=$c+'.hwax-tmp';$s='write';[System.IO.File]::WriteAllText($t,$js.Serialize($j),$u);",
      `$s='verify';$r=$js.DeserializeObject([System.IO.File]::ReadAllText($t,$u));if($r.Count -ne $n -or ${deskAuth} -cne $env:HWAX_AUTH){throw 'mismatch'};`,
      "$s='replace';[System.IO.File]::Copy($t,$c,$true);Remove-Item -LiteralPath $t -Force -EA SilentlyContinue;Write-Host '            등록 완료'",
      "}catch{$bad=1;if($t){Remove-Item -LiteralPath $t -Force -EA SilentlyContinue};Write-Host ('            [X] '+$s+' failed: '+$_.Exception.GetType().Name)}};",
      'if($bad){exit 1};exit 0',
      "}catch{Write-Host ('     failed: '+$_.Exception.GetType().Name);exit 1}",
    ].join(' ');
    L.push(
      ':desktop',
      'echo  [3] Claude Desktop 확인...',
      // ⚠ Roaming 경로를 %APPDATA% **하나로만** 믿지 않는다 — 축소된 환경(서비스·일부 원격 도구)에서는 비어 있어
      //   경로가 `\Claude` 가 되고, 기업 폴더 리디렉션이 오프라인이면 설정돼 있어도 닿지 않는다. 둘 다 '폴더 없음' 으로 보인다.
      //   **존재까지 확인**하고 아니면 프로필에서 직접 짚는다. PowerShell 로 알려진 폴더를 묻는 방법도 있지만
      //   `for /f ... in (\`…\`)` 안의 괄호는 cmd 의 `in (` 를 먼저 닫아 버리고, 임시파일로 우회하면 한글 사용자명이
      //   코드페이지에서 깨질 수 있다 — 그 위험을 지려면 실제 Windows 에서 재봐야 하므로 지금은 쓰지 않는다.
      'set "HWAX_ROAMING=%APPDATA%"',
      'if not defined HWAX_ROAMING set "HWAX_ROAMING=%USERPROFILE%\\AppData\\Roaming"',
      'if not exist "%HWAX_ROAMING%\\" set "HWAX_ROAMING=%USERPROFILE%\\AppData\\Roaming"',
      'set "HWAX_DESKDIR=%HWAX_ROAMING%\\Claude"',
      'set "HWAX_CFG=%HWAX_DESKDIR%\\claude_desktop_config.json"',
      // 어디를 봤는지 반드시 찍는다 — 종전엔 '폴더 없음' 만 말해 어느 경로를 본 것인지 알 수 없었다.
      'echo      설치판 설정 자리: %HWAX_CFG%',
      'if exist "%HWAX_DESKDIR%\\" goto :desktop_write',
      // ⚠ 여기가 사용자가 만난 '설정 폴더 없음 - 건너뜀' 자리다. 그 폴더는 Claude Desktop 을 **한 번
      //   실행했을 때** 만들어진다 — 설치만 해 둔 사람(또는 방금 설치한 사람)은 종전 판에서 영영 등록이
      //   안 됐고, 나중에 Desktop 을 켜도 연결이 없었다. 폴더 하나 만드는 것은 무해하고(Desktop 은 있으면
      //   읽고 없으면 만든다), 아직 설치하지 않았더라도 설치 직후 바로 붙는다. 그래서 만들고 등록한다.
      'set "HWAX_DESKAPP="',
      // 설치 흔적 — 맞히면 문구가 정확해지고, 못 맞혀도 등록은 그대로 한다(설치 경로가 문서화돼 있지 않아 단정하지 않는다).
      'if exist "%LOCALAPPDATA%\\AnthropicClaude\\claude.exe" set "HWAX_DESKAPP=1"',
      'for /d %%D in ("%LOCALAPPDATA%\\AnthropicClaude\\app-*") do if exist "%%D\\claude.exe" set "HWAX_DESKAPP=1"',
      'if exist "%HWAX_ROAMING%\\Microsoft\\Windows\\Start Menu\\Programs\\Claude.lnk" set "HWAX_DESKAPP=1"',
      'if exist "%PROGRAMDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Claude.lnk" set "HWAX_DESKAPP=1"',
      'mkdir "%HWAX_DESKDIR%" >nul 2>nul',
      'if not exist "%HWAX_DESKDIR%\\" goto :no_desktop',
      'if defined HWAX_DESKAPP goto :desktop_made',
      'echo      Claude Desktop 설치를 못 찾았습니다 - 설정만 미리 넣어 둡니다',
      'echo          ^(설치한 뒤 Desktop 을 켜면 바로 hwax 가 보입니다^)',
      'goto :desktop_write',
      ':desktop_made',
      'echo      설정 폴더가 없어 새로 만들었습니다 ^(Desktop 을 아직 한 번도 실행하지 않은 경우입니다^)',
      ':desktop_write',
      `set "HWAX_AUTH=Bearer ${token}"`,
      ...(pem ? [`set "HWAX_CERT=${caFile}"`, `set "HWAX_NOPROXY=${NOPROXY}"`] : []),
      'echo      고치는 파일^(Store 판 자리가 있으면 그것도^):',
      `powershell -NoProfile -ExecutionPolicy Bypass -Command "${ps}"`,
      'if errorlevel 1 goto :desktop_fail',
      'set HWAX_DONE=1',
      'echo      Claude Desktop 등록 완료 ^(기존 설정은 .bak 으로 백업^)',
      // Desktop 이 켜져 있으면 종료할 때 자기 메모리의 설정으로 이 파일을 덮어쓸 수 있다 — 먼저 끄고 다시 켜야 한다.
      'echo          Desktop 이 켜져 있으면 완전히 종료한 뒤 다시 실행하세요.',
      'goto :desktop_done',
      ':desktop_fail',
      'echo      [X] Desktop 설정 수정 실패 - 위 메시지 확인 ^(원본은 .bak 에 그대로 있습니다^)',
      'goto :desktop_done',
      ':no_desktop',
      // 이제 '폴더가 없다' 로는 오지 않는다 — 만들려고 했는데 **못 만든** 경우만 온다. 그러니 원인을 짚는다.
      'echo      [X] Claude Desktop 설정 폴더를 만들 수 없습니다 - 건너뜀',
      'echo          위 경로에 쓸 수 없습니다. 네트워크 드라이브^(기업 폴더 리디렉션^)면 연결을,',
      'echo          관리자 권한으로 실행 중이면 권한 없이 다시 실행하는 것을 확인하세요.',
      ':desktop_done',
      '',
    );

    // ── Gemini CLI ────────────────────────────────────────────────────────────
    // ⚠ `gemini mcp add` 는 --header 를 **자기 옵션으로 먹는다**(실측: args 에서 통째로 사라져
    // 인증 없이 등록됨 → 401). npx 뒤에 `--` 를 넣어야 나머지가 서버 인자로 넘어간다(실측 확인).
    const gemEnv = pem
      ? `-e AUTH="Bearer ${token}" -e NODE_EXTRA_CA_CERTS=${caFile}`
      : `-e AUTH="Bearer ${token}"`;
    L.push(
      ':gemini',
      'echo  [4] Gemini CLI 확인...',
      'where gemini >nul 2>nul',
      'if errorlevel 1 goto :no_gemini',
      // claude 와 같은 이유로 격리 실행한다 — gemini 도 Node CLI 라 배치를 끊는다(리포트 §1 후속).
      ...isolatedCli('HWAX_GEM_CMD', '%TEMP%\\hwax-gemini-setup.cmd', [
        '@echo off',
        'gemini mcp remove hwax -s user >nul 2>nul',
        `gemini mcp add -s user -t stdio ${gemEnv} hwax npx -- -y mcp-remote ${MCP_URL}${ALLOW_HTTP} --header "Authorization:${'${AUTH}'}"`,
      ]),
      'if not "%HWAX_RC%"=="0" goto :gemini_fail',
      'set HWAX_DONE=1',
      'echo      Gemini CLI 등록 완료',
      // 등록이 됐는데도 목록에 안 뜨는 사례가 있다 — 아래 폴더 신뢰 정책 때문이다.
      // "완료" 만 찍고 끝내면 사용자는 이 배치를 의심한다. 한 줄로 미리 짚어 준다.
      'echo          ^(gemini mcp list 에 안 보이면 폴더 신뢰 설정을 확인하세요.^)',
      'goto :codex',
      ':gemini_fail',
      // ⚠ 이 실패는 이 배치의 버그가 아닐 수 있다. Gemini CLI 는 **신뢰하지 않는 폴더**에서
      // user 범위 MCP 서버를 끄거나 숨긴다(사용자 실측 2026-09-04: 격리 패치로 배치는 안
      // 죽는데 등록만 실패/Disabled 로 보임). 사유를 짚지 않으면 사용자가 원인을 못 찾는다.
      'echo      [X] Gemini CLI 등록 실패',
      'echo          Gemini CLI 는 신뢰하지 않는 폴더에서 user 범위 MCP 서버를 끄거나 숨깁니다.',
      'echo          ^(다운로드 폴더에서 바로 실행하면 특히 그렇습니다.^)',
      'echo          gemini mcp list 로 hwax 가 보이는지 확인하고, 안 보이거나 Disabled 면',
      'echo          Gemini CLI 에서 이 폴더를 신뢰하도록 설정한 뒤 다시 실행하세요.',
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
      ? `--env AUTH="Bearer ${token}" --env NODE_EXTRA_CA_CERTS=${caFile}`
      : `--env AUTH="Bearer ${token}"`;
    const codexToml = [
      '[mcp_servers.hwax]',
      'command = "npx"',
      `args = ["-y", "mcp-remote", "${MCP_URL}"${ALLOW_HTTP_TOML}, "--header", "Authorization:\${AUTH}"]`,
      '',
      '[mcp_servers.hwax.env]',
      `AUTH = "Bearer ${token}"`,
      // TOML 리터럴 문자열(홑따옴표)은 이스케이프를 처리하지 않으므로 경로를 그대로 쓴다.
      // 큰따옴표 + 백슬래시 이중화는 Desktop JSON 과 똑같은 함정에 빠진다 — 배치가 echo 할 때
      // %USERPROFILE% 이 확장되면서 홑/겹 백슬래시가 섞여 \U 가 되고 TOML 파싱이 깨진다.
      ...(pem ? [`NODE_EXTRA_CA_CERTS = '${caFile}'`] : []),
    ];
    L.push(
      ':codex',
      'echo  [5] Codex CLI 확인...',
      'where codex >nul 2>nul',
      'if errorlevel 1 goto :no_codex',
      // claude 와 같은 이유로 격리 실행한다 — codex 도 Node CLI 다(리포트 §1 후속).
      ...isolatedCli('HWAX_CDX_CMD', '%TEMP%\\hwax-codex-setup.cmd', [
        '@echo off',
        'codex mcp remove hwax >nul 2>nul',
        `codex mcp add hwax ${codexEnv} -- npx -y mcp-remote ${MCP_URL}${ALLOW_HTTP} --header "Authorization:${'${AUTH}'}"`,
      ]),
      'if not "%HWAX_RC%"=="0" goto :codex_manual',
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

    // ── [5b] 서버 LLM 에 일 맡기기(토큰 절감 2판 E — docs/token-saving/offload-v2.md 3-4) ─────────────────────────
    // 칸을 켜면 Claude Code 사용자 명령 둘(/hwax-ask · /hwax-draft)과 사용자 CLAUDE.md 의 규칙 묶음(표지 두 줄 사이)을 넣고, 끄면 걷는다.
    // 자리는 Claude Code 의 규칙 — CLAUDE_CONFIG_DIR 이 있으면 그 아래, 없으면 <프로필 폴더>\.claude(위 ccjPs 의 폴더 D 와 같은 판정).
    // 꺼진 배치의 걷기는 걷을 것이 있을 때만 말한다 — 칸을 켠 적 없는 PC 에서는 화면이 종전과 같다(그래서 꺼진 쪽은 머리 줄도 PowerShell 이 찍는다).
    // 글(명령 · 규칙)은 base64 환경변수로 넘긴다(위 b64). 경로 · 조립은 PowerShell, Stop + exit 1, 예외는 단계와 종류만 찍는다(Code · Desktop 병합과 같다).
    // CLAUDE.md 는 엄격한 UTF-8 로 읽는다 — 못 읽으면 건드리지 않는다(5.1 이 ANSI 로 읽은 글을 다시 쓰면 사람이 쓴 한글이 깨진다). BOM 은 있던 대로 둔다.
    // 바꿀 때는 Code 설정과 같은 순서 — 백업(.hwax-bak) → 임시 파일에 쓰고 되읽어 확인 → 바꿔 넣기.
    // ⚠ 이 줄에는 `!` 를 글자로 두지 않는다 — 지연 확장(레지스트리 DelayedExpansion)이 켜진 PC 의 cmd 는 한 줄 안의 `!…!` 짝을 변수로 풀어 그 사이를
    //   지운다(표지 둘의 `<!--` 가 짝이 된다). 홀로 쓴 `!` 는 그 글자만 빠져 무해해 다른 줄은 그대로 둔다. PowerShell 이 $bg([char]33)로 짓는다.
    const psBang = (s: string): string => `'${s.split('!').join("'+$bg+'")}'`;
    const offPs = (on: boolean): string => {
      const read = [
        // $f 는 CLAUDE.md, $x 는 그 글(BOM 뺀), $w 는 다시 쓸 인코딩(BOM 이 있던 파일은 BOM 째로)
        "$f=[System.IO.Path]::Combine($d,'CLAUDE.md');$x='';$w=$u;",
        'if(Test-Path -LiteralPath $f){$bb=[System.IO.File]::ReadAllBytes($f);',
        // 꺼진 배치 — 표지가 없으면 읽기부터 하지 않는다(UTF-8 이 아닌 파일이어도 칸을 켠 적 없는 PC 에서는 아무 말도 하지 않게)
        on ? '' : 'if($u.GetString($bb).Contains($mb)){',
        '$o=0;if($bb.Length -ge 3 -and $bb[0] -eq 239 -and $bb[1] -eq 187 -and $bb[2] -eq 191){$o=3;$w=New-Object System.Text.UTF8Encoding($true)};',
        '$x=$v.GetString($bb,$o,($bb.Length - $o))',
        on ? '};' : '}};',
        "$i=$x.IndexOf($mb,$oc);$k=-1;if($i -ge 0){$k=$x.IndexOf($me,$i,$oc)};if($i -ge 0 -and $k -lt 0){$s='marker';throw 'marker'};",
      ];
      const write = [
        "$s='backup';if(Test-Path -LiteralPath $f){Copy-Item -LiteralPath $f -Destination ($f+'.hwax-bak') -Force};[void][System.IO.Directory]::CreateDirectory($d);",
        "$t=$f+'.hwax-tmp';$s='write';[System.IO.File]::WriteAllText($t,$y,$w);",
        "$s='verify';if([System.IO.File]::ReadAllText($t,$u) -cne $y){throw 'mismatch'};",
        "$s='replace';[System.IO.File]::Copy($t,$f,$true);Remove-Item -LiteralPath $t -Force -EA SilentlyContinue;$t=$null;",
      ];
      const body = on
        ? [
            "$s='commands';",
            "foreach($p in @(@('hwax-ask',$env:HWAX_OFF_ASK),@('hwax-draft',$env:HWAX_OFF_DRAFT))){$f=[System.IO.Path]::Combine($cd,$p[0]+'.md');",
            `if((Test-Path -LiteralPath $f) -and -not ([System.IO.File]::ReadAllText($f,$u).Contains('${OFFLOAD_MARK}'))){Write-Host ('          ['+$bg+'] 같은 이름의 다른 파일이 있어 두었습니다: '+$f);continue};`,
            '[void][System.IO.Directory]::CreateDirectory($cd);',
            '[System.IO.File]::WriteAllText($f,[System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($p[1])),$u);',
            "Write-Host ('          명령: '+$f)};",
            "$s='read';",
            ...read,
            // 줄바꿈은 그 파일의 것을 따른다 — LF 만 쓰는 파일이면 LF, 아니면 CRLF(새 파일 포함)
            "$s='rules';$nl=$crlf;if($x.Contains($lf) -and -not $x.Contains($crlf)){$nl=$lf};",
            '$r=[System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:HWAX_OFF_RULES)).Replace($lf,$nl);$b=$mb+$nl+$r+$nl+$me;',
            // 표지가 있으면 그 사이만 바꾸고, 없으면 끝에 붙인다(끝 줄에 줄바꿈이 없으면 하나 넣고)
            'if($i -ge 0){$y=$x.Substring(0,$i)+$b+$x.Substring($k+$me.Length)}else{$y=$x;if($y.Length -gt 0 -and -not $y.EndsWith($lf,$oc)){$y+=$nl};$y+=$b+$nl};',
            'if($y -cne $x){',
            ...write,
            '};',
            "Write-Host ('          규칙 묶음: '+$f);exit 0",
          ]
        : [
            "$g=@();$s='commands';",
            // 우리가 만든 명령만 지운다 — 끝 줄의 표지로 가른다(같은 이름의 사람 파일은 그대로)
            `foreach($n in @('hwax-ask','hwax-draft')){$f=[System.IO.Path]::Combine($cd,$n+'.md');if((Test-Path -LiteralPath $f) -and ([System.IO.File]::ReadAllText($f,$u).Contains('${OFFLOAD_MARK}'))){Remove-Item -LiteralPath $f -Force;$g+=$f}};`,
            "$s='read';",
            ...read,
            // 표지 두 줄과 그 사이, 끝 표지 뒤의 줄바꿈 하나를 걷는다 — 그 밖은 바이트 그대로. 남는 것이 없으면(우리 묶음뿐이던 파일) 파일을 지운다(백업은 남긴다).
            'if($i -ge 0){$z=$x.Substring($k+$me.Length);if($z.StartsWith($crlf,$oc)){$z=$z.Substring(2)}elseif($z.StartsWith($lf,$oc)){$z=$z.Substring(1)};$y=$x.Substring(0,$i)+$z;',
            "if($y.Length -eq 0){$s='backup';Copy-Item -LiteralPath $f -Destination ($f+'.hwax-bak') -Force;$s='remove';Remove-Item -LiteralPath $f -Force}else{",
            ...write,
            '};$g+=$f};',
            "if($g.Count -gt 0){Write-Host '  [5b] 서버 LLM 에 일 맡기기 - 칸이 꺼져 있어 전에 넣은 명령 · 규칙을 걷었습니다';foreach($q in $g){Write-Host ('          '+$q)}};exit 0",
          ];
      return [
        "$ErrorActionPreference='Stop';$s='path';$t=$null;$f=$null;$bg=[string][char]33;",
        'try{',
        "$h=[Environment]::GetFolderPath('UserProfile');if(-not $h){$h=$env:USERPROFILE};",
        "$d=[System.IO.Path]::Combine($h,'.claude');if($env:CLAUDE_CONFIG_DIR){$d=$env:CLAUDE_CONFIG_DIR};",
        "$cd=[System.IO.Path]::Combine($d,'commands');",
        '$u=New-Object System.Text.UTF8Encoding($false);$v=New-Object System.Text.UTF8Encoding($false,$true);$oc=[StringComparison]::Ordinal;',
        `$mb=${psBang(OFFLOAD_BEGIN)};$me=${psBang(OFFLOAD_END)};$lf=[string][char]10;$crlf=[string][char]13+[char]10;`,
        ...body,
        '}catch{if($t){Remove-Item -LiteralPath $t -Force -EA SilentlyContinue};',
        "if($s -eq 'marker'){Write-Host ('     ['+$bg+'] CLAUDE.md 에 시작 표지만 있고 끝 표지가 없어 건드리지 않았습니다: '+$f)}",
        "elseif($s -eq 'read'){Write-Host ('     ['+$bg+'] CLAUDE.md 를 UTF-8 로 읽지 못해 건드리지 않았습니다: '+$f)}",
        "else{Write-Host ('     '+$s+' failed: '+$_.Exception.GetType().Name)};exit 1}",
      ]
        .filter((l) => l)
        .join(' ');
    };
    L.push(
      ...(offload
        ? [
            'echo  [5b] 서버 LLM 에 일 맡기기 - Claude Code 명령 /hwax-ask · /hwax-draft 와 CLAUDE.md 규칙 묶음',
            `set "HWAX_OFF_ASK=${b64(OFFLOAD_ASK)}"`,
            `set "HWAX_OFF_DRAFT=${b64(OFFLOAD_DRAFT)}"`,
            `set "HWAX_OFF_RULES=${b64(OFFLOAD_RULES)}"`,
            `powershell -NoProfile -ExecutionPolicy Bypass -Command "${offPs(true)}"`,
            'if errorlevel 1 echo      [!] 명령 · 규칙을 다 넣지 못했습니다 - 위 메시지 확인. MCP 등록은 그대로 끝났습니다.',
            'echo          Claude Code 를 새로 열면 /hwax-ask · /hwax-draft 가 보입니다. 이 포털 박스에서 기능이 꺼져 있으면 명령이 그렇다고 말하고 멈춥니다.',
            'echo          걷으려면 토큰 화면에서 칸을 끄고 받은 배치를 다시 실행하세요 - CLAUDE.md 는 표지 두 줄 사이만 걷습니다.',
            '',
          ]
        : [
            `powershell -NoProfile -ExecutionPolicy Bypass -Command "${offPs(false)}"`,
            'if errorlevel 1 echo      [!] 전에 넣은 서버 LLM 명령 · 규칙을 걷지 못했습니다 - 위 메시지 확인. MCP 등록은 그대로 끝났습니다.',
          ]),
    );

    // ── [5c] 내 Claude 대화를 포털에 공유(docs/interaction-data contract §5) ─────────────────────────────────────────
    // 칸을 켜면 올리는 스크립트(%USERPROFILE%\.hwax\hwax-share.ps1)와 명령 /hwax-share 를 두고, 자동 칸이면 settings.json 에 SessionEnd 훅을 단다.
    // 끄면 걷는다 — 걷을 것이 있을 때만 말한다(위 sharePs 머리 주석). 글은 base64 환경변수로(스크립트는 조각으로) 넘긴다.
    L.push(
      ...(share !== 'off'
        ? [
            `echo  [5c] 내 Claude 대화를 포털에 공유 - Claude Code 명령 /hwax-share${share === 'auto' ? ' 와 세션 끝 자동 올리기' : ''}`,
            ...b64Sets('HWAX_SHARE_PS1', sharePs1()),
            `set "HWAX_SHARE_CMD=${b64(SHARE_CMD)}"`,
            `powershell -NoProfile -ExecutionPolicy Bypass -Command "${sharePs(share)}"`,
            'if errorlevel 1 echo      [!] 공유 스크립트 · 명령을 다 넣지 못했습니다 - 위 메시지 확인. MCP 등록은 그대로 끝났습니다.',
            'echo          Claude Code 를 새로 열면 /hwax-share 가 보입니다. 이 포털 박스에서 상호작용 기록이 꺼져 있으면 올릴 때 그렇다고 말합니다.',
            'echo          걷으려면 토큰 화면에서 칸을 끄고 받은 배치를 다시 실행하세요.',
            '',
          ]
        : [
            `powershell -NoProfile -ExecutionPolicy Bypass -Command "${sharePs('off')}"`,
            'if errorlevel 1 echo      [!] 전에 넣은 공유 스크립트 · 명령 · 훅을 걷지 못했습니다 - 위 메시지 확인. MCP 등록은 그대로 끝났습니다.',
          ]),
    );

    L.push(
      'echo.',
      'if not "%HWAX_DONE%"=="0" goto :ok',
      'echo  [X] Claude Code / Desktop / Gemini / Codex 중 어느 것도 설정하지 못했습니다.',
      'echo      하나라도 설치한 뒤 이 파일을 다시 실행하세요.',
      'pause',
      'exit /b 1',
      ':ok',
      // ── [6] 실제 연결 확인 ───────────────────────────────────────────────
      // 지금까지는 '등록됐는가' 만 봤다. 그건 연결된다는 뜻이 아니다 — http origin 에서
      // 만든 설정이 등록은 되고 mcp-remote 는 "Non-HTTPS URLs are only allowed for
      // localhost" 로 즉시 죽어, 사용자는 '완료' 를 보고도 Claude 에서 도구가 왜 안 뜨는지
      // 몰랐다(실사고). 그래서 여기서 mcp-remote 를 그대로 띄워 프록시가 서는지 본다.
      // 실패해도 배치를 끊지 않는다 — 등록은 이미 끝났고 되돌릴 것이 없다. 무엇을 봐야
      // 하는지만 알려 준다. 토큰은 환경변수로만 넘긴다(명령줄에 실으면 프로세스 목록에 남는다).
      'echo.',
      'echo  [6] 실제 연결 확인 중... (최대 40초)',
      `set "HWAX_MCP_URL=${MCP_URL}"`,
      `set "HWAX_ALLOW_HTTP=${IS_PLAINTEXT ? '1' : '0'}"`,
      'set "HWAX_TESTLOG=%TEMP%\\hwax-mcp-test.log"',
      `powershell -NoProfile -ExecutionPolicy Bypass -Command "${"$ErrorActionPreference='SilentlyContinue';$env:AUTH=$env:HWAX_AUTH;if($env:HWAX_CERT){$env:NODE_EXTRA_CA_CERTS=$env:HWAX_CERT};$log=$env:HWAX_TESTLOG;Remove-Item $log,($log+'.out') -Force -EA SilentlyContinue;$a=@('/c','npx','-y','mcp-remote',$env:HWAX_MCP_URL);if($env:HWAX_ALLOW_HTTP -eq '1'){$a+='--allow-http'};$a+=@('--header','Authorization:${AUTH}');$p=Start-Process -FilePath 'cmd.exe' -ArgumentList $a -NoNewWindow -PassThru -RedirectStandardError $log -RedirectStandardOutput ($log+'.out');$ok=0;$err='';for($i=0;$i -lt 40;$i++){Start-Sleep -Seconds 1;$t=((Get-Content $log,($log+'.out') -Raw -EA SilentlyContinue) -join '');if($t -match 'Proxy established successfully'){$ok=1;break};if($t -match 'Non-HTTPS URLs'){$err='mcp-remote 가 http 주소를 거부했습니다 (--allow-http 누락).';break};if($t -match '401|403|Unauthorized|Forbidden'){$err='토큰이 거부됐습니다 (만료 또는 폐기).';break};if($t -match 'ENOTFOUND|ECONNREFUSED|ETIMEDOUT|EAI_AGAIN'){$err='서버에 닿지 못했습니다 (주소/방화벽/프록시).';break};if($p.HasExited -and $i -gt 3){$err='mcp-remote 가 곧바로 종료했습니다.';break}};if(-not $p.HasExited){$p.Kill()};if($ok -eq 1){Write-Host '     [O] 연결 확인됨 - 서버가 응답했습니다.';exit 0}else{Write-Host ('     [!] 연결 확인 실패: '+$(if($err){$err}else{'응답이 없습니다 (시간 초과).'}));Write-Host ('     자세한 내용: '+$log);exit 1}"}"`,
      'if errorlevel 1 echo      등록은 끝났습니다. 위 사유를 해결한 뒤 Claude 를 재시작하세요.',
      'echo  [O] 완료. Claude 를 완전히 종료한 뒤 다시 실행하세요.',
      'echo      Desktop: 설정 - 커넥터에 hwax 가 보이면 정상',
      // ⚠ 확인 명령도 PATH 를 전제하면 안 된다 — 여기까지 온 사용자 중에 PATH 에 claude 가
      //   없는 사람이 있다(위 [2] 가 파일 경로로 찾아 등록해 준 경우). 찾은 경로를 그대로 준다.
      'if defined HWAX_CLAUDE echo      CLI    : "%HWAX_CLAUDE%" mcp get hwax',
      'if not defined HWAX_CLAUDE echo      CLI    : claude mcp get hwax',
      'echo               gemini mcp list  ^| codex mcp list',
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
  function desktopServerEntry(token: string, certPath: string | null, vv: string = VIEW_PORTAL): object {
    if (!certPath) {
      return { type: 'http', url: MCP_URL, headers: { Authorization: `Bearer ${token}`, [VIEW_NAME]: vv, [RESULT_NAME]: RESULT_REF } };
    }
    return {
      command: 'npx',
      args: ['-y', 'mcp-remote', MCP_URL, ...(IS_PLAINTEXT ? ['--allow-http'] : []), '--header', 'Authorization:${AUTH}', '--header', `${VIEW_NAME}:${vv}`, '--header', `${RESULT_NAME}:${RESULT_REF}`],
      env: { AUTH: `Bearer ${token}`, NODE_EXTRA_CA_CERTS: certPath, NO_PROXY: NOPROXY },
    };
  }

  function claudeDesktopSnippet(token: string, certPath: string | null, view?: string | null): string {
    return JSON.stringify({ mcpServers: { hwax: desktopServerEntry(token, certPath, viewValue(view)) } }, null, 2);
  }

  function chatCurlSnippet(token: string): string {
    return [
      `curl -N -X POST ${CHAT_URL} \\`,
      `  -H "Authorization: Bearer ${token}" \\`,
      `  -H "Content-Type: application/json" \\`,
      `  -d '{"message":"안녕하세요"}'`,
    ].join('\n');
  }

  /** 배치 없이 인증서로 직접 설정하는 순서(10-20 사용자 요청, docs/token-bat TB-D6) — 배치 [1] · [2] · [3] 이 하는 일을 사람이 차례로 한다.
   * 파일 · 묶음 본문은 배치와 같은 상수를 쓴다. token 이 없으면(발급하지 않고 인증서만 받은 사람) `<토큰>` 자리표시자를 넣는다.
   * ② 는 PowerShell 창에 붙여 넣는다 — exit 를 쓰지 않는다(그 창이 닫힌다). 저장소를 못 읽으면 배치처럼 포털 인증서만 담는다. */
  function certGuide(token: string | null): CertStep[] {
    const tok = token ?? '<토큰>';
    const psPath = (p: string) => p.replace('%USERPROFILE%', '$env:USERPROFILE');
    const noToken = token ? '' : ' <토큰> 자리에 발급 때 복사해 둔 토큰을 넣으세요 — 토큰은 발급 직후 한 번만 보입니다.';
    return [
      {
        label: '① 인증서를 제자리에 — 명령 프롬프트(cmd)',
        text: [`mkdir "${CERT_DIR}" 2>nul`, `move /y "%USERPROFILE%\\Downloads\\hwax-portal.crt" "${CERT_FILE}"`].join('\n'),
        note: '받은 파일이 다운로드 폴더에 없거나 이름이 hwax-portal (1).crt 처럼 바뀌었으면 move 의 앞쪽 경로를 고치세요.',
      },
      {
        label: '② 회사 인증서와 한 파일로 묶기 — PowerShell',
        text: [
          `$env:HWAX_PORTAL_CRT="${psPath(CERT_FILE)}"`,
          `$env:HWAX_CA_FILE="${psPath(CA_BUNDLE)}"`,
          'try{',
          ...PS_BUNDLE_BODY,
          "if($seen.Count -eq 0){Copy-Item -LiteralPath $env:HWAX_PORTAL_CRT -Destination $env:HWAX_CA_FILE -Force;Write-Host '윈도우 인증서 저장소를 읽지 못해 포털 인증서만 담았습니다 - 사내 프록시 뒤라면 npx 가 실패할 수 있습니다'}else{",
          PS_WRITE_BUNDLE,
          "Write-Host ('만들었습니다: '+$env:HWAX_CA_FILE+' (윈도우 신뢰 인증서 '+$seen.Count+'개 + 포털 인증서)')}",
          "}catch{Write-Host ('실패: '+$_.Exception.Message+' - ①에서 인증서를 '+$env:HWAX_PORTAL_CRT+' 에 두었는지 보세요')}",
        ].join('\n'),
        note:
          'Claude(Node)는 윈도우 인증서 저장소를 보지 않고, NODE_EXTRA_CA_CERTS 는 파일 하나만 받습니다. 그래서 포털 인증서와 이 PC 가 믿는 ' +
          '루트 인증서(회사 인증서 포함)를 한 파일로 묶습니다 — 배치파일이 하는 것과 같습니다.',
      },
      {
        label: '③ 연결 확인 — 명령 프롬프트(cmd)',
        text: [
          `set "NODE_EXTRA_CA_CERTS=${CA_BUNDLE}"`,
          // 실패는 오류 코드로 찍는다 — Node 의 문장(unable to verify the first certificate)보다 아래 안내와 맞대기 쉽다(실측 10-20).
          `node -e "fetch('${ORIGIN}/health').then(r=>console.log('OK HTTP',r.status)).catch(e=>console.log('FAIL',e.cause&&e.cause.code||String(e)))"`,
        ].join('\n'),
        note:
          'OK HTTP 200 이 나오면 Claude 도 이 인증서로 포털에 붙습니다. FAIL 뒤가 UNABLE_TO_VERIFY_LEAF_SIGNATURE · SELF_SIGNED_CERT_IN_CHAIN 이면 ' +
          '①②의 경로를, ENOTFOUND · ECONNREFUSED · UND_ERR_CONNECT_TIMEOUT 이면 주소 · 방화벽 · 프록시를 보세요.',
      },
      {
        label: '④ Claude Code 등록 — 명령 프롬프트(cmd)',
        text: ['claude mcp remove hwax -s user >nul 2>nul', claudeCodeSnippetSelfSigned(tok, CA_BUNDLE)].join('\n'),
        note: `첫 줄은 예전 hwax 등록을 지웁니다(없으면 아무 일도 안 합니다).${noToken}`,
      },
      {
        label: '⑤ Claude Desktop — claude_desktop_config.json 의 mcpServers',
        // Desktop 은 설정 값의 %USERPROFILE% 을 풀지 않는다 — 붙여 넣는 조각은 사람이 바꿀 자리표시자로 둔다.
        text: claudeDesktopSnippet(tok, CA_BUNDLE.replace('%USERPROFILE%', 'C:\\Users\\<사용자>')),
        note: `<사용자> 를 본인 계정 폴더 이름으로 바꾸세요. 트레이에서 Desktop 을 완전히 끈 뒤 저장해야 예전 설정으로 되돌아가지 않습니다.${noToken}`,
      },
      {
        label: '(선택) 모든 Node 프로그램에 늘 적용 — 명령 프롬프트(cmd)',
        text: `setx NODE_EXTRA_CA_CERTS "${CA_BUNDLE}"`,
        note: '새로 여는 창부터 Claude Code · npx · Gemini CLI · Codex 가 모두 이 묶음을 믿습니다. ④⑤의 설정과 겹쳐도 됩니다.',
      },
    ];
  }

  return { buildSetupBat, claudeCodeSnippet, claudeCodeSnippetSelfSigned, claudeDesktopSnippet, chatCurlSnippet, certGuide };
}

/** PC 문서 도우미 설치 배치 — 웹 챗의 'PC 의 PowerPoint 로 열어 가져오기' 단추가 이 PC 의 추출기(-Url 모드)를 부르게 한다(docs/chat-ppt B5).
 *
 *  ① 추출기를 포털에서 `%LOCALAPPDATA%\HWAX\` 로 받는다(직결 먼저 · 안 되면 시스템 프록시, 못 받으면 배치 옆의 사본) — 받은 파일에 판 표식
 *     (`HWAX_DOC_HELPER = `)이 있는지 본다. 없는 정적 경로는 SPA 가 index.html 을 200 으로 내 '받았다' 로 보인다.
 *  ② 포털 주소를 설정 파일(`hwax-doc.json`)에 적는다 — 도우미는 URL 이 아니라 이 주소로만 올린다(가짜 링크가 남의 서버로 못 보낸다).
 *  ③ `HKCU\Software\Classes\hwax-doc` 를 잇는다 — 이 사용자만이라 관리자 권한이 필요 없다.
 *  토큰이 없다(표는 웹 화면이 그때그때 받는다). Claude 셋업 배치와 따로 둔다 — 웹 챗 사용자는 그것을 돌리지 않는다(PP-D9). */
export function buildDocHelperBat(origin: string): string {
  const ORIGIN = origin.replace(/\/+$/, '');
  const PS1_URL = `${ORIGIN}/doc-extract/hwax-doc-extract.ps1`;
  // 받기 — 포털은 사내 주소라 직결을 먼저, 안 되면 시스템 프록시. TLS 1.2 를 켠다(PS 5.1 기본값이 낮은 PC 가 있다).
  const download =
    'powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference=\'Stop\';' +
    '[Net.ServicePointManager]::SecurityProtocol=[Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12;' +
    `$u='${PS1_URL}';$o=Join-Path $env:LOCALAPPDATA 'HWAX\\hwax-doc-extract.ps1';` +
    'try{[System.Net.WebRequest]::DefaultWebProxy=$null;Invoke-WebRequest -UseBasicParsing -TimeoutSec 60 -Uri $u -OutFile $o}' +
    'catch{$p=[System.Net.WebRequest]::GetSystemWebProxy();$p.Credentials=[System.Net.CredentialCache]::DefaultCredentials;' +
    '[System.Net.WebRequest]::DefaultWebProxy=$p;Invoke-WebRequest -UseBasicParsing -TimeoutSec 60 -Uri $u -OutFile $o}"';
  const L: string[] = [
    // ⚠ 첫 줄은 희생용이다 — BOM 을 cmd.exe 가 첫 줄에 섞어 읽는다(Claude 셋업 배치와 같은 까닭).
    '@rem HWAX doc helper setup',
    '@echo off',
    'setlocal',
    'chcp 65001 >nul',
    'echo.',
    'echo  HWAX 포털 - PC 문서 도우미 설치',
    "echo  웹 챗의 'PC 의 PowerPoint 로 열어 가져오기' 단추가 이 PC 의 Office 를 부르게 합니다.",
    `echo  포털: ${ORIGIN}`,
    'echo.',
    // 관리자 권한이면 %LOCALAPPDATA% 와 HKCU 가 관리자 프로필을 가리킨다 — 평소 계정의 브라우저가 못 찾는다.
    'whoami /groups 2>nul | find "S-1-16-12288" >nul 2>nul',
    'if errorlevel 1 goto :not_admin',
    'echo  [!] 관리자 권한으로 실행 중입니다 - 지금 사용자^(%USERNAME%^) 에만 등록됩니다.',
    'echo      평소 브라우저를 쓰는 계정이 아니면 관리자 권한 없이 그냥 더블클릭해 다시 실행하세요.',
    'echo.',
    ':not_admin',
    'set "HWAX_DIR=%LOCALAPPDATA%\\HWAX"',
    'if not exist "%HWAX_DIR%" mkdir "%HWAX_DIR%"',
    'echo  [1/3] 추출기 내려받기...',
    download,
    'if not errorlevel 1 goto :dl_check',
    'if not exist "%~dp0hwax-doc-extract.ps1" goto :dl_fail',
    'copy /y "%~dp0hwax-doc-extract.ps1" "%HWAX_DIR%\\hwax-doc-extract.ps1" >nul',
    'echo      포털에서 받지 못해 이 배치 옆의 hwax-doc-extract.ps1 을 썼습니다.',
    ':dl_check',
    'findstr /c:"HWAX_DOC_HELPER = " "%HWAX_DIR%\\hwax-doc-extract.ps1" >nul 2>nul',
    'if not errorlevel 1 goto :dl_ok',
    'del /q "%HWAX_DIR%\\hwax-doc-extract.ps1" >nul 2>nul',
    'echo  [!] 받은 파일이 추출기가 아닙니다^(로그인 화면이거나 낡은 추출기^).',
    'goto :dl_hint',
    ':dl_fail',
    'echo  [!] 추출기를 내려받지 못했습니다 - 사내망^(VPN^) · 프록시를 확인하세요.',
    ':dl_hint',
    `echo      포털의 ${ORIGIN}/doc-extract/hwax-doc-extract.ps1 을 이 배치와 같은 폴더에 받아 다시 실행해도 됩니다.`,
    'goto :fail',
    ':dl_ok',
    'echo  [2/3] 포털 주소 적기...',
    // 도우미는 URL 이 아니라 이 주소로만 올린다 — 이 줄이 올릴 곳의 정본이다.
    `> "%HWAX_DIR%\\hwax-doc.json" echo {"origin": "${ORIGIN}"}`,
    'if errorlevel 1 goto :fail',
    'echo  [3/3] 웹 챗 단추와 잇기 - hwax-doc:// , 이 사용자만 · 관리자 권한 불필요...',
    'reg add "HKCU\\Software\\Classes\\hwax-doc" /ve /d "URL:HWAX Doc Helper" /f >nul',
    'if errorlevel 1 goto :reg_fail',
    'reg add "HKCU\\Software\\Classes\\hwax-doc" /v "URL Protocol" /d "" /f >nul',
    'if errorlevel 1 goto :reg_fail',
    // %%1 — 배치 안이라 % 를 겹쳐 적는다(레지스트리에는 %1 로 들어간다). 따옴표는 reg 의 \" 다.
    'reg add "HKCU\\Software\\Classes\\hwax-doc\\shell\\open\\command" /ve /d ' +
      '"powershell.exe -NoProfile -ExecutionPolicy Bypass -File \\"%HWAX_DIR%\\hwax-doc-extract.ps1\\" -Url \\"%%1\\"" /f >nul',
    'if errorlevel 1 goto :reg_fail',
    'echo.',
    "echo  설치했습니다. 포털 화면으로 돌아가 'PC 의 PowerPoint 로 열어 가져오기' 를 다시 누르세요.",
    "echo  처음 한 번은 브라우저가 'HWAX Doc Helper 를 열까요' 를 묻습니다 - [열기] 를 누르세요.",
    'echo  이 PC 의 Office 를 먼저 확인하려면:',
    'echo    powershell -NoProfile -ExecutionPolicy Bypass -File "%HWAX_DIR%\\hwax-doc-extract.ps1" -SelfTest',
    'echo.',
    'pause',
    'exit /b 0',
    ':reg_fail',
    'echo  [!] 레지스트리에 잇지 못했습니다 - 회사 정책이 HKCU\\Software\\Classes 쓰기를 막았을 수 있습니다.',
    ':fail',
    'echo.',
    'pause',
    'exit /b 1',
  ];
  // CRLF + BOM — 윈도우 배치는 CRLF 여야 안전하고, BOM 이 있어야 위 한글 안내가 UTF-8 로 읽힌다(Claude 셋업 배치와 같다).
  return '﻿' + L.join('\r\n') + '\r\n';
}
