# 체크리스트 — MCP 현대화

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md) · 공통 계약 [contract.md](contract.md).

## 파악 · 결정

- [x] 조사 네 갈래(계약 · 찾기 · 쓰는 쪽 · 사내) — audit/ (11-27, MM-1)
- [x] 스펙 2026-07-28 · Skills · Events · Python SDK 2.x 원문 확인(11-27, MM-2)
- [x] 계획 · 공통 계약 · 결정 기록(11-27, MM-3)
- [x] 사용자 결정 셋(11-27, MM-4 ~ MM-6) — 세션 없는 셋은 이 세션이 · 표지는 게이트웨이 판정으로 노출 · cae00 은 7차에 1단계까지

## M0 측정 바닥

- [x] 앱별 품질 카드 스크립트 `mcp_quality_card.py`(게이트웨이 `ea058fd` — 카탈로그 + 감사 원장, 설명 원문 · 사람 · 주소 없음, 받아 둔 파일로도 · 시험 6 · dev 실측 797 · 인자 설명 0.379 · 표지 0.343)
- [x] 감사 원장에 `isError` 결과의 사유(게이트웨이 `3d776c9` — 가린 다음 앞 200자)
- [ ] 점수판이 중첩 인자(객체 · `$defs`)를 센다 · 「게이트웨이가 채움」 을 따로
- [ ] 도구 수 셋(health · tools-map · tools/list) 맞추기
- [ ] 보기 · prompts · skills 채택 셈을 날마다 원장에(`/usage-rollup`)
- [ ] dev 에이전트 서버 `.env` 의 16K 시절 도구 값 걷기(재기동은 확인 뒤)

## M1 stateless

- [ ] 우리 앱이 서버 → 클라이언트 채널(알림 · sampling · elicitation)을 쓰는지 확인 — 1단계에서 버려진다
- [x] 게이트웨이 세션 기댐 떼기 — 근거 원장은 신원으로만 · 재기동 막기는 비우는 동안 initialize 만 503(`7636080`)
- [x] 게이트웨이 stateless(1단계) — master `9bbc338` · dev 반영(11-27) · 실호출 확인(세션 번호 없음 · 세션 없이 / 옛 세션 머리로 tools/list 797 · tools/call 200). PC 킷(mcp-remote) 확인은 cae00 물음으로
  - [x] 에이전트 서버 루틴 실행기가 세션 번호 없이도 한 번만 연다(`df32ed2` · dev 반영)
- [x] 심의 MCP(에이전트 서버) — 이미 stateless
- [x] 앱 세션에 1단계 청(11-27) — DynaForge · RA · SignalForge · MaterialTwin · Laminate · WDA · SmartTwin MCP
  - RA(f6) — `b929a66` 로컬 커밋 · 채널 0 확인 · 배포는 RA 사용자 승인 뒤 · 아홉 항목 답 받음
  - WDA(7e) — 로컬 적용 · 채널 0 · 원장은 meeting_id 로 디스크 · push 는 87 의 5차 동결 해제 뒤 · 아홉 항목 답 받음(R3 은 서버 지침으로 갈음 — 안 함)
- [x] 세션 없는 셋(MM-4) — ThermalShock `7cd9297` · 웹 리서치 `29d67f0`(stateless + 실제 전송 시험, 전체 65 · 47 통과) · PaperIngest 는 이미 stateless. 허브가 SIF 를 지음(안에 고침 확인)
  - [ ] Drive 올리기 — 이 세션의 자동 모드가 막음 → 사용자 한 줄 명령
- [ ] SDK 2.x 2단계 — 게이트웨이 · 에이전트 서버 venv 3.11+ · AI 데이터 허브 · 리스크 앱 · 자동 파이프라인 judge(2.x 예외 가림)
- [ ] 앱 세션에 2단계 청(contract.md P2 · P3)

## M2 정밀한 계약

- [x] contract.md 를 앱 세션에 보냄(11-27, 「최대한 많이」 지시로 2단계도 지금) — 정정 셋(C6 1.x camelCase · P3 2.3 머리 · C7 두 벌, `dede79ba` · `38f2884b` · C1 길잡이 `01ab9cc3`)
  - 받음 — RA(SDK 2.x 까지 · 로컬 21커밋 · 배포는 RA 승인) · DocForge(0.5.0 · 2.x · main) · DynaForge(가지 a03c02c0 · 2.x) · MaterialTwin(로컬 4커밋 · compare_materials 크래시 진짜 원인) · WDA(로컬) · MXWP(로컬 · 보안 b588a71) · ste(가지 · R1 job_events 이벤트 `list_job_events`) · Laminate(가지 · C5 는 가벼운 꼴)
  - 남음 — StepForge · SignalForge · SmartTwin MCP 답
- [x] 쓰기 분류가 확인된 읽기 목록 먼저(`8094f68`)
- [ ] 게이트웨이 일괄 — 설명 들여쓰기 걷기 · docstring 대신 채우기 · 한 판정 노출(MM-5) · 구조 결과 두 벌 정리 · 점수판 중첩(서브에이전트 가지 `wt1127/m2` 짓는 중)
- [ ] 읽기/쓰기 한 판정 — 부류를 `/tools-map` 에, 쓰는 쪽 일곱 벌을 그 부류 위로(모순 0 · 모름 0)
- [ ] SmartTwin `_register_direct` 가 카탈로그 스키마를 살리기(c8)
- [x] 포털 몫 계약 — AI 데이터 허브 `7ed5dd0`(인자 설명 · 표지 0 → 100%) · 리스크 앱 `9f2086f` + 바깥 도구 인자 꼴 고침 `f534ab1` · 심의 MCP `234d016`(표지 · 설명 7,757 → 1,496자) · ThermalShock `99905fb` · 웹 리서치 `dafd506` · PaperIngest `210dc1d`(+ 보안 `4f25168`) · HE팀 운영자 목록 밖 쓰기 셋 `93d59a3b`

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

- [ ] cae00 받은 편지함 — 절 초안 `cae00-7th-section.md`(점검 MQ-1 ~ MQ-10 · 되돌리기 · 판 표 — 앱 판 채움 칸이 남음) → 87 에 넘김
- [x] 사내 앱 주인 요청서 13장 `requests/`(README 목록) — [ ] 사용자가 건넨다
- [ ] cae00 카드 · 평가 결과를 받아 덧씌우기 튜닝
