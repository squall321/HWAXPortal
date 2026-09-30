# 서비스별 접속 이력 — 체크리스트

- [x] A: `access_log` 표·기록 함수(실패해도 로그인은 안 막고 WARNING 으로 드러낸다)
- [x] A: 로컬 로그인 성공·실패, SSO(OIDC 콜백·SAML ACS 둘 다), launch(+via=primer), ste 중계, `POST /systems/{id}/open`
- [x] B: `hwax_uid` 쿠키(로그인 때 발급·로그아웃 때 삭제) + nginx log_format 끝 칸
- [x] 관리자 API: 원장 조회 · 계정별 정문 요청 요약(nginx 로그 + 회전본)
- [x] 관리자 화면 `/admin/access` + 헤더 링크 · 타일 클릭 기록 · SsoPrimer 물러나기·via=primer
- [x] systems.local.yaml 오버레이 · 주소 없는 외부 타일 '곧 공개' · dev 오버레이 작성 · 내부 IP 가드 15 → 14
- [x] usage-report 회전본
- [x] 시험 격리(conftest — 운영 감사 원장에 시험이 쓰던 것)
- [x] 시험(포털 전체 928 + 신규) + 변이 14건 전부 사망 · dev 실검증
- [x] 업데이트 이력 항목
- [ ] 적대적 검토 · 푸시 · Drive 업로드(화면) · cae00 반영(systems.local.yaml 한 번)

### 결과(2026-09-30)
- 변이 14건 전부 사망(로그인 쿠키·SAML ACS 경로·미리 로그인 표시·열기 보임 검사·자동 갱신 숨김·uid 거름·창 거름·
  uid 칸 안내·주소 없는 타일·영역 표기·로그아웃 쿠키·원장 실패 경고·로그인 실패 기록·conftest). SAML ACS 경로 변이가
  처음엔 살아남았다 — e2e 가 `/auth/callback` 만 탔다. `/auth/saml/acs` 로도 돌게 했다.
- dev 실검증(포털·nginx 재기동, pid 교체 확인): mock SSO 로그인 → 쿠키 넷(hwax_uid 포함) · 원장 login(sso)·launch(heax-hub)·
  open(spdm) 이 IP·연결 ID 와 함께 · 계정별 정문 요청 portal 3·heax-hub 1 · nginx 로그 끝 칸에 연결 ID.
- usage-report 14일: 고유 IP 19 → 249(회전본을 읽기 시작).
