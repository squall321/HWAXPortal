// 윈도우 설치 배치와 등록 스니펫을 만드는 순수 생성기 — 브라우저 없이 시험할 수 있게 페이지에서 떼어 냈다
//
// 왜 페이지에서 떼어 냈나: 이 배치는 실사고가 여섯 번 났는데(PAT 평문 노출·http 스니펫 무연결·npm 점검 무한대기·
// Desktop JSON 이스케이프·`claude mcp add` 가 배치를 끊음·PATH 미반영) 그동안 **시험이 하나도 없었다**. TokenPage.tsx
// 안에 있으면 React·DOM 없이 실행할 수 없어서다. 여기 있으면 origin 만 넘겨 산출물을 그대로 검사할 수 있다
// (backend/tests/test_setup_bat.py 가 tsc 로 이 파일만 컴파일해 node 로 돌린다).
//
// window·document 를 **참조하지 않는다** — origin 은 인자로 받는다.

export interface Snippets {
  buildSetupBat: (token: string, name: string, pem: string | null) => string;
  claudeCodeSnippet: (token: string) => string;
  claudeCodeSnippetSelfSigned: (token: string, certPath: string) => string;
  claudeDesktopSnippet: (token: string, certPath: string | null) => string;
  chatCurlSnippet: (token: string) => string;
}

export function makeSnippets(origin: string): Snippets {
  const ORIGIN = origin;
  const MCP_URL = `${ORIGIN}/mcp-gw/mcp`;
  // NO_PROXY 는 호스트(:포트)만 받는다 — 스킴이 붙으면 무시된다.
  const HOSTONLY = ORIGIN.replace(/^https?:\/\//, '');
  // 사내 프록시. 다른 서비스들이 쓰는 값과 같다(infra/.env.example HWAX_FALLBACK_PROXY,
  // AIDataHub _common.sh DEFAULT_FALLBACK_PROXY). npm 레지스트리는 이걸 타야 나간다.
  const CORP_PROXY = 'http://168.219.61.252:8080';
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

  function claudeCodeSnippet(token: string): string {
    return `claude mcp add -s user --transport http hwax ${MCP_URL} --header "Authorization: Bearer ${token}"`;
  }

  // 자체서명 인증서를 쓰는 동안의 등록 명령.
  // ⚠ `NODE_EXTRA_CA_CERTS=... claude mcp add --transport http ...` 는 듣지 않는다(실측).
  // --transport http 는 설정에 URL·헤더만 저장하고 환경변수를 담지 않아서, 등록 시점의 변수는
  // 정작 연결하는 시점(나중에 뜨는 Claude 프로세스)에 사라진다. stdio(mcp-remote) 형태는
  // -e 로 준 환경변수를 설정에 저장해 매 실행마다 적용하므로 이쪽을 쓴다.
  function claudeCodeSnippetSelfSigned(token: string, certPath: string): string {
    return [
      `claude mcp add -s user hwax ^`,
      `  -e AUTH="Bearer ${token}" ^`,
      `  -e NODE_EXTRA_CA_CERTS=${certPath} ^`,
      `  -- npx -y mcp-remote ${MCP_URL}${ALLOW_HTTP} --header "Authorization:\${AUTH}"`,
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

  function buildSetupBat(token: string, name: string, pem: string | null): string {
    const certDir = '%USERPROFILE%\\.hwax';
    const certFile = `${certDir}\\hwax-portal.crt`;
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
      // 에러가 'MCP 등록 실패' 로만 보인다. 미리 확인하고 없으면 사내 프록시를 이 창에 세운다.
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
      L.push(`echo      ${certFile}`, '');
    }

    // ⚠ 아래는 일부러 괄호 블록( if ... ( ... ) )을 쓰지 않고 goto 로 흐름을 만든다.
    // 괄호 안에 PowerShell 한 줄처럼 (, ), | 가 섞인 긴 명령을 넣으면 cmd 의 괄호 매칭이
    // 어긋나 "예기치 않음" 으로 죽는 사고가 잦다. 라벨 방식이 장황해도 깨지지 않는다.

    // ── Claude Code (CLI) — 있을 때만 ──────────────────────────────────────────
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
          ? `"%%HWAX_CLAUDE%%" mcp add -s user hwax -e AUTH="Bearer ${token}" -e NODE_EXTRA_CA_CERTS=${certFile} -- npx -y mcp-remote ${MCP_URL}${ALLOW_HTTP} --header "Authorization:${'${AUTH}'}"`
          : `"%%HWAX_CLAUDE%%" mcp add -s user --transport http hwax ${MCP_URL} --header "Authorization: Bearer ${token}"`,
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
      // 예전엔 여기서 "정상" 이라고 했다. 설치해 둔 사용자에게는 거짓이다 — 무엇을 확인했고
      // 무엇을 모르는지 말하고, 다음에 할 일을 준다. 토큰은 절대 화면에 찍지 않는다.
      'echo      Claude Code 를 찾지 못해 이 단계만 건너뜁니다.',
      'echo          PATH 와 아래 위치를 모두 확인했습니다:',
      'echo            %USERPROFILE%\\.local\\bin\\claude.exe',
      'echo            %APPDATA%\\npm\\claude.cmd ^| claude.exe',
      'echo          Claude Desktop 만 쓰신다면 이대로 정상입니다.',
      'echo          Claude Code 를 쓰신다면 둘 중 하나입니다:',
      'echo            1^) 아직 설치 전 - https://claude.ai/install.ps1 로 설치',
      'echo            2^) 설치했는데 이 창의 PATH 에 아직 반영 안 됨',
      'echo               ^> 새 터미널을 열고, 토큰 페이지의 Claude Code 명령을 붙여넣으세요.',
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
      ? `$e=[pscustomobject]@{command='npx';args=@('-y','mcp-remote','${MCP_URL}',${ALLOW_HTTP_ARR}'--header','Authorization:$\{AUTH}');env=[pscustomobject]@{AUTH=$env:HWAX_AUTH;NODE_EXTRA_CA_CERTS=$env:HWAX_CERT}};`
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
      // ⚠ Roaming 경로를 %APPDATA% 하나로 믿지 않는다. 그 변수는 (a) 관리자 권한 실행에서 다른 프로필을
      //   가리키고 (b) 기업 폴더 리디렉션에서 UNC 경로가 되며 (c) 축소된 환경에서 아예 비어 있을 수 있다.
      //   GetFolderPath('ApplicationData') 는 리디렉션을 반영한 실제 경로를 준다. 폴백 둘을 둬서
      //   PowerShell 이 막힌 PC 에서도 종전과 같게 동작한다.
      'set "HWAX_ROAMING="',
      'for /f "usebackq delims=" %%R in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "[Environment]::GetFolderPath(\'ApplicationData\')" 2^>nul`) do set "HWAX_ROAMING=%%R"',
      'if not defined HWAX_ROAMING set "HWAX_ROAMING=%APPDATA%"',
      'if not defined HWAX_ROAMING set "HWAX_ROAMING=%USERPROFILE%\\AppData\\Roaming"',
      'set "HWAX_DESKDIR=%HWAX_ROAMING%\\Claude"',
      'set "HWAX_CFG=%HWAX_DESKDIR%\\claude_desktop_config.json"',
      // 어디를 봤는지 반드시 찍는다 — 종전엔 '폴더 없음' 만 말해 어느 경로를 본 것인지 알 수 없었다.
      'echo      설정 파일: %HWAX_CFG%',
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
      ...(pem ? [`set "HWAX_CERT=${certFile}"`] : []),
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
      ? `-e AUTH="Bearer ${token}" -e NODE_EXTRA_CA_CERTS=${certFile}`
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
      ? `--env AUTH="Bearer ${token}" --env NODE_EXTRA_CA_CERTS=${certFile}`
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
      ...(pem ? [`NODE_EXTRA_CA_CERTS = '${certFile}'`] : []),
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
  function desktopServerEntry(token: string, certPath: string | null): object {
    if (!certPath) {
      return { type: 'http', url: MCP_URL, headers: { Authorization: `Bearer ${token}` } };
    }
    return {
      command: 'npx',
      args: ['-y', 'mcp-remote', MCP_URL, ...(IS_PLAINTEXT ? ['--allow-http'] : []), '--header', 'Authorization:${AUTH}'],
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

  return { buildSetupBat, claudeCodeSnippet, claudeCodeSnippetSelfSigned, claudeDesktopSnippet, chatCurlSnippet };
}
