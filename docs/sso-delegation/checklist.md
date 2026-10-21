# 사람별 위임(ste 방식) — 체크리스트

## 코드(이 박스)
- [x] 이전안(포털이 토큰을 발급·저장·갱신) 걷기 — 엔진·암호화·로그인 훅·서비스별 연결 화면(D-13)
- [x] 게이트웨이 `strip_headers` · 옛 페이지 이름 문구
- [x] 게이트웨이 provision — RA_SSO_SECRET·TESTSCOPE_SSO_SECRET → per_user_sso · testscope 백엔드 · expires_in 반영 캐시
- [x] 포털 — RA_SSO_SECRET·ra_sso.py · PPT 가져오기 · 사전검사 · 연결 화면 모드 · 배선 설정 항목 · start.sh·update-all
- [x] 포털 — TestScope 타일(라우트 있을 때만) · plat:testscope
- [x] 포털 화면 — RA 카드 sso 모드 · 데스크톱 안 Claude Code 안내
- [x] 배치파일 — CLI 없어도 Claude Code 사용자 설정에 등록(D-9), 자리는 Claude Code 규칙(D-11) · 시험
- [x] TestScope — 토큰 등록(구 RA 방식, D-15): 외부 연결 카드 · 주인 확인 · 게이트웨이 PORTAL_CONN · 외부 링크 타일 · ste 방식 준비분 걷기
- [x] TestScope 두 방식(D-16) — `TESTSCOPE_SSO_SECRET` → `per_user_sso.testscope` · `testscope_mode` · 카드 sso 모드 · start.sh·update-all
- [x] 되돌리기 실제로 — 비밀을 비우면 update-all 이 `PER_USER_SSO_OFF` 로 게이트웨이 위임을 지운다(D-17)
- [x] ~~검토(반박 검증) — 사용자 요청으로 생략, 전체 시험으로 대신(포털 1126 · 게이트웨이 144)~~ — 버림(10-17 — 줄에 적힌 대로 반박 검토 대신 전체 시험(포털 1126 · 게이트웨이 144)으로 갈음했다 — 검토 라운드는 돌지 않았다)

## 문서
- [x] PLAN(ste 방식으로 다시) · ra-request(RA 담당용) · server-setup · context-notes D-9~D-13
- [x] CLAUDE.md 표 · testscope-request(선택) · server-setup B-2 · context-notes D-14~D-17
- [x] 업데이트 이력

## 배포
- [x] 커밋(의미 단위) · push(포털·게이트웨이·TestScope — TestScope 는 push 가 릴리스를 만든다, 확인 후) · 빌드 · Drive · dev 재기동 (확인 10-17 — 포털 f90a9eb · 614a764, 게이트웨이 674a843 · dd8d604 가 origin 에 있다 · TestScope 는 해당 없음(D-14) · 빌드 · Drive 는 delib-engine-feedback 체크리스트)

## 서버(사람 몫 — server-setup.md)
- [ ] RA 담당 — ra-request(heax.py 되살리기 + 홈 부서) · HEAX_SSO_SECRET
- [ ] cae00 — RA_SSO_SECRET · TESTSCOPE_BASE_URL · systems.local.yaml testscope · provision.env TESTSCOPE_MCP_URL · (선택) TESTSCOPE_SSO_SECRET · update-all
- [ ] TestScope 서버 — MCP(:8022) 도달 · (선택, B-2) `/api/auth/sso` + HEAX_SSO_SECRET

## 10-20 MatNexus · TestScope · FMEA Agent(사용자 요청)
- [x] 조사 — MatNexus(GitHub v1.292.1) · TestScope(로컬 v0.62.0 으로 최신화): 둘 다 표준 위임 창구 · 개인 토큰 · `/api/auth/me`, MatNexus 연동 안내 P1~P4 (D-18)
- [x] 게이트웨이 — `PER_USER_SSO_APPS` 쌍의 `<접두>_MCP_URL` → 같은 키 MCP 백엔드(시험 4 · 변이 2) (D-19)
- [x] update-all 이름 넘기기 · 기대 목록(게이트웨이 MANAGED 이름은 빼고) / check-egress 일반 앱 목적지(시험 3 · 기대값 5 갱신 · 변이 4)
- [x] 권한표 · 타일 — `matnexus` · `fmea`(둘 다 주소가 없으면 숨김) (D-20)
- [x] 문서 — PLAN 5 · server-setup C(MatNexus) · B-2(TestScope 위임, v0.51.0+) · D(FMEA) · fmea-request · D-18~D-20
- [ ] 커밋 · push(포털 · 게이트웨이) · 업데이트 이력
- [ ] 비밀 — 포털 운영자가 서비스마다 `openssl rand -hex 32` 하나씩(MatNexus 전용 · TestScope 전용) → 그쪽 운영에 안전한 길로
- [ ] MatNexus 운영 — 운영 판에 창구가 있는지(verify) · `HEAX_SSO_SECRET` · (선택) `HEAX_SSO_ALLOWED_IPS` · `MCP_ALLOWED_HOSTS` · 방화벽 8012
- [ ] TestScope 운영 — v0.51.0 이상 · `HEAX_SSO_SECRET` · `MCP_ALLOWED_HOSTS` · 방화벽 8022
- [ ] cae00 — server-setup C3~C6 · B2~B5 + B-2 · `NO_PROXY` · update-all
- [ ] FMEA Agent — fmea-request 답 → server-setup D(타일 소개 문구도 맞춘다)
- **10-21 — MatNexus · FMEA 는 토큰 등록(외부 연결 `connect:`)으로 바뀜** — 위 MatNexus 운영 · 비밀 · cae00 C3~C6 · FMEA 답 줄은 그 길로는 하지 않는다. 할 일은 [docs/ext-connect/checklist.md](../ext-connect/checklist.md) · 절차는 [server-setup.md](server-setup.md) C · D(다시 씀).
