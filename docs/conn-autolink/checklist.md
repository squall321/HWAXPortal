# 하위 서비스 계정·토큰 자동 연결 — 체크리스트

## 코드(이 박스)
- [ ] 포털 저장 — connections 열 넷(source·remote_id·expires_at·updated_at) · connection_optouts · 토큰 암호화(옛 평문 1회 감싸기)
- [ ] 포털 서비스 표(conn_services) — reportarchive · testscope(TESTSCOPE_BASE_URL)
- [ ] 포털 엔진(conn_autolink) — 교환 → /api/me 대조 → 토큰 발급 → 저장, 회전(토큰 자신으로), 회수, 잠금·백오프·마지막 오류
- [ ] 포털 라우트 일반화 + 내부 조회의 자동 연결(대기 상한) + 정지면 내주지 않음
- [ ] 로그인 훅(SSO·이메일) · 정지 훅 · PPT 가져오기 전 ensure · 절차 문구
- [ ] access.yaml plat:testscope · systems.yaml testscope 타일 · registry(핸드오프+hide_unless_routed 는 라우트 있을 때만)
- [ ] 설정 칸 + backend/.env.example
- [ ] 게이트웨이 — conn_backends 병합 · 서비스별 라벨·헤더·문구 · provision 이어받기 · 시험
- [ ] 화면 — 외부 연결 카드(서비스별) · 문구 · 인라인 스타일 0
- [ ] 시험 — 포털 백엔드 · 게이트웨이 · 화면 점검
- [ ] 검토(반박 검증) → 고침 → 재검토

## 문서
- [x] PLAN · checklist · context-notes
- [ ] TestScope 요구사항(testscope-requirements.md)
- [ ] 서버 설정(server-setup.md)
- [ ] CLAUDE.md 문서 표 · 업데이트 이력 · gotchas 필요시

## 배포
- [ ] 커밋(의미 단위) · push(포털·게이트웨이) · 빌드 · Drive · dev 재기동(포털·게이트웨이)

## 서버(사람 몫 — server-setup.md)
- [ ] RA 서버 PORTAL_JWKS_URL(RA 담당) — update-all §6 'portal-callback → 303/400/401'
- [ ] TestScope 쪽 계약 구현(TestScope 담당)
- [ ] cae00 TESTSCOPE_BASE_URL · routes.local.env testscope= · 게이트웨이 testscope 백엔드 · portal.conn_backends
