# 서비스별 접속 이력 — 결정과 이유

**D-1 범위(사용자 결정, 2026-09-30).** A(포털 진입 원장)·B(정문 요청마다 계정) — 포털 리포만. 앱별 보완(HEAX Caddy 신뢰 프록시·
앱 접속 줄, MXWP·AIDH·SignalForge)과 우회 입구 정리는 하지 않는다. 함께 고칠 것: systems.yaml 사내 IP·usage-report 회전본·
SsoPrimer 401 폭주. 로컬 로그인 IP 로그가 로깅 설정이 없어 버려지던 무음 결함은 A 의 원장이 대신한다.

**D-2 조사에서 확인한 현재 상태(2026-09-30, dev).** 이메일+IP 가 함께 남는 곳은 게이트웨이 감사(MCP)와 RA `user_access_logs`
뿐이다. 포털은 로그인에 `last_login_at` 을 덮어쓰기만 하고 launch 는 아무것도 안 남긴다. HEAX 는 Caddy 에 trusted_proxies 가 없어
모든 IP 가 127.0.0.1 이고, SSO 전환 뒤 로그인 감사가 0건이다. 정문 nginx 는 IP·시각·경로를 14일 남기지만 계정이 없다.

**D-3 원장은 agent_audit.sqlite 의 새 표.** 기존 `agent_audit` 표의 meta JSON 에 넣으면 IP·서비스로 찾을 때마다 JSON 을 풀어야 하고
principal 이 subject 라 SSO 에서는 이메일이 아닐 수 있다. 새 파일은 데이터 레지스트리(services.yaml) 등록이 따로 필요해서 같은 파일에
표만 더한다(같은 잠금·연결). 보존은 게이트웨이 감사와 같게 무기한(사용자 결정 gateway-audit-ip D-1 과 같은 성격).

**D-4 원장 쓰기가 실패해도 로그인·진입은 막지 않는다 — 대신 WARNING.** 원장은 부기록이다. 다만 조용히 삼키면 '기록되는 줄 알았는데
0줄' 이 된다(로컬 로그인 INFO 로그가 그랬다 — 포털에 로깅 설정이 없어 INFO 는 버려지고 WARNING 은 남는다, 실측).

**D-5 uid 쿠키는 자격이 아닌 불투명 값.** 세션 JWT·CSRF 값을 nginx 로그에 남기면 자격증명이 로그에 쌓인다. 로그인마다 새 무작위
값을 주고 원장의 login 행에 적어 조인한다. 수명은 refresh 토큰과 같은 8h(refresh 는 세션만 갱신하고 refresh 토큰은 안 늘리므로
로그인 하나의 수명과 같다). 클라이언트가 보내는 값이라 **귀속이지 증명이 아니다** — 원장에 없는 값은 그냥 안 이어진다.

**D-6 auth_request 를 쓰지 않은 이유.** 요청마다 포털 서브요청이 붙어 포털 장애가 모든 서비스의 500 이 되고, 세션 쿠키는 900초라
하위 앱 탭에만 있는 사람은 15분 뒤 계정이 빈다(조사 front·verify).

**D-7 시험이 운영 원장에 쓰고 있었다(발견·수정, 2026-09-30).** TestClient 로 포털을 띄우면 기동이 get_settings() 의
agent_audit 경로(= /data 의 운영 원장)를 연다. dev 운영 원장 814줄 중 622줄이 시험 계정(user@corp.com)의 챗 기록이었다.
tests/conftest.py 가 get_settings() 가 처음 불리기 전에 AGENT_AUDIT_LOG_PATH 를 임시 파일로 정한다. 이미 쌓인 622줄은
지우지 않았다(운영 데이터 삭제는 사람이 정한다). 다른 저장소(users·token_store·conversations)도 기동이 실경로를 열지만
시험이 곧바로 갈아 끼우므로 쓰기는 없다 — 같은 모양의 위험으로 남겨 둔다.

**D-8 외부 타일 주소 — systems.local.yaml.** routes.local.env 는 값이 있으면 타일을 프록시로 승격하고 nginx 가 그 키로
location 을 만든다 — 직결 링크(다른 서버의 자체 주소)에는 맞지 않는다. 그래서 `<id>: {url: ...}` 모양의 별도 덮어쓰기(url 한 칸만)를
둔다. cae00 은 이 파일이 없으면 arp·odb-hub 가 '곧 공개' 로 뜬다 — git 기록의 직전 값으로 한 번 만든다
(`git show 7d2335b~1:backend/config/systems.yaml` 에서 두 타일의 url 을 옮긴다. 명령은 사용자에게 따로 준다 — 값을 문서에 적지 않는다).
