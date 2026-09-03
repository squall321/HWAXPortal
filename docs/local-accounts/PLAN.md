# 이메일 로컬 계정 — SSO 지연 브리지 (2026-09-03)

## 무엇을, 왜

사내 SSO 발급이 늦어져 데모 계정 하나를 여러 명이 공유 중이다. 이메일+비밀번호
로컬 계정을 도입해 **지금부터 사람 단위 신원**을 세우고, 나중에 SSO 가 연동되면
같은 이메일로 자동 연결한다. SSO 전환 후에도 계정 행은 남는다(로그인 수단만 바뀜).

## 설계 결정 (요체)

1. **subject = 이메일, 영구 키.** 대화·PAT·잡·감사가 전부 sub 키라 SSO 전환 시
   이메일 매칭만으로 무이관 승계된다. AD objectGUID 는 나중에 링크 속성으로만.
2. **가입은 관리자 승인제.** 정문이 인터넷 노출(스캐너 274 IP 실측) — 개방 가입 금지.
   가입 → pending → portal-admin 승인 → active.
3. **로그인 수단은 계정에 붙는 속성.** users 행이 원장, auth_source 만 local↔sso 로
   갱신. SSO 콜백에 note_sso_login 훅을 지금 심어 전환 작업을 0 으로 만든다.
4. **비밀번호는 stdlib scrypt** — 의존성 추가 없음. 실패 5회 → 10분 잠금 +
   IP 단위 rate-limit(로그인 10/분, 가입 5/시간).
5. **관리자 역할 = 기존 "portal-admin"** — require_role 그대로.

## 구조 (기존 코드에 얹는 자리)

- `complete_login()` 이 IdP 독립이라 로컬 로그인도 검증 후 같은 세션 발급을 탄다.
- users 저장소는 conv_store 패턴(stdlib sqlite + Lock), `data/users.sqlite`.
- 프론트 LoginPage 에 이메일/비번 폼 + 가입 신청, /admin/users 승인 화면.

## 검증 계획

1. backend/tests/test_local_auth.py — 저장소 단위(해시 왕복·잠금·승인) +
   TestClient 흐름(가입→pending 로그인 거부→승인→로그인→/auth/me→관리자 가드 403).
2. pnpm build 통과 + 포털 재기동 후 브라우저 실로그인.
3. RA 연동 여부는 별도 조사(Explore) 결과를 context-notes 에 기록.
