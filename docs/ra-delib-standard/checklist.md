# 체크리스트 — 심의 보고서 RA 제출 표준화

> 계획은 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md).

## 파악

- [x] RA 최신 받기(`--ff-only` 04a147e v0.188.0 — 커밋 없음)
- [x] RA 의 시스템 보고서 길(형식 등록 · from-format · 시스템 공간 · 게시판 지정 게시 · 시스템 계정) 원문 대조
- [x] 우리 쪽 다섯 길 지도(조사 에이전트 · 주요 줄 직접 대조)
- [x] 사용자 결정 둘(11-26 — 시스템 공간에 확인 후 게시 · 심의 형식 하나)

## 포털

- [x] `app/agent/ra_post.py` — 박스 파일의 심의 줄(형식 · 게시판) 읽기, 에이전트 서버 · 게이트웨이와 같은 규칙
- [x] 창구 셋 — post-target · post-preview · post(CSRF)
- [x] 리스크 종합 보고서 — 재료가 기본 `deliberation` 일 때만 박스 형식으로
- [x] 심의 결과 카드 — 「시스템 공간에 올리기」 단추 · 미리보기 확인
- [x] `ra-register-format.py --board`
- [x] 시험 — 박스 파일 읽기 · 창구 · 리스크 형식 바꾸기 · 세 리더가 같은 파일을 같이 읽는지
- [x] 빌드 · 포털 전체 회귀 · 커밋 · push

## 게이트웨이

- [x] 로컬 읽기 도구 `ra_report_format`(좌석 접두에 안 걸리는 이름 — 공통 시험)
- [x] 게이트웨이 전체 회귀(1,255) · 병합 · push `c27a2f9`

## 워크플로

- [x] `hwax-deliberate.js` — `ra_report_format` 로 형식 · 게시판, 게시판이 있으면 게시 안내
- [x] sync-workflows · 계약 시험

## 마무리

- [x] server-setup.md(cae00 사람 몫)
- [x] 업데이트 이력 · CLAUDE.md 문서 표
- [x] 리스크 앱 화면 요청(게시 단추 — 리스크 앱 화면 세션 몫) — `risk-frontend-request.md` → 리스크 앱 main `5885e5a`(카드 · 시험 13) — 단, 리스크 앱에 「RA 초안으로 보내기」 단추(11-22 요청서 `docs/ra-report-draft-frontend-request.md`)가 아직 없어 화면에서 초안을 못 만들므로 카드는 아직 뜨지 않는다(RS-12)
- [x] cae00 받은 편지함 — 87 에 넘김(11-26, request-1125 R25-23)
- [x] dev 반영(11-26 사용자 승인 — 포털 · 게이트웨이 재기동, 새 리스너가 커밋 뒤에 떴다 · 포털 창구 셋 401(없으면 404) · 게이트웨이 `/tools-map` 에 `ra_report_format` · 감사 env 그대로 — 함께 켜진 다른 세션 커밋 없음)
