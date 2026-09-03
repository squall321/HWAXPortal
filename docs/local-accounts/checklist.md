# 로컬 계정 체크리스트

## 백엔드
- [x] user_store.py — users sqlite(이메일 PK·scrypt 해시·status·groups·auth_source·잠금 필드)
- [x] routes/local.py — signup / login / change-password / 관리자 list·approve·disable·reset
- [x] rate-limit(IP·계정) + 실패 잠금(5회→10분)
- [x] main.py 배선(app.state.user_store, 라우터 등록)
- [x] config.py — local_auth_enabled, local_bootstrap_admins
- [x] session.py 콜백에 note_sso_login 훅(미래 SSO 연동 대비, saml ACS 포함)
- [x] tests/test_local_auth.py — 저장소 단위 + API 흐름 (8 passed)
- [x] pytest 통과 + ruff 클린(신규 코드분)

## 프론트
- [x] LoginPage — 이메일/비번 로그인 + 가입 신청 폼(SSO 버튼 유지)
- [x] auth.api.ts — localLogin/signup/admin API
- [x] AdminUsersPage(/admin/users) — 승인·비활성·비번 재설정, portal-admin 만 노출
- [x] pnpm build 통과

## 마감
- [x] 포털 재기동 + 정문(:8088) curl e2e(가입→승인→로그인→401/403 음성 케이스)
- [x] 브라우저 실검증(playwright — 폼 로그인·관리자 화면·내비 노출)
- [x] 부트스트랩 관리자 생성(hwax.demo@samsung.com, 임시 비번 — 변경 필요)
- [x] RA 연동 조사 결과 context-notes 반영
- [ ] 커밋·푸시(cae00 은 pull + pnpm build + portal 재기동)
- [ ] (후속) RA 신원 전달 — 게이트웨이 per_user_sso 확장 + RA 측 /auth/sso (RA 리포는 hands-off, 별도 결정 필요)
