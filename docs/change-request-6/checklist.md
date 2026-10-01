# 6차 변경 요청 — 체크리스트

- [x] §2 `SAML_WANT_NAMEID`(기본 참) · NameID 부재 500 → 400 · SAML 이메일 정규화 — d059a64
- [x] 운영 ADFS 모양 e2e 시험(실제 서명 Assertion, NameID 없음·URI Claim 다섯) + 변이 셋
- [x] 이름·그룹·sub·대소문자 전수 점검(포털 백엔드·화면, HEAX Hub·HWAXRisk·AIDataHub·MXWP·SignalForge·RA·에이전트서버·게이트웨이·ste)
- [x] §3 넣지 않음(요청자 철회 · D-5) · NameIDFormat 유지(D-4)
- [ ] cae00 — 요청자: pull·`.env`(SAML_WANT_NAMEID=false 외)·포털 재기동·메타데이터 확인·SSO 운영팀과 nginx 리로드·첫 로그인 Claim 확보
