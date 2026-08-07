# 1차 항목 변경 지점 명세 — 착수 게이트 3번

`plan.md` §3 의 0차·1차 항목(T0, F1, F10)이 들어갈 함수·라인을 착수 전에 고정한다. 구현 중 범위가 번지는 것을 막는 것이 목적이다.
라인 번호는 2026-08-07 기준이며, 구현 시 앵커 문자열로 재확인한다.

---

## 0차 — T0 계측 하네스

**신규 파일.** `HWAXAgentServer/tools/delib_metrics.py` (신설). 기존 코드는 건드리지 않는다.

**입력.** 두 경로의 산출물을 모두 받는다.
- MCP 경로 — 워크플로 transcript 디렉토리의 `journal.jsonl` (라운드별 결과가 `{type:"result", result:{...}}` 로 남는다)
- 웹 경로 — Report Archive 보고서의 `minutes`·`recommendation` 블록, 또는 `save_conversation` 메시지 배열

**산출 지표.**

| 지표 | 산출 방법 | 계층 |
|---|---|---|
| 수치 인용 밀도(근거 유래/비유래) | 발언 내 수치 토큰 수 ÷ 발언 길이. `(도구)` / `(경험칙)` 표기로 분리 | A(선행 검토) |
| 반박 타겟률 | `rebut` 항목 중 특정 페르소나·특정 주장을 지목한 비율 | A |
| 신규 개념 도입률 | 라운드 N 발언의 명사구 중 라운드 N-1 에 없던 비율 | A |
| 결정문 수치 밀도 | 결정문 내 수치 토큰 수 ÷ 문단 수 | A |
| 파싱 실패율 · 필드 원본 길이 | 스키마 검증 실패 건수, 절단 전 원본 길이 분포 | 가드레일 |
| **착석 도메인 다양성** | 착석 페르소나 키의 도메인 접두사(`disp-`·`sw-`·`mat-` 등) 고유 개수 | **B(본 계획)** |
| **좌석 변동률** | 이어하기 시 신규 착석 수 ÷ 전체 착석 수 | **B** |
| **`non_negotiable` 보존율** | 이전 심의의 `non_negotiable` 중 이어하기 프롬프트·결정문에 등장한 비율 | **B** |

**기준선 확보.** 손잡이 전부 꺼진 현행 상태에서 심의 3건에 돌려 기준선을 기록한다. S26U 2건이 이미 저널로 남아 있으므로 재실행 없이 2건 확보 가능하다.

**비용.** 에이전트 0. 텍스트 파싱만 수행한다.

---

## 1차 — F1 도메인 커버리지 게이트

### [웹] `HWAXAgentServer/deliberation.py`

| 위치 | 앵커 | 변경 |
|---|---|---|
| L48 | `N_PERSONAS = _env_int("DELIB_PERSONAS", 5)` | 바로 아래에 `_COUNTER_SEATS = _env_int("DELIB_COUNTER_SEATS", 2)` 추가. 0 이면 F1 비활성(회귀 탈출구) |
| L936 | `yield _delib("stage", stage="discover")` | 변경 없음 |
| L953~L977 | `rec = await _call(tools, "recommend_agents", {"q": question})` 이하 자동 발굴 블록 | 1차 발굴 완료 후 **역질의 블록 삽입**. 질의문은 `f"{question}\n\n위 문제의 원인이 다음 분야 밖에 있다면 어느 분야인가 — {', '.join(선정된 키)}"`. 결과에서 이미 선정된 키를 제외하고 상위 `_COUNTER_SEATS` 명을 `personas` 에 append. 각 좌석에 `origin: "counter"` 표시 |
| L984 | `yield _delib("personas", totalRounds=opts.rounds, …)` | 각 페르소나 항목에 `origin`(`primary`/`counter`) 필드 추가. 프론트가 라벨을 그릴 근거 |
| L1208 | `chair_human = (` | 결정문 요구사항에 "(0) 참여 도메인과 미착석 인접 도메인" 항목 추가 |

**주의.** 역질의 실패(도구 오류·빈 결과)는 비치명적으로 처리한다. 반대 도메인 좌석 없이 진행하되 `origin` 표시로 그 사실이 결정문에 남게 한다. 기존 `if len(personas) < 2` 가드는 그대로 둔다.

### [MCP] `HWAXPortal/infra/pipeline/hwax-deliberate.js`

| 위치 | 앵커 | 변경 |
|---|---|---|
| L41~43 | `const PERS = A.personas \|\| []` / `if (!pk.length) throw …` | 좌석은 호출자가 주는 현행 계약을 유지하되, `personas[].origin` 을 선택 필드로 받는다 |
| 파일 상단 주석(L2~10) | 입력 스펙 주석 | **호출자 계약 명문화** — "이어하기·신규 모두 반대 도메인 좌석 1~2 를 포함해 전달할 것. 미포함 시 결정문에 커버리지 한계가 기록된다" |
| L172 | `const decision = await agent(` | 합성 프롬프트에 "(0) 참여 도메인과 미착석 인접 도메인" 추가. `origin` 이 있으면 반대 도메인 좌석을 구분 표기 |

**설계 판단.** MCP 경로는 좌석 발굴을 워크플로 안으로 끌어오지 않는다. 호출자(Claude)가 이미 `recommend_agents` 를 직접 쓸 수 있고, 워크플로 안에 넣으면 호출자가 의도적으로 구성한 좌석을 덮어쓸 위험이 있다. 계약 문서화 + 결정문 기록으로 처리한다.

---

## 1차 — F10 이어하기 좌석 재심사

### [웹] `deliberation.py`

| 위치 | 앵커 | 변경 |
|---|---|---|
| L48 부근 | 옵션 상수 블록 | `_RESCREEN = _env_int("DELIB_RESCREEN", 1)` 추가. 0 이면 현행 동작(재심사 없음)으로 복귀 |
| **L937** | `if opts.continue_personas:` | **핵심 변경 지점.** 현재는 이 분기가 발굴을 통째로 건너뛴다. 변경 후 흐름 — (1) 이전 좌석 역할 복원(현행 L943~950 유지) → (2) `_RESCREEN` 이면 **실효 질문**으로 `recommend_agents` 재호출 → (3) 유임/신규 분류 → (4) 유임 최소 보장 `max(2, len(이전)//2)` 적용 → (5) 신규 좌석 append |
| L937 블록 내 | 실효 질문 구성 | `f"{question}\n\n[이전 결론]\n{opts.continue_summary[:2000]}\n\n[사람 의견]\n{opts.human_note[:1000]}"` — 원 질문만이 아니라 이어하기의 실제 논점으로 발굴한다 |
| L984 | `yield _delib("personas", …)` | 각 좌석에 `origin`(`carry`/`new`/`counter`) 추가 |
| L1208 | `chair_human = (` | "(0)" 항목에 좌석 변동(유임 N·신규 M·하차 K) 기록 요구 |

**하차 처리.** 1차에서는 하차를 구현하지 않는다. 정원 상한이 없으므로 `유지 + 신규 추가` 만으로 충분하고, 좌석을 빼면 그 도메인의 이전 발언에 대한 책임 주체가 사라진다.

### [MCP] `hwax-deliberate.js`

| 위치 | 앵커 | 변경 |
|---|---|---|
| L44 | `const CONT = A.continueFrom \|\| null` | 변경 없음(F11 에서 구조 확장) |
| 파일 상단 주석 | 입력 스펙 | 이어하기 호출 계약 명문화 — "이전 좌석 전원 재사용 금지. 실효 질문으로 재발굴해 유임 `max(2, 절반)` + 신규를 구성해 전달할 것" |
| L172 | `const decision = await agent(` | 좌석 변동 기록 요구 추가 |

---

## 회귀 탈출구

각 조치에 env 스위치를 둔다. 문제 발생 시 코드 롤백 없이 종전 동작으로 복귀한다.

| 스위치 | 기본 | 0 일 때 |
|---|---|---|
| `DELIB_COUNTER_SEATS` | 2 | 역질의 생략 — F1 이전 동작 |
| `DELIB_RESCREEN` | 1 | 이어하기 재심사 생략 — F10 이전 동작 |

**손잡이 7종(`DELIB_CROSS_EXAM` 등)의 기본값은 건드리지 않는다.** 본 변경과 무관하며, 활성화는 T-서열 A/B 결과로만 결정한다.

---

## 변경하지 않는 것

- `_round_live` 및 라운드 프롬프트 구성부 — 계층 A 이며 T-서열 소관이다.
- `summarize()` / `readable()` — 동일.
- 자유 조회(`_free_gather_one`)·지식 RAG(`agent_search`) 블록 — 이어하기에서 이미 새 질문으로 재실행되므로 손댈 필요가 없다.
- Report Archive 블록 구조, `save_conversation` 메시지 스키마.
- `tests/test_grounding.py` 가 검증하는 순수 함수들(유령 ID 게이트·자유 도구 화이트리스트).
