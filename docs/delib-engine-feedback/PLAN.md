# 심의 엔진 변경 — S26U 실사용 피드백 반영

> 2026-10-07 · 근거: 실사용 팀(S26U 잠재리스크 심사)의 「HWAX 심의 엔진 변경 요청서」 — 엔진을 밖에서 관찰한 문제 11건을
> 소스로 감사해 `file:line` 으로 확정한 것. 요청은 리포 넷에 걸쳐 24건이다(엔진 14 · AIDataHub 3 · hwax-risk 3 · 포털 4).
> 요청서의 진단은 dev 소스에서 **전부 재현**했다(줄번호는 cae00 기준이라 1~4줄 어긋난다) — 아래 표의 자리는 dev 기준이다.
> 요청서 §5(설정으로 처리하는 것)·§0(관찰이 틀린 것)은 요청 대상이 아니다.

## 1. 공통 뿌리

24건 중 절반이 같은 모양이다 — **잘리거나 버려지는데 아무도 모른다.** 근거 본문 키가 `result` 가 아니면 항목이 통째로
사라지고(1-2), 41번째 근거가 사라지고(1-3), 의장은 전사의 1/6 만 보고(1-7), 오류 메시지는 80자에서 끊겨 사람이 다른
버그로 결론 내고(1-1), 도구 설명은 실제 상한의 1/12 을 적어 호출자가 스스로 버린다(1-4). 고치는 원칙은 하나다 —
**버리지 않을 수 있으면 버리지 않고, 버려야 하면 화면에 남긴다.**

## 2. 항목 — 무엇을 어디서

### HWAXAgentServer (엔진, `deliberation.py`·`delib_jobs.py`·`mcp_server.py`·`evidence.py`)

| # | 무엇 | 자리(dev) | 방침 |
|---|---|---|---|
| 1-1 | 합성 지정석(`delib-*`·origin adversary)에 지식카드 조회 안 함 · 오류 절단 80→400자 | `deliberation.py:3316`·`:1836` | 요청대로 |
| 1-2 | 근거 본문 키 폴백(result·text·content·excerpt·summary·body·output·data) · 빈 항목 수를 화면에 | `:783` | 요청대로, dict/list 는 JSON |
| 1-3 | 근거 건수 초과를 화면에 | `:781` | 요청대로 |
| 1-4 | `deliberate_start` 설명 — 상한은 상수에서 읽어 적고, `voc`·`chair_template` 을 advanced 목록에 | `mcp_server.py:185`·`:199` | 숫자를 다시 박지 않는다(D-2) |
| 1-5 | 지식카드를 요청 단위로 끈다(`persona_knowledge`) | `:658`·`:710`·`:3311` | 요청대로 |
| 1-6 | Job `risk-review-sealed` — 유입 경로 넷을 한 인자로 닫고, 봉인 사실을 잡·결정문에 남긴다 | `delib_jobs.py` Job 표 | 요청대로 |
| 1-7 | 의장 전사 상한을 모델 컨텍스트에서 유도(env 는 명시 오버라이드) | `:89`·`:1368` | D-5 |
| 1-8 | 지식카드 조회 동시성 상한(세마포어 6) | `:3339` | 요청대로 |
| 1-9 | 거절 메시지에 **내 잡만** · 사용자별 상한 분리 | `delib_jobs.py:256` | 큐는 하지 않는다(D-6) |
| 1-10 | 수치 대조 소스에 절단 전 전사·근거 블록 · 「표시 6건 + 총 N건」 | `:4010`·`evidence.py:38` | 요청대로 |
| 1-11 | `human_note` 상한 env · 잘리면 알린다 | `:731` | D-7 |
| 1-12 | 좌석 상한 env(`DELIB_MAX_SEATS`, 기본 20) | `:76` | D-3 |
| 1-13 | 공용 풀 예산을 라운드에 비례 | `:2164` | 요청대로, 상한은 `_pre_budget()*0.15` |
| 1-14 | 「공용 근거」 문구 → 「다른 좌석의 조회 결과」 | `:3701` | 요청대로 |
| 3-2(엔진 몫) | 근거 항목의 `key` 를 받아 `[e:N\|E3]` 로 찍는다 | `:786`·`:3383` | D-4 |

### AIDataHub

| # | 무엇 | 자리 | 방침 |
|---|---|---|---|
| 2-1 | DB 풀 인자(`DB_POOL_SIZE` 12 · `DB_MAX_OVERFLOW` 8 · `DB_POOL_TIMEOUT` 60) | `api_server/src/api/db/base.py:27` | 요청대로 |
| 2-2 | `agent_search` 날짜 컷오프(`as_of`) | `recommend_svc.py`·`search_svc.py` | **이번엔 조사만**(D-8) |
| 2-3 | `delib-baseline-defender` 에이전트 등록 | 운영 데이터 | 하지 않는다(D-9) |

### hwax-risk (리포 `HWAXRisk`)

| # | 무엇 | 자리 | 방침 |
|---|---|---|---|
| 3-1 | 러너가 `voc: "off"` 를 싣는다 | `backend/app/runner.py:297` | 요청대로 |
| 3-2 | 근거 키(E0~E9)를 엔진까지 넘긴다 | `backend/app/brief.py:1292` | D-4 |
| 3-3 | 12칸 초과분을 조용히 버리지 않는다(상한 자체는 그대로) | `runner.py:306`·`infra/pipeline/hwax-deliberate.js:147` | 드롭을 결과에 남긴다 |

### HWAXPortal

| # | 무엇 | 자리 | 방침 |
|---|---|---|---|
| 4-1 | 근거 칸 40 → 120(포털 스키마·프론트·엔진 기본값 셋) | `backend/app/agent/routes.py:134`·`frontend/…/handoff.ts:6`·엔진 `:100` | 요청대로 |
| 4-2 | 좌석 20 — 포털 셋은 그대로 20, 계약 시험이 엔진 **기본값**과 대조 | `routes.py:97`·`HandoffBrief.tsx:26`·`RosterEditor.tsx` | D-3 |
| 4-3 | SSO 가입자 소속 자동 매핑 | `backend/app/auth/user_store.py` | 10차 §2 로 대체했다 — `docs/change-request-8-10` #1(D-15) |
| 4-4 | `human_note` 포털 상한을 엔진과 맞춘다 | `routes.py:90` | D-7 |

## 3. 순서

엔진은 한 파일(`deliberation.py`)에 몰려 있어 **순서대로** 고친다(P1 조용한 실패 → P2 봉인 → P3 품질). AIDataHub·hwax-risk 는
엔진과 나란히, 포털은 엔진이 끝난 뒤(계약 시험이 엔진 상수를 읽는다). 구현 뒤에는 반박 검토(조용한 실패·계약 어긋남·
요청 대조 세 렌즈) → 확정된 것만 수정 → 리포별 전체 시험.

## 4. 반영 경로

| 리포 | 반영 |
|---|---|
| HWAXAgentServer | push → `./start.sh -d` 재기동(진행 중 심의가 없을 때) |
| AIDataHub | push → API 재기동 |
| HWAXPortal | push → `pnpm build` → `build-all-to-drive.sh portal` → 포털 재기동 · JS 는 `sync-workflows.sh` |
| HWAXRisk | push(프론트까지) → HEAXHub SIF 재빌드 → `redeploy-app.sh` → Drive (D-14) |

## 5. 하지 않는 것

- 반대석 에이전트 등록(2-3, 선택) · 리스크 앱 근거 상한 12 → 40(3-3 — CAPS 재배분이 따로 필요하다) · `as_of`(2-2 — 조사 결과로 보류, D-15).
- 대기 큐(1-9 ③)는 처음엔 뺐다가 사용자 지시로 2차에 넣었다(D-12·D-16).
- 요청서 §5 의 설정(`DELIB_DECISION_CTX=24000`·`DELIB_EVID_ITEMS=120` 등) — 실사용 팀이 cae00 에서 넣는다.
