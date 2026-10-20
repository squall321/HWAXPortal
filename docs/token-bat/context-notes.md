# 설치 파일(hwax-claude-setup.bat) — 결정과 까닭

**TB-D1 회사 인증서는 윈도우 신뢰 저장소에서 꺼내 묶는다(10-20 사용자 결정).** 요청은 'NODE_EXTRA_CA_CERTS = 회사 인증서 파일 경로' 였는데
그 경로는 사람마다 다르고 배치가 알 수 없다. 회사 루트 인증서는 사내 PC 의 윈도우 신뢰 저장소에 이미 있다(브라우저가 쓰는 그것). 그래서
`Cert:\LocalMachine\Root` · `Cert:\CurrentUser\Root` 를 지문으로 겹침 없이 PEM 으로 내보내 포털 인증서와 한 파일로 묶는다 — Node 의
`--use-system-ca` 와 같은 효과다(그 플래그는 Node 22.15 · 23.8 부터라, 옛 Node 에서 NODE_OPTIONS 로 주면 mcp-remote 가 아예 안 뜬다).
NODE_EXTRA_CA_CERTS 는 파일 하나만 받으므로 묶음이어야 한다. 내보내기가 실패하면 포털 인증서만 담아 종전과 같게 간다.

**TB-D2 JSON 은 JavaScriptSerializer 로 읽고 쓴다.** PowerShell 5.1 의 `ConvertFrom-Json` 은 대소문자만 다른 키를 중복으로 보고 멈춘다.
`System.Web.Script.Serialization.JavaScriptSerializer`(.NET Framework, 5.1 에 늘 있다)는 대소문자를 구분하는 사전으로 읽는다. 쓰기도 같은
것으로 해 두 키가 그대로 남게 한다 — 대신 줄바꿈 없는 한 줄 JSON 이 된다(Claude 는 상관없다, 사람이 고칠 때 보기 불편할 뿐). `MaxJsonLength`
는 int 최대로 올린다(기본 2MB — Claude Code 설정은 커질 수 있다).

**TB-D3 토큰 갱신은 있는 항목을 바탕으로(10-20 요청 4).** 요청은 'AUTH 만 바꾸는 갱신 방식' 이었다. 그대로 AUTH 만 바꾸면 포털 주소가 바뀐 뒤의
재실행이 옛 주소를 남긴다. 그래서 우리가 정하는 칸(명령 · 인자 · 주소 · 형식)은 덮고, 그 밖의 칸과 손으로 넣은 env 는 옮긴다. NO_PROXY ·
NODE_EXTRA_CA_CERTS 는 없을 때만 채운다(대소문자 무시) — 다만 예전 배치가 넣은 포털 인증서 경로(`…\.hwax\hwax-portal.crt`)는 새 묶음으로
바꾼다(안 바꾸면 회사 인증서가 끝내 안 들어간다). Claude Code CLI 길(`claude mcp add`)은 지우고 다시 넣는 공식 명령이라 손으로 넣은 env 를
옮기지 못한다 — 대신 두 기본값이 들어가므로 흔한 손질은 덮인다.

**TB-D4 실행 중인 Desktop 은 경로로 고른다(10-20 요청 5).** 프로세스 이름 `claude` 는 Claude Code CLI 와 같다. 경로가
`…\AnthropicClaude\…`(설치판) · `…\WindowsApps\…`(Store 판)인 것만 Desktop 으로 본다. 남의 · 권한 높은 프로세스는 경로가 비어 걸리지 않는다
— 그때는 종전의 '켜져 있으면 끄고 다시' 안내가 남는다. 설정을 하나라도 바꾸기 전에 멈춘다(Claude Code 사용자 설정도 같은 앱이 덮는다).

**TB-D5 시험은 산출물의 글이다.** dev 에 PowerShell 이 없다(5.1 의 JavaScriptSerializer 는 .NET Framework 라 pwsh 로도 못 돈다). 그래서 요청마다
조각 · 순서 · 빠진 것이 없음을 글로 보고, 실제 Windows 확인은 요청자 PC 에서 받는다. 생성된 PowerShell 을 눈으로 검토하다 둘을 고쳤다 —
배열을 PowerShell 이 감싼 채 넣으면 JavaScriptSerializer 가 객체로 쓸 수 있어 `[object[]]` 로 못 박았고, `-NoProfile` 창에서 Cert: 드라이브가
안 올라왔을 수 있어 모듈을 먼저 부른다.

