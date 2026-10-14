# 체크리스트 — 리스크 심사 앱 사람 자격(서비스 키 없이)

계획은 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md) 다.

## P0 계획

- [x] 요청서(2026-10-14 R1~R5)를 지금 main 기준으로 다시 조사(리스크 앱·포털·게이트웨이·허브, 10-14)
- [x] 사용자 결정 넷(U-1~U-4, 10-14)
- [x] PLAN · checklist · context-notes · 화면 요청서

## P1 포털 — 토큰 교환

- [x] `POST /auth/pat/exchange` — Bearer 원 PAT, 기록된 PAT 만, `feat:api-token`, 좁히기만(aud·scopes·만료 ≤ 원)(포털 `12862e3`, 미push — 교환 PAT 은 원이 못 된다 C-7, 거절 code 일곱 C-8)
- [x] `token_store` 에 `parent_jti` — 같은 이름의 앞선 교환 PAT 폐기, 원 PAT 폐기 연쇄(돌던 원장은 `PRAGMA table_info` 로 칸을 더한다 · 기록할 때 원의 폐기를 다시 본다 C-9)
- [x] 시험 — 넓히기 거절 넷(aud·scopes·수명·챗 PAT 원) · 쿠키 길 거절 · 폐기된 원 · 권한 없음 · 연쇄 폐기 · 대체 폐기(`test_pat_exchange.py` 19건 — 절차 PAT·만료된 원·정지·교환 PAT 원·만료 상한·원장 이관 포함; 스크래치 사본 변이 22종 중 21종이 해당 시험을 깬다, 남은 하나는 `verify_pat` 폐기 목록과 겹치는 원장 `revoked = 0`)
- [ ] 포털 시험 전체 → push — 시험 전체 2264 통과·11 건너뜀(10-14), push 는 아직

## P2 리스크 앱

- [x] R5 — 필수 키는 `CRED_KEY` 하나, `box.reasons[]`, `cred_key_source`, `dev_fallback` 기동 경고·옮기기 안내(리스크 앱 `8d672c7`, 브랜치 `creds` 미push)
- [x] U-3 — 패널 잡의 서비스 PAT 폴백 없앰(만들기·claim·엔진), 안내문, 서비스 PAT 를 쓰는 짧은 호출은 `credential: service` 표시(`5d47690` — `roster_credential`·브리프 `field_credential`·캡처 `credentials.mcp`, C3 자동 후속도 요청자 → owner)
- [x] R2 — 캡처 REST 의 위임 경로 = 게이트웨이 `step-forge` + 사람 PAT, `capture_rest` 값·안내문(`0e65f3a` — 게이트웨이 다리는 PAT 의 aud 에 `step-forge` 가 있어야 연다, 교환 명세는 `mcp-gateway` 만이라 지금은 교환 PAT 로 다리가 열리지 않는다 — 결정 대기)
- [x] R3 — `external_sync` 요약(`sender_unwired`)을 과제·대상·`risk_get_coverage`·`risk_next_step` 에(`0966b41`)
- [x] R1 — `_user_prefs` 살림 표, `GET /api/me` 의 `portal_pat.auto`, `PUT /api/me/portal-pat-auto`, 단언의 `portal_pat_wanted`, `POST /api/auth/portal-pat`, 손잡이 둘·기동 검사(`491895c`)
- [x] 리스크 시험 전체 · ruff(10-14 — 2,298 통과·xfail 4, ruff 깨끗 · 거절 검사 변이 19종 중 18종이 시험을 깨고 1종은 도달 불가 변이)

## P3 게이트웨이

- [x] `per_user_sso.<app>.portal_pat_url` — `portal_pat_wanted` 면 호출자 PAT 로 교환 → 등록(최선 노력, GW_TOKEN 호출 제외), 감사 note(게이트웨이 `c5ae578`, 미push — via=pat 만, 웹 챗·절차 PAT 도 건너뜀)
- [x] `provision-config.sh` 가 hwax_risk 에 `portal_pat_url` 을 적는다(게이트웨이 `ae92a6d`, 미push — `HWAXRISK_PORTAL_PAT_URL` 로 덮음)
- [x] 게이트웨이 시험(새 24건, 전체 344 통과 10-14 · 변이 9종이 해당 시험을 깨는 것 확인)

## P4 반대 검토

- [ ] 1라운드(사칭 · 수명 늘리기 · 토큰이 새는 길 · 조용한 강등 · 실패가 정상처럼 보이는 곳) → 재현 뒤 고침
  - [x] 포털 고침(10-14, `3d9c714`~`9f731b5` 미push) — 이름 대체 없앰 + `revoke-self`(C-11), `min_remaining_s`(C-12), 자식 다섯(C-13), `par`(C-14), 범위 형식·거절 글·기록 `%r`·목록 `parent_jti`·토큰 화면 배지(C-15); 변이 31종 중 30종이 시험을 깬다(남은 하나는 동치)

## P5 dev 실주행

- [ ] dev 리스크 앱 교체(고아 인스턴스 먼저 확인 — 메모 heax-orphan-instance-same-name) · 게이트웨이·포털 재기동
- [ ] Claude(hwax MCP) → `risk_next_step` → 교환 → 등록이 실제로 일어난다(토큰 목록에 `hwax-risk` 하나, 앞선 것은 폐기)
- [ ] PAT 없는 사람의 패널 잡이 서비스로 내려가지 않고 멈춘다
- [ ] 위임 캡처가 REST 로 `/tree` 를 읽어 G6 이 「모름」이 아니다

## P6 마무리

- [ ] `server-setup-m1.md` 키 표 · `cred.key` 옮기기
- [ ] cae00 절차서 [server-setup.md](server-setup.md)
- [ ] 업데이트 이력(기술·수정) · push
- [ ] 화면 세션에 요청서 전달 확인
