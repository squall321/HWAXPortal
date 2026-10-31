# 6차 변경 요청 — 체크리스트

- [x] §2 `SAML_WANT_NAMEID`(기본 참) · NameID 부재 500 → 400 · SAML 이메일 정규화 — d059a64
- [x] 운영 ADFS 모양 e2e 시험(실제 서명 Assertion, NameID 없음·URI Claim 다섯) + 변이 셋
- [x] 이름·그룹·sub·대소문자 전수 점검(포털 백엔드·화면, HEAX Hub·HWAXRisk·AIDataHub·MXWP·SignalForge·RA·에이전트서버·게이트웨이·ste)
- [x] §3 넣지 않음(요청자 철회 · D-5) · NameIDFormat 유지(D-4)
- [x] 3판 — §3 subject 출처 못박기(엄격) · §4-B 이름·부서 대체 사슬·원장 upsert·Claim 부재 경고 + 검토 2차 수정 넷(D-12)
- [x] cae00 — 요청자: pull·`.env`(SAML_WANT_NAMEID=false 외)·포털 재기동·메타데이터 확인·SSO 운영팀과 nginx 리로드·첫 로그인 Claim 확보 — 풀림 10-02 운영 로그인 성공(docs/change-request-7/PLAN.md:3-4) · 그 뒤 cae00 웹 QA 가 SSO 로그인으로 돌았다(docs/request_261030.md:5) (10-31 정리)
