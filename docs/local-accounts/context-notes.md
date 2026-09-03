# 로컬 계정 — 결정 기록

- **subject=이메일 영구 키.** provider.py 주석은 prod 에서 objectGUID 를 상정했지만,
  대화(owner_sub)·PAT(sub)·감사(principal)가 이미 이메일로 쌓이고 있어 objectGUID 로
  가면 SSO 전환 때 전 데이터가 고아가 된다. 이메일로 고정하고 GUID 는 속성으로.
- **scrypt(stdlib) 채택.** argon2 가 더 낫지만 의존성 추가 + 컨테이너 재빌드가 필요.
  hashlib.scrypt(n=2^14, r=8, p=1)면 사내 브리지 용도로 충분하다.
- **로그인 라우트는 CSRF 면제.** 로그인 전엔 CSRF 쿠키가 없다 — 자격증명 자체가 증명.
  change-password·관리자 액션은 세션 기반이라 CSRF 유지.
- **역할 변경은 재로그인 후 반영.** groups 가 세션 JWT 에 박히는 기존 구조 그대로.
  승인 직후 관리자 화면에서 안내 문구로 커버.
- **부트스트랩:** users 테이블이 비어 있을 때 local_bootstrap_admins 에 든 이메일이
  가입하면 즉시 active+portal-admin. 첫 관리자를 만들 다른 경로가 없어서다.
- **mock SSO 버튼 유지.** 데모 시연 경로를 끊지 않는다. AUTH_PROVIDER 는 안 건드림.
- **note_sso_login 훅을 지금 심는 이유:** SSO 가 오는 날 "연동 작업"이 없게 —
  콜백에서 이메일 매칭 upsert 만 하면 계정 원장이 이어진다(사용자 요구: 계정 잔존).
- **부트스트랩 판정은 count_local(pw_hash 있는 행)로.** 전체 행 수로 하면 mock SSO
  로그인이 먼저 원장 행을 만들어 부트스트랩 창이 닫힌다(테스트로 확인).
- **SSO 생성 행(pw_hash NULL)에 가입으로 비번을 붙여 주지 않는다** — 가입이 열려
  있는 동안 남의 SSO 계정을 비번으로 탈취하는 경로가 되기 때문. 중복 가입은
  존재 여부를 노출하지 않고 {"status":"pending"} 으로 삼킨다.
- **테스트 사고:** TestClient 픽스처에서 user_store 를 컨텍스트 진입 **전에** 심으면
  lifespan 이 실설정으로 덮어써 실DB(data/users.sqlite)에 테스트 계정이 기록된다.
  진입 후 교체로 수정, 오염 DB 는 검사 후 삭제.

## 실사고 2건 (2026-09-03, koo.park 가입 직후)

- **대화 누출(브라우저 캐시)** — localStorage 키(hwax.chat/hwax.delib)가 계정 미구분이라
  같은 브라우저의 이전 사용자(demo) 대화가 새 계정에 그대로 보였다. 서버는 소유자
  분리를 강제하고 있었고 화면 캐시가 범인. `${prefix}.${email}` 네임스페이스로 고치고
  구 키는 발견 즉시 제거(그 자체가 누출 사본).
- **"부서 dev" 메시지** — RA 의 워크스페이스=부서 개념. 게이트웨이가 서비스 PAT
  (워크스페이스 dev)로 RA 를 불러 새 계정에게 남의 부서 문구가 보였다. 아래 연결
  토큰 기능이 근본 해법.

## RA 연결 토큰 — 구현 완료 (2026-09-03, 사용자 발안)

"RA 에서 발급받은 키를 포털에 등록해 두고 그걸로 연결" — 채택·구현. SSO 가 오면
RA 쪽 자동 계정 등록으로 대체될 브리지.

- 포털: `PUT /auth/connections/reportarchive` 가 RA `/api/me`(주의: /api/users/me 아님,
  openapi 실측)로 토큰 검증 + **이메일 일치 강제**(남의 토큰 등록=오귀속 차단) +
  home_workspace_slug 저장 + 포털 부서 자동 채움. UI 는 API 토큰 페이지 하단 카드.
- 게이트웨이: reportarchive 호출 시 `/internal/connections`(공유 시크릿=GW_TOKEN,
  포털 .env 의 GATEWAY_SHARED_TOKEN)로 토큰 조회 → 단발 세션에 Bearer rat_ +
  X-Workspace-Slug(사용자 부서) 교체. 미등록자는 종전 서비스 계정 폴백,
  등록자 실패 시엔 강등하지 않고 재등록 안내(오귀속 재발 방지). 캐시 5분.
- RA 응답은 {success, data:{…}} 봉투 — data 언랩 필요(실측 두 번 걸림).
- dev RA 는 8/14 프로세스가 낡아 mcp-tokens 라우트가 없었다 → requirements 동기화
  (ijson 등) 후 ./start.sh restart 로 v0.157.1 정상 기동(코드 무수정, 운영 재시작만).
- e2e 실증: RA 가입(hwax.demo)→rat_ 발급→포털 등록 200(부서 'Dev (개발)' 자동 채움)
  →내부 조회 403/200. 게이트웨이 audit 에는 실사용 시 `as-conn:<email>` 로 찍힌다.

## RA(Report Archive) 연동 조사 결과 (2026-09-03)

- RA 는 **이미 이메일 UNIQUE 키 + owner_user_id 소유 모델** — 포털 이메일 계정과
  구조적으로 자동 정합. 소유자는 인증 주체로만 정해지고 페이로드 author 필드는
  없다(위조 방지 설계 — author 필드를 새로 뚫는 방향은 금지).
- **현재는 신원이 RA 에 안 간다** — 게이트웨이가 고정 서비스 PAT 1개로 호출해
  챗/심의 생성 보고서 전부가 서비스 계정 1인 소유(list_my_reports 가 전원 동일
  목록을 반환하는 기존 귀속 버그).
- 연동 경로 2개: ① 브라우저 SSO — systems.yaml 을 jwt-handoff 로 바꾸면 포털 측
  4줄이지만 **RA 측 portal-callback 이 아직 없어** 지금 바꾸면 타일이 깨진다.
  ② MCP — 게이트웨이 per_user_sso 에 reportarchive 추가(+app_id 산출 수정)와
  RA 측 /api/v1/auth/sso 발급구(~60-80줄)가 정식. RA 리포는 hands-off 라
  **RA 측 변경은 사용자 결정 필요.** 전환해도 기존 보고서 소유자는 백필 전까지
  서비스 계정 그대로.
