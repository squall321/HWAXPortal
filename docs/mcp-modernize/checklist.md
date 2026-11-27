# 체크리스트 — MCP 현대화

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md) · 공통 계약 [contract.md](contract.md).

## 파악 · 결정

- [x] 조사 네 갈래(계약 · 찾기 · 쓰는 쪽 · 사내) — audit/ (11-27, MM-1)
- [x] 스펙 2026-07-28 · Skills · Events · Python SDK 2.x 원문 확인(11-27, MM-2)
- [x] 계획 · 공통 계약 · 결정 기록(11-27, MM-3)
- [x] 사용자 결정 셋(11-27, MM-4 ~ MM-6) — 세션 없는 셋은 이 세션이 · 표지는 게이트웨이 판정으로 노출 · cae00 은 7차에 1단계까지

## M0 측정 바닥

- [ ] 앱별 품질 카드 스크립트(게이트웨이 리포 — dev · cae00 같은 꼴, 설명 원문은 싣지 않음)
- [ ] 감사 원장에 `isError` 결과의 사유(앞 200자 · 사람 정보 가림)
- [ ] 점수판이 중첩 인자(객체 · `$defs`)를 센다 · 「게이트웨이가 채움」 을 따로
- [ ] 도구 수 셋(health · tools-map · tools/list) 맞추기
- [ ] 보기 · prompts · skills 채택 셈을 날마다 원장에(`/usage-rollup`)
- [ ] dev 에이전트 서버 `.env` 의 16K 시절 도구 값 걷기(재기동은 확인 뒤)

## M1 stateless

- [ ] 우리 앱이 서버 → 클라이언트 채널(알림 · sampling · elicitation)을 쓰는지 확인 — 1단계에서 버려진다
- [ ] 게이트웨이 세션 기댐 떼기 — 근거 원장 열쇠 · 재기동 막기 · 질의 기록 잇기
- [ ] 게이트웨이 stateless(1단계) · 옛 클라이언트 시험(개인 Claude 꼴) · 재기동 뒤 끊김 0
- [ ] 심의 MCP(에이전트 서버) — 이미 stateless 확인 · 시험
- [ ] 앱 세션에 1단계 청 — DynaForge · RA · SignalForge · MaterialTwin · Laminate · WDA · SmartTwin MCP(+ 세션 없는 셋은 결정대로)
- [ ] SDK 2.x 2단계 — 게이트웨이 · 에이전트 서버 venv 3.11+ · AI 데이터 허브 · 리스크 앱 · 자동 파이프라인 judge(2.x 예외 가림)
- [ ] 앱 세션에 2단계 청(contract.md P2 · P3)

## M2 정밀한 계약

- [ ] contract.md 를 앱 세션 열둘에 보냄(+ 그 앱의 카드 줄 · 고칠 것 상위 10 — audit/contract.md)
- [ ] 게이트웨이 일괄 — 설명 들여쓰기 걷기 · 쓰기 분류가 확인된 읽기 목록 먼저 · docstring 대신 채우기(확인된 앱만, 따로 셈)
- [ ] 읽기/쓰기 한 판정 — 부류를 `/tools-map` 에, 쓰는 쪽 일곱 벌을 그 부류 위로(모순 0 · 모름 0)
- [ ] SmartTwin `_register_direct` 가 카탈로그 스키마를 살리기(c8)
- [ ] AI 데이터 허브 · 리스크 앱 — 인자 설명 · 표지 · enum(포털 몫)

## M3 목적 단위

- [ ] `tool_purposes.json` 꼴 · 덧씌우기 · `/health` 의 missing 셈 · 씨앗(HE팀 운영자 workflow)
- [ ] 검색 작은 고침 — 쓰기 의도 낱말(작성 · 쓰기) · 띄어쓰기 접기 · 표지로 감점 · 평가에서 나빠진 쌍 0
- [ ] 검색 목적 층 · `list_tool_apps(by='purpose')` · 앱 입구 `entry`
- [ ] 보기 `purpose:<key>` · prompts `purpose-<key>`(사람 PAT 분기)
- [ ] 웹 챗 목적 예산(그림자 → 켜기) · 좌석 후보 그림자 · PC 킷 목적 고르기
- [ ] 평가셋 — HE samples(app@1) · 목적 쌍(purpose@1) · 186쌍 사람 검토 · cae00 스냅숏 평가

## M4 Skills · Events

- [ ] 게이트웨이 Skills 확장(목적 표 → SKILL.md · 워크플로 skill) · 받지 못하는 클라이언트용 prompts · 자원
- [ ] 게이트웨이 Events 확장(poll · stream) · 첫 이벤트 — 잡 끝 · 새 CAD 차수 · RA 게시
- [ ] 자동 파이프라인 감지를 이벤트로(지금의 묻기는 대비 길로 남김)
- [ ] Tasks — SDK 구현을 지켜본다

## M5 cae00 팔로업

- [ ] cae00 받은 편지함 — 비전 · 받는 차례 · 점검 MQ-1 ~ MQ-6 · 덧씌우기 안내 · Python 3.11+ · 바퀴 꾸러미(87 과 차례 맞춤)
- [ ] 사내 앱 주인 요청서(공통 계약 + 그 앱의 카드 줄) — 사용자가 건넨다
- [ ] cae00 카드 · 평가 결과를 받아 덧씌우기 튜닝
