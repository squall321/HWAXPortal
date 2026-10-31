# 리스크 심사 ECAD 싣기(10-31) — 체크리스트

요청서 정본 [`request.md`](request.md) · 판단 [`context-notes.md`](context-notes.md) · ODB 허브에 보낼 글 [`odb-hub-request.md`](odb-hub-request.md).

- [x] 요청서 정본 저장 · 리스크 앱 코드와 대조(HWAXRisk `ecad8c8` — 스텁 · 계약 4이름 · contract_only · 빈 ref · 계약 문서의 '게이트웨이 백엔드 없음' 모두 맞다)
- [x] D-1 사용자 결정 — (가) 지금 도구에 묶음 읽기
- [x] 1단계 결정 셋(사용자 결정 10-31) — ECAD 는 그 사람의 PAT 만(없으면 409 `ecad_pat_absent`) · pwr · rf 는 2단계까지 deferred · `risk_max_leaf` 가 ECAD 부품도 센다(넘으면 `allow_large`) — [`context-notes.md`](context-notes.md) E-3
- [ ] ODB 허브 요청 보내기(사람 — `odb-hub-request.md`)
- [ ] HWAXRisk 1단계 ER-01 ~ ER-05(워크플로 — 구현 · 블랙박스 · 반대 검토 · 고침) → 합치기 · push · SIF · Drive
- [x] 포털 `plan.md` §2.5.3 · §2.13.5 바꾸기(ER-05 — 1단계 결과 글로) — 리스크 앱 워크플로가 낸 글을 결정 셋으로 고쳐 넣고, 그 글이 짚은 함께 고칠 줄(§2.2 · §2.3 · §2.11.3 · §3.3.6)과 §6 의 ECAD 의존 도메인 규칙도 고쳤다(context-notes E-4)
- [x] 리스크 앱 화면 요청(ECAD 보드 고르기 — find_job 후보를 사람이 고른다, 화면 세션 몫) — [`frontend-request.md`](frontend-request.md)(10-31, 보드 카드 · 찾기 · 붙이기 · 떼기 · 오류 · 캡처 kinds · `model_too_large` · 스냅샷 board 노드 · 표지 · `comparability.ecad` · 결정 셋)
- [ ] cae00 다시 볼 시험(요청서 6절 1단계 캡처)
- [-] 2단계 ER-06 — ODB 허브 OH-01 · OH-02 뒤
