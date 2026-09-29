# 게이트웨이 감사 IP — 결정과 이유

**D-1 범위와 보존(사용자 결정, 2026-09-29).** 게이트웨이만 고친다 — 개인 Claude 호출은 실제 PC IP, 안에서 부르는 호출
(웹 챗·심의·업로드·절차)은 127.0.0.1 로 남고 `via` 로 가른다. 브라우저 IP 를 포털→에이전트 서버→게이트웨이로 잇는 안은
세 리포·에이전트 도구 캐시 키까지 바꿔야 해 뺐다. `audit.jsonl` 보존은 지금처럼 무기한(감사는 뒤로 채울 수 없다) —
사내 규정이 정해지면 회전을 붙인다. 이 파일은 staging 으로 mirror 되고 매일 백업된다(services.yaml, backup-local.sh).

**D-2 IP 는 이미 게이트웨이에 와 있다.** 게이트웨이는 `uvicorn.run(app, host, port)` 로 뜬다 — uvicorn 0.49 기본값이
`proxy_headers=True`·`forwarded_allow_ips=127.0.0.1` 이라 nginx(`/mcp-gw/`, http 수준 `X-Forwarded-For
$proxy_add_x_forwarded_for` 를 상속)를 거친 요청은 `scope["client"]` 가 이미 nginx 의 `$remote_addr` 로 바뀌어 있다
(dev 접근 로그의 `<ip>:0` 줄 — 포트 0 이 XFF 에서 온 표시). 그래서 nginx 도 uvicorn 설정도 안 고친다.

**D-3 ContextVar 를 쓰지 않는다.** 도구 핸들러는 HTTP 요청 태스크가 아니라 세션 서버 태스크에서 `start_soon` 으로
돈다 — 미들웨어에서 심은 ContextVar 는 세션의 첫 요청(initialize) 값으로 굳는다. MCP SDK 가 메시지마다 심는
`_low.request_context.request`(그 POST 로 만든 Starlette Request)를 읽는다. 기존 `_request_purpose()` 등과 같은 길이다.

**D-4 형식 검사하고, 실패하면 칸만 뺀다.** uvicorn 은 XFF 의 가장 오른쪽 비신뢰 토큰을 **그대로** 쓴다 — 주소가 아닌
글자도 들어간다(검증 에이전트가 `evil"}{ x` 로 재현). `ipaddress.ip_address` 를 통과한 값만 적는다. `_audit` 은 전체를
`except: pass` 로 감싸므로, IP 읽기가 터지면 **줄 전체가 사라진다**(시험 가짜 요청에는 `.client` 가 없다) — getattr 과
안쪽 try 로 가둔다. 값이 없으면 키를 안 쓴다(기존 시험이 빈 줄의 키 집합을 정확히 건다).

**D-5 `via` 는 게이트웨이가 정한다.** 127.0.0.1 만으로는 '웹 챗 경유' 와 'dev Claude Code' 를 못 가른다. 미들웨어가 인증
분기에서 `x-hwax-via` 를 싣고, 두 분기 모두 클라이언트가 보낸 사본은 버린다(`x-hwax-purpose`·`x-hwax-muted-apps` 와
같은 규칙). 챗 판정은 끄기(D-7 of mcp-app-toggle)와 같은 식 — `pat_name == chat-session` **그리고** jti 가 `chat-`.

**D-6 계정 칸.** MCP 줄의 caller 는 이메일(`x-hwax-user`)인데 대화 저장·검색 4곳과 사용자별 자격 실패 2곳은 caller 를
안 넘겨 빈 칸이었다 — `_audit` 이 안 받으면 요청 신원을 쓴다. REST 다리는 caller 가 PAT 의 `sub` 였다(SSO 사용자는
이메일이 아닐 수 있다) → 이메일, 없으면 sub.

**D-7 인증 실패는 `/mcp` 에서만 남긴다.** 401 은 `/mcp` 밖 경로에도 나지만, 클라이언트가 OAuth 메타데이터를 찾는
`/mcp/.well-known/*` 조회가 정상 동작 중에도 401 을 받는다(dev 로그 4건) — 그걸 실패로 적으면 잡음이다. 토큰이 없었는지
(`no-bearer`) 틀렸는지(`invalid-token`)만 가른다. 검증 안 된 토큰의 이메일은 계정으로 적지 않는다(주장일 뿐이다).

**D-8 조사 중 발견 — dev 박스 시스템 nginx.** `/etc/nginx/conf.d/hpc-portal.conf` 의 `location ~ ^/vncproxy/([0-9]+)/`
가 인증 없이 박스 안 아무 포트로 넘긴다. 로컬에서 `/vncproxy/9110/health`·`/vncproxy/9009/health` 가 200 이었다.
에이전트 서버 `/chat` 은 본문의 이메일·그룹을 믿으므로 바깥에서 닿으면 사칭이 된다. HWAX 리포 밖 설정이라 건드리지 않고
사용자에게 알렸다(포트 범위 제한 또는 인증 권고). 이 경로도 XFF 를 싣으므로 IP 기록 자체는 맞게 된다.
