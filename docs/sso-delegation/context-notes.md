# 하위 서비스 계정·토큰 자동 연결 — 결정 기록

## D-1. 질문의 두 축 — 브라우저 SSO 와 토큰은 따로 논다 (2026-10-03)
"SSO 가 되니까 다 이어지나" 의 답은 둘로 갈린다. 타일을 누르면 본인으로 들어가는 것(브라우저 SSO, jwt-handoff)은 RA 양쪽 코드가
있다. Claude·챗·심의가 본인 명의로 부르는 것(토큰)은 SSO 와 무관하게 사람이 `rat_` 를 붙여 넣어야 했다 — SSO 로그인이 서비스 토큰을
만드는 코드가 어디에도 없었다. 조사는 8갈래(지도 4 + 반박 4)로 했고 RA 엔드포인트는 직접 열어 확인했다.

## D-2. RA 를 고치지 않는 길이 있다 — 교환 + 자기 토큰 발급 (2026-10-03)
RA 에 `POST /api/auth/portal-exchange`(포털 launch 토큰 → RA 세션 JWT, 북마크로 RA 에 바로 온 사람용)와 `POST /api/me/mcp-tokens`
(로그인한 사람이 자기 PAT 발급)가 이미 있다. 포털이 서버에서 launch 토큰을 직접 서명해 둘을 차례로 부르면 그 사람의 `rat_` 가 나온다.
RA 리포는 hands-off(federation 제외)라 RA 쪽 수정이 필요 없는 이 길을 골랐다. 게이트웨이 per_user_sso(공유 시크릿 HMAC) 방식은
RA 담당이 09-26 4a96cef 에서 일부러 걷어낸 방식이라 되살리지 않는다.

## D-3. 교환은 처음 한 번만, 갱신은 토큰 자신으로 (2026-10-03)
교환은 RA 에 부작용이 있다 — 접속 이력에 '포털 로그인'(event=login_portal) 한 줄이 남아 RA 관리자 접속 통계에 1회로 잡히고, 기존 사용자의
`sso_profile` 이 덮여 SAML 부서 힌트가 지워진다(타일 클릭과 같은 부작용). 로그인마다 교환하면 둘 다 매번 일어난다. RA 의
`/api/me/mcp-tokens` 는 `rat_` 로도 열리므로 회전(새로 발급 → 저장 → 옛 id 삭제)은 교환 없이 한다. 교환은 연결이 없거나 토큰이 거부될 때만.
교환 요청에는 `User-Agent: HWAXPortal-autolink/1` 을 실어 RA 접속 이력에서 사람 로그인과 갈리게 한다(RA 가 기록하는 것은 UA·IP 뿐).

## D-4. 권한 있는 사람만 — RA 는 모르는 이메일이면 계정을 만든다 (2026-10-03)
RA 는 `PORTAL_JIT_CREATE=true`(기본)면 처음 보는 이메일로 계정·개인 공간을 만든다. 포털 로그인 전원에게 자동 연결을 걸면 RA 를 안 쓰는
사람의 RA 계정이 생기고 통계가 '미지정' 으로 쌓인다. 그래서 `plat:<service>` 가 있는 사람만(포털 권한 계산 그대로 — 정지면 빈 권한).

## D-5. 자동은 사람이 한 것을 덮지 않는다, 사람이 끊으면 멈춘다 (2026-10-03)
직접 붙인 토큰(source=manual)은 자동이 바꾸지 않는다 — 그 사람이 고른 토큰이다. '해제' 는 어느 쪽이든 opt-out 을 남겨, 다음 로그인에
자동이 되살리지 않는다('자동으로 연결' 을 누르면 opt-out 이 풀린다). 자동 토큰을 끊으면 RA 쪽 토큰도 지운다(포털이 만든 것이라서).

## D-6. 내부 조회에서 기다리는 상한 (2026-10-03)
Claude Code 만 쓰고 브라우저로 포털에 다시 안 오는 사람도 있다 — 첫 RA 호출 때 게이트웨이의 내부 조회가 자동 연결을 건다. 게이트웨이의
포털 조회 타임아웃은 8초다. 교환·대조·발급 세 번이 그 안에 안 끝나면 게이트웨이가 '모름' 으로 거부하고 30초 캐시한다. 그래서 작업은
shield 한 태스크로 돌리고 `CONN_LOOKUP_WAIT_S`(6초)만 기다린다 — 못 끝나면 404(미등록)로 답하고, 끝나면 포털이 게이트웨이 캐시를
비워 다음 호출부터 본인 명의가 된다.

## D-7. TestScope 는 명시적으로 켤 때만 '본인 토큰 필수' (2026-10-03)
게이트웨이가 testscope 백엔드를 보면 자동으로 연결 대상으로 삼게 할 수도 있었다. 그러면 cae00 에서 지금 서비스 계정으로 돌고 있을지 모르는
TestScope 호출이 배포 한 번에 전부 '등록 안 됨' 으로 막힌다(TestScope 쪽 계약이 아직 없다면 자동 연결도 못 한다). 그래서 기본 표는 RA 하나,
TestScope 는 게이트웨이 `portal.conn_backends` 에 사람이 넣을 때 바뀐다. 포털 쪽은 `TESTSCOPE_BASE_URL` 이 있을 때만 카드·연결이 생긴다.

## D-8. 저장 암호화, 키는 등록된 비밀 디렉터리에 (2026-10-03)
자동 연결이면 권한 있는 전원의 RA 토큰을 포털 DB 가 떠안는다. users.sqlite 는 0644 이고 미러·백업 대상이다. Fernet 으로 감싸고 키는
`secrets/jwt/conn.fernet` — 데이터 레지스트리에 이미 있는 비밀 클래스(jwt, sync none, 바인드됨) 안이라 DB 와 함께 복제되지 않는다.
새 레지스트리 클래스를 만들면 update-all 2b 이관기가 움직이므로 피했다. 키를 잃으면 복호화 실패를 '없음' 으로 읽는다 — 자동 연결분은
다시 만들어지고, 직접 등록분은 다시 붙여야 한다.

## D-9. 데스크톱 앱 안의 Claude Code 는 `~/.claude.json` 을 쓴다 — 배치가 CLI 없는 사람을 빠뜨렸다 (2026-10-03)
사용자가 동료(김예지 님, 10-02) 메모를 붙여 줬다 — Claude Desktop 은 `%APPDATA%\Claude\claude_desktop_config.json`, Claude Code 는
`~/.claude.json`(사용자·로컬 범위 MCP)·`.mcp.json`(프로젝트), 그리고 **데스크톱 앱 안에서 돌리는 Claude Code 도 데스크톱 설정이 아니라
`~/.claude.json` 을 쓴다.** 그래서 한쪽에 등록한 서버는 다른 쪽에 안 보인다. 토큰 화면 배치는 `claude` 명령을 찾았을 때만 Code 를 등록했고
(`claude mcp add -s user` 가 그 파일을 쓴다), 못 찾으면 "Claude Desktop 만 쓰신다면 이대로 정상입니다" 라고 말했다 — 데스크톱 앱만 깔고
그 안의 Code 탭을 쓰는 사람에게는 정반대 안내다(실패가 성공처럼 보이는 그 부류). 고침: CLI 가 없을 때 데스크톱 설정 병합과 같은 방식
(백업 → PowerShell 병합 → 되읽어 확인 → 바꿔 넣기)으로 `~/.claude.json` 의 `mcpServers.hwax` 를 쓴다. 항목 모양은 CLI 가 쓰는 것과 같게
(http 는 type/url/headers, 사내 CA 면 stdio+mcp-remote+env). 그 파일은 Claude Code 의 큰 전역 상태라 다른 키는 그대로 두고, 켜져 있는
앱이 종료하며 덮을 수 있어 완전히 종료하라고 붙인다.

## D-10. TestScope 는 소스가 생겼다 — 그쪽 코드도 여기서 맞춘다, 다만 있는 경로는 그대로 쓴다 (2026-10-03)
사용자가 TestScope 를 `~/claude/TestScope` 에 클론해 두고 "RA 처럼 연결해 두라, cae00 서버 셋업은 알아서 한다" 고 했다(RA 와 달리
TestScope 는 hands-off 대상이 아니다). TestScope 는 RA 와 같은 계보지만 경로가 다르다 — 내 정보 `/api/auth/me`, 토큰 `POST /api/auth/tokens`(201)·
`DELETE /api/auth/tokens/{id}`(204), 포털 SSO 는 없다. TestScope 에 RA 모양 별칭을 더 만들면 같은 일을 하는 경로가 둘이 된다. 그래서
TestScope 에는 **없는 것만**(포털 로그인 받기 — 브라우저 콜백·서버 간 교환) 넣고, 포털의 서비스 표가 서비스마다 경로·응답 모양을 따로 갖는다
(RA 는 `{success,data}` 봉투, TestScope 는 맨 모델). 요구사항 문서(testscope-requirements.md)는 '그쪽이 해야 할 일' 에서 '여기서 넣은 것과
서버에서 켤 것' 으로 바뀐다.

## D-11. 윈도우의 `.claude.json` 자리는 하나로 단정하지 않는다 (2026-10-03, 사용자 지적)
`~/.claude.json` 은 보편 경로가 아닐 수 있다. 배치는 ① `claude` 명령이 있으면 경로를 그 명령에 맡기고(`mcp add -s user` 가 제 자리를 안다),
② 없을 때만 직접 쓰되 자리를 이렇게 고른다 — `CLAUDE_CONFIG_DIR` 이 있으면 그 아래 `.claude.json`, 없으면 `%USERPROFILE%` 가 아니라
`[Environment]::GetFolderPath('UserProfile')`(관리자 권한·축소 환경에서 `%USERPROFILE%` 가 엉뚱한 곳을 가리킨 전례 — 데스크톱 폴더 건과 같다).
고른 경로와 그 판단 근거(이미 파일·`.claude` 폴더가 있었나)를 화면에 찍고, 흔적이 전혀 없으면 만들되 그 사실을 말한다.

## D-12. TestScope 의 Claude·챗 연결은 ste 방식으로, RA 는 자동 연결 유지 (2026-10-03, 사용자 결정)
사용자가 "다 ste 처럼 연결하고 싶다" 고 했다. ste 방식은 두 길로 나뉜다 — ① 게이트웨이 `heax_registry.per_user_sso.<백엔드>`
(공유 비밀로 서비스의 `/api/auth/sso` 에 "이 사람" 을 알려 호출마다 토큰을 받아 12시간 캐시, 포털은 아무것도 저장하지 않는다) ② 브라우저용
포털 중계(`/ste/credential`·StePrimer). ②는 ste 헤드노드가 인터넷이 없어 포털 JWKS 를 못 받기 때문에 생긴 예외라, JWKS 를 받을 수 있는
서비스에는 표준 jwt-handoff 타일이 맞다.

- **RA 는 여기서 ste 방식으로 못 간다.** RA 담당(박용진 님)이 09-26 4a96cef 에서 바로 그 방식(`/api/auth/sso` + 공유 비밀)을 일부러 걷어냈다 —
  "포털 표준은 jwt-handoff, ste 는 인터넷 없는 예외, RA 만의 특례는 안 된다". RA 리포는 hands-off. 사용자 선택: **RA 는 자동 연결(교환 1회 +
  자기 토큰 발급·회전·회수)을 유지**.
- **TestScope 는 ste 방식** — TestScope 에 `/api/auth/sso`(헤더 `X-Heax-Gateway-Secret`·`X-Heax-User-Email`·`X-Heax-User-Name`·`X-Heax-Client`)를
  넣고, 게이트웨이에는 설정 한 줄(`per_user_sso.testscope = {sso_url, secret, client}`)이다(per_user_sso 는 정적 백엔드에도 설정만으로 걸리고
  provision `--force` 가 이어받는다). 발급하는 것은 **사람 세션이 아니라 기계 자격(PAT)** — TestScope ADR 0009(PAT 로 들어온 쓰기는 후보)가
  그대로 걸리게. 이름은 `HWAX 게이트웨이(<client>)`, 수명 1일(게이트웨이 캐시 12시간보다 길게), 발급 때 같은 이름의 직전 토큰을 회수한다.
  브라우저는 jwt-handoff 타일(portal-callback) 그대로. 포털은 TestScope 토큰을 저장하지 않으므로 포털 연결 표에서 testscope 를 뺀다
  (`TESTSCOPE_BASE_URL` 도 필요 없다). TestScope 의 portal-exchange 는 쓰는 곳이 없어지므로 넣지 않는다.
- TestScope 리포 주인도 같은 분(4leaf321-nox321)이라, TestScope 에 ste 방식을 넣는 것은 그분이 RA 에서 밝힌 원칙과 어긋난다 — 사용자가
  알고 고른 것이다(포털 담당 결정). ADR 0010 에 그 사실과 이유(포털 코드가 늘지 않는다 — 게이트웨이 설정 한 줄, 토큰을 포털이 쥐지 않는다)를 적는다.

## D-13. RA 도 ste 방식으로 — 포털이 토큰을 쥐는 '자동 연결' 을 걷었다 (2026-10-03, 사용자)
사용자가 "RA 도 ste 방식으로 바꾼대" 라고 전했다 — RA 담당이 RA 에 서버 간 위임(`/api/auth/sso`)을 되살린다. 그러면 D-2~D-8 의 '자동 연결'
(포털이 교환 → 자기 토큰 발급 → 암호화 저장 → 만료 전 회전 → 정지 때 회수)은 하는 일이 없다 — 게이트웨이가 공유 비밀로 그 자리에서 토큰을 받는다.
그래서 끊긴 구현(세션 한도로 중간에 멈춘 워크플로가 남긴 작업 트리)을 **걷었다**: 엔진·서비스 표·연결 표 열 추가·Fernet·로그인/정지 훅·서비스별
연결 화면. 걷기 전에 확인한 것 — 진짜 비밀 디렉터리(`/data/hwax/secrets/portal/jwt`)에 키 파일이 생기지 않았고, dev 실DB(`users.sqlite`)
연결 표도 그대로(열 다섯, 암호문 0건)였다. 살린 것 — TestScope 타일·권한, 배치파일 수정, 옛 페이지 이름 문구, 게이트웨이 `strip_headers`.

**ste 방식에서 새로 생긴 일 셋.** ① 포털도 RA 를 직접 부른다(PPT 가져오기) — 포털이 같은 비밀로 그 사람 토큰을 받는다(`ra_sso.py`,
`/ste/credential` 선례). ② 게이트웨이 설정의 RA 서비스 헤더 `X-Workspace-Slug: dev` 가 사람별 호출에 실려 남의 부서로 읽고 쓴다 —
`per_user_sso.reportarchive.strip_headers` 로 빼고, 부서는 RA 가 그 사람의 홈 부서로 정한다(ra-request §3, RA 담당 몫). 포털 화면에서 조직을
고르던 기능은 ste 방식에서는 쓰지 않는다. ③ RA 위임 토큰 수명(12시간)이 게이트웨이 캐시(12시간)와 같아 만료 직전 토큰을 쓸 수 있다 —
게이트웨이가 응답의 `expires_in` 을 보고 그보다 일찍 다시 받는다.

**비밀은 자동으로 만들지 않는다(ste 와 다른 점).** `STE_SSO_SECRET` 은 `start.sh` 가 없으면 만든다 — ste 는 update-all 2c 가 같은 값을 ste 에
심기 때문이다. RA·TestScope 는 남의 서버라 포털이 값을 심을 수 없고, 포털·게이트웨이에 비밀이 먼저 생기면 게이트웨이가 위임으로만 부르기
시작해(PER_USER_SSO 가 포털 연결 경로보다 먼저다) 서비스가 준비되기 전의 모든 호출이 거부된다. 그래서 사람이 서비스 쪽을 켠 뒤 넣는다.

## D-14. TestScope·RA 는 직접 고치지 않는다 — 요청서로 (2026-10-03, 사용자)
"TestScope 도 RA 도 직접 수정하지 마, 포털에 뭘 고쳐야 하는지만 알려 주고 여기서 할 수 있는 것만 최신화해." D-10(TestScope 는 여기서 고친다)을
뒤집는다. 돌던 워크플로를 멈추고, TestScope 작업 트리를 커밋 `d900254` 그대로 되돌렸다(에이전트가 만든 변경 넷·새 파일 넷, 그리고 오늘 생긴
무시 대상 `frontend/node_modules`·`backend/logs` — 기준 시험과 `npm ci` 가 만든 것). RA 는 처음부터 손대지 않았다(추적 안 되는 셋은 6월 운영 파일).
그쪽에 필요한 것은 `testscope-request.md`·`ra-request.md` — 조사로 확인한 그쪽 코드 위치(d900254·v0.167.0 기준)를 같이 적어, 받는 쪽이 다시 찾지 않게.
포털·게이트웨이는 그 계약대로 준비해 두고, 서버 설정(비밀 한 줄)으로 켠다. 시험용 임시 PostgreSQL(55432)·TestScope 가상환경은 스크래치에만 있었다.

## D-15. TestScope 는 구 RA 방식(토큰 등록) — 다른 조직의 포털이라 (2026-10-03, 사용자)
"TestScope 가 다른 조직의 포털이라 그렇게(구 RA 방식으로) 연결해야 할 것 같다, 다른 주소로 노출되는 거라." 맞다 — 자기 주소로 서는 남의 포털을
우리 nginx 아래(`/testscope/`)로 끌어오거나 우리 SSO·공유 비밀을 그쪽에 심을 이유가 없다. 그쪽에는 이미 개인 토큰(`tsc_pat_`, 범위)과 토큰 주인을
돌려주는 `GET /api/auth/me` 가 있어 **그쪽 코드 수정 없이** 붙는다. 사람이 그쪽 토큰을 포털 '외부 연결' 에 등록 → 포털이 `TESTSCOPE_BASE_URL` 로
주인 이메일을 확인(포털 이메일과 다르면 거절 — RA 와 같은 fail-closed) → 게이트웨이 `PORTAL_CONN_BACKENDS` 가 본인 토큰으로만 부른다(없으면 거부).
타일은 그쪽 주소로 바로 여는 외부 링크(`systems.local.yaml`). 방금 커밋한 TestScope ste 방식 준비분(`TESTSCOPE_SSO_SECRET`·`per_user_sso.testscope`·
`testscope=` 라우트 유도·jwt-handoff 타일·testscope-request.md)을 걷었다. RA 는 그대로 — 토큰 등록이 지금도 돌고, RA 쪽이 준비되면 `RA_SSO_SECRET` 로 넘어간다.
⚠ 다른 조직이라 계정 이메일이 포털과 다를 수 있다 — 그러면 등록이 거절된다. 실제로 그러면 '연결 ID 대응표' 같은 완화가 필요하다(지금은 하지 않음).
