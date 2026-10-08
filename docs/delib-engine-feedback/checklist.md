# 심의 엔진 변경 — 체크리스트

## 준비
- [x] 요청서 진단을 dev 소스에서 재현(D-1)
- [x] 계획 · 결정 기록

## HWAXAgentServer
- [x] 1-1 합성 지정석 지식카드 생략 · 오류 절단 400자
- [x] 1-2 근거 본문 키 폴백 · 빈 항목 수 표시
- [x] 1-3 근거 건수 초과 표시
- [x] 1-4 `deliberate_start` 설명(상수에서 읽기 · voc · chair_template)
- [x] 1-14 「다른 좌석의 조회 결과」
- [x] 3-2 `[e:N|KEY]`(엔진 몫)
- [x] 1-5 `persona_knowledge` 요청 단위
- [x] 1-6 Job `risk-review-sealed` · 봉인 표시
- [x] 1-9 거절 메시지 누출 · 사용자별 상한
- [x] 1-11 `DELIB_HUMAN_NOTE_MAX` · 절단 표시
- [x] 1-12 `DELIB_MAX_SEATS`
- [x] 1-7 의장 전사 상한 유도
- [x] 1-8 지식카드 세마포어
- [x] 1-10 수치 대조 소스 · 총 N건
- [x] 1-13 공용 풀 라운드 비례

### 2차(D-12·D-13)
- [x] 1-9 ③ 대기 큐
- [ ] 2-2 `as_of` — 보류(D-15)
- [x] 합성 지정석 지식 조회 env 손잡이(`DELIB_KNOWLEDGE_SYNTHETIC_SEATS`)

## AIDataHub
- [x] 2-1 DB 풀 인자
- [x] 2-2 날짜 컬럼 조사 → **보류**(D-15 — `doc_date` 컬럼과 지식카드 취급 결정이 먼저)

## HWAXRisk (커밋만, push 보류 — D-11)
- [x] 3-1 `voc: "off"`
- [x] 3-2 `key` 를 엔진까지
- [x] 3-3 근거 초과 드롭을 남긴다

## HWAXPortal
- [x] 4-1 근거 120(셋 동시)
- [x] 4-2 좌석 계약 시험 — 엔진 기본값과 대조
- [x] 4-3 소속 자동 매핑 → 10차 §2 로 대체(`docs/change-request-8-10` D-2)
- [x] 4-4 human_note 상한 정합
- [x] 3-2·3-3 JS 파이프라인(`hwax-deliberate.js`) · 파리티

## 검증·반영
- [x] 반박 검토(8·9·10차와 함께, 렌즈 여덟) → 확정분 수정(D-16)
- [x] 리포별 전체 시험
- [ ] push · agent-server 재기동 · AIDataHub 재기동 · 포털 빌드·Drive·재기동 · sync-workflows
- [ ] 업데이트 이력 · CLAUDE.md 표

## 시간 제한(D-17)
- [x] 경로 전수 조사(149건) → 통합 표(바꿈 60 · 그대로 89)
- [x] 엔진 heartbeat·LLM 제한·의장 실패 폴백 · 게이트웨이 호출 600초 · 포털 릴레이·nginx·토큰 · 리스크 앱 벽시계 12시간 · AIDataHub 워치독
- [x] 층 순서 검토 → 확정 26건 수정 → 전체 시험
- [ ] push · hwax-risk SIF · Drive · dev 재기동 · 서버 절차서 갱신
- [ ] (미룸) 웹 심의 잡 원장(engine-26) · KooRemapper·HEAXHub 네 건 · 리스크 앱 화면의 마지막 신호
