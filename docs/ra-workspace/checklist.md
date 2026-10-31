# RA 조직 선택 체크리스트

계획은 [PLAN.md](PLAN.md), 판단 근거는 [context-notes.md](context-notes.md).

## P0 — 백엔드

- [x] `user_store.set_connection_workspace` — 토큰을 건드리지 않고 슬러그만 갱신
- [x] `_workspace_options(me)` — 멤버십을 조직 우선으로 정렬한 후보 목록
- [x] `_pick_default_workspace(me)` — 조직 멤버십 우선, 없을 때만 home 폴백
- [x] `PUT /auth/connections/reportarchive` — 선택 `workspace` 수용 + 멤버십 검증 + 후보 반환
- [x] `GET /auth/connections/reportarchive/workspaces` — 저장 토큰으로 후보 조회
- [x] `PUT /auth/connections/reportarchive/workspace` — 슬러그만 변경(멤버십 검증)
- [x] 멤버십 밖 슬러그는 400 으로 거절(조용히 저장 금지)
- [x] 토큰이 응답·로그에 안 실린다

## P0 — 프론트

- [x] `RaConnectionCard` — 연결 후 조직 `<select>` 렌더, 개인 워크스페이스 표시
- [x] '지정 안 함'과 '조직 지정' 을 구분해 안내
- [x] 변경 저장·실패 문구
- [x] 빌드 통과

## P1 — 검증

- [x] 백엔드 테스트 — 검증 통과/거절, 기본값이 개인을 안 고름, 슬러그만 변경
- [x] 실주행 — RA `/api/me` 실응답으로 후보 목록이 뜨는지
- [x] 게이트웨이 캐시 TTL — 5분 지연을 발견해 `POST /conn-invalidate` 로 즉시 반영하게 했다

## P2 — 마무리

- [x] context-notes append
- [x] 커밋 분할 — 백엔드 / 게이트웨이 / 프론트 / 문서


## 남은 것

- [x] 브라우저 화면 실측 — 로그인 자격이 없어 못 했다(D5). 데이터 경로는 전부 확인됨. — 걷음: 운영(cae00)은 10-03 부터 RA 위임이라 카드가 조직 고르기를 그리지 않는다(frontend/src/components/RaConnectionCard.tsx:146-147) — 토큰 등록은 되돌리기용으로만 남아 실측 대상이 없다 (10-31 정리)
- [x] 등록자가 1명뿐이다(`hwax.demo@samsung.com`). 다른 사용자가 등록해야 다중 조직
      선택이 실사용으로 검증된다. — 걷음: 위임 방식에서는 RA 토큰을 등록하지 않아 다중 조직 선택이 실사용될 일이 없다(RaConnectionCard.tsx:146-147) — 이 줄의 계정 메일을 가릴지는 사용자 결정(docs/leftovers-1017/triage-1031.md) (10-31 정리)
