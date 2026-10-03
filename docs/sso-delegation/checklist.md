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
- [ ] 검토(반박 검증) — 사용자 요청으로 생략, 전체 시험으로 대신(포털 1117 · 게이트웨이 137)

## 문서
- [x] PLAN(ste 방식으로 다시) · ra-request(RA 담당용) · server-setup · context-notes D-9~D-13
- [ ] 업데이트 이력 · CLAUDE.md 표(했다)

## 배포
- [ ] 커밋(의미 단위) · push(포털·게이트웨이·TestScope — TestScope 는 push 가 릴리스를 만든다, 확인 후) · 빌드 · Drive · dev 재기동

## 서버(사람 몫 — server-setup.md)
- [ ] RA 담당 — ra-request(heax.py 되살리기 + 홈 부서) · HEAX_SSO_SECRET
- [ ] cae00 — RA_SSO_SECRET · TESTSCOPE_SSO_SECRET · routes.local.env testscope= · update-all
- [ ] TestScope 서버 — v0.50.0 · HEAX_SSO_SECRET · PORTAL_JWKS_URL · MCP 도달
