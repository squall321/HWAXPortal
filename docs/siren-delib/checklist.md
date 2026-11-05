# SIREN 을 심의 · 리스크 심사에서 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 날짜는 한국 시각.

## 0. 받기 · 결정
- [x] 요청서를 리포에 옮김([request.md](request.md), 11-06)
- [x] 사용자 결정 넷(11-06 — SD-1)

## 1. 게이트웨이(HWAXMcpGateway, 가지 `wt1106/siren`)
- [x] HG-26 실패 가르기(`_conn_fail_status` · `_conn_fail_text`) · 실패 감사 줄의 caller · mode · corr · status
- [x] HG-27 `X-Request-Id`(호출마다 새 UUID) · 감사 `rid` · 선언 칸 `request_id`
- [x] HG-28 `tool_areas.json` 앱 기본값 `siren` → `quality`
- [x] HG-29 선언 칸 `mask_keep_hosts` · 링크 호스트 자리만 가림 예외
- [x] 시험(새 21건 포함 844 통과)
- [x] 반대 검토 · 고침(SD-22 ~ SD-26)
- [x] master 병합 · 올림(`469f724`) · dev 재기동(11-06 06:01 KST) · `/tools-map` 확인(도구 590 · 미분류 0)

## 2. 포털(HWAXPortal, 가지 `wt1106/siren`)
- [x] 권한표 `connect:` 새 칸 둘(`request_id` · `mask_keep_hosts`) → 게이트웨이로
- [x] 시험(test_ext_connections 75 통과)
- [x] 전체 시험(4,490 — 작업 트리에만 나는 알려진 실패 둘) · 반대 검토(SD-26)
- [x] main 병합 · 올림(`518190d3`) · dev 포털 재기동(06:10 KST)

## 3. 에이전트 서버(HWAXAgentServer, 가지 `wt1106/siren`)
- [x] HA-36 선언 백엔드의 확인된 읽기를 좌석 자유 조회에(리스크 심사 포함 · 기준일 제외 · 앱 목록 좁히기에서도 남김)
- [x] 잡 줄 `_ConnGate`(동시 2 · 429 뒤 그 잡에서 안 부름 · 라운드 알림)
- [x] HA-37 지정 도구 차례(`_list_first`)
- [x] HA-38 천 단위 쉼표(evidence `_NUM_TOK_RE`)
- [x] RK-12 엔진 몫 — 미연결 · 한도 초과는 다시 시키지 않음 · 경고 사건(backends · labels · tools) · trust 안내 한 줄
- [x] 시험(새 25건 · 조립식 시험 고침)
- [x] 반대 검토 · 고침(SD-17 ~ SD-21) · 전체 시험(4,506)
- [x] main 병합 · 올림(`5cd1938`) · dev 재기동(06:02 KST)

## 4. 리스크 앱(HWAXRisk, 가지 `wt1106/siren`)
- [x] 손잡이 `HWAXRISK_CASE_TOOLS`(꼴 tools · 기본 SIREN 셋 · off) · 런타임 손잡이 표
- [x] 러너가 띄울 때 — 보통 패널 남은 자리 · 쟁점 패널 셋(게이트웨이 지도에 있을 때만) · 패널 호출 상한 · Claude 잡 제외 · 까닭 기록
- [x] 경고 → 패널 품질 표지(`conn_unregistered` · `conn_rate_limited`) · 쟁점 회의록 꼬리
- [x] 시험(새 12건)
- [x] 반대 검토 · 고침(SD-27 ~ SD-29) · 전체 시험(4,497)
- [x] main 병합 · 올림(`97d5aef`) · SIF 빌드 · dev 교체(06:12 KST) · Drive 판 `dist-20261105-211248Z`
- [ ] 화면 요청서 보내기([frontend-request.md](frontend-request.md) — 사용자가 화면 세션에)

## 5. 문서 · 알림
- [x] PLAN · context-notes · server-setup · frontend-request
- [x] ext-connect 요청서 칸 표에 새 칸 둘
- [x] `docs/request-1030/server-setup.md` 0절 줄 · 업데이트 이력 · CLAUDE.md 줄
- [x] cae00 받은 편지함(확인 결과 · SIREN R-9 — [2026-11-06](../cae00-inbox/2026-11-06.md))
- [ ] cae00 확인 결과 받기(사람) · 화면 요청서 보내기(사용자)
