# 03 HWAX 에이전트 서버 — 10-30 요청에서 할 일

| 칸 | 값 |
|---|---|
| 받는 곳 | 이 세션(`hwaxportal-a5`)이 고친다 — 우리 리포라 다른 세션에 보내지 않았다([PLAN](../PLAN.md) 갈래 표의 '에이전트 서버' 줄). 리포는 형제 `HWAXAgentServer`(dev `~/claude` · cae00 `~/Projects` 아래)다. |
| 어떻게 갔나 | HA-26 첫 몫(안내를 사람 발화 머리로)은 main `7ca3a2e` 에 들어갔다(10-30 15:38 KST 커밋, 이 박스의 `origin/main` 도 같은 판). 재시도 몫 · HA-31 · HA-32 · HA-33 · HA-34 · HA-08(다시)는 형제 워크트리에서 구현 · 반대 검토 중이다 — 대조 시각에 가지마다 main 위 커밋이 있고 아직 합치지 않았다(`wt1030/ha26r` `59299af`(재시도 몫) · `wt1030/ha31` `90daab8` · `wt1030/vocab` `ac2aec0`(HA-32) · `wt1030/ha33` `9255db2`(커밋 2) · `wt1030/ha34` `f450a69`(커밋 2) · `wt1030/ha08` `ae861fe`(커밋 2), 포털 `wt1030/vocab` 에도 HA-32 · HP-56 커밋이 있다). HA-27 · HA-28 · HA-29 · HA-30 은 설계 중이다 — 대조 시각에 설계서 넷이 모두 있다([`design-ha27.md`](../design-ha27.md) · [`design-ha28.md`](../design-ha28.md) · [`design-ha29.md`](../design-ha29.md) · [`design-ha30.md`](../design-ha30.md), 18:02 ~ 18:11 KST 에 생겼고 모두 커밋 전). 구현은 아직 없다. [checklist](../checklist.md) 1절은 HA-26 첫 줄만 `[x]` 다. |
| 요청서 정본 | [../../request_261030.md](../../request_261030.md) — 1절 '에이전트 서버'(HA-26 ~ HA-32), 끝 절 '이전 회차에서 남은 챗 · 디지털 워커 요청' 의 에이전트 서버 표(HA-33 · HA-34 · HA-08(다시)), 6절 첫째 · 셋째 줄, 7절 첫째 · 둘째 · 셋째 · 다섯째 줄(다시 볼 시험). 건수 표의 에이전트 서버 줄은 높음 4 · 중간 3 · 낮음 · 선택 3 이다. |
| cae00 기준 판 | `969e723` |
| 이 박스(dev)에서 대조한 판 | `HWAXAgentServer` main `7ca3a2e`, 2026-10-30 18:13 KST(가지 · 설계서 상태도 이 시각 기준이다 — 형제 워크트리에서 계속 바뀐다). `969e723` 이 이 리포에 있고 HEAD 의 조상이라 `git show 969e723:<파일>` 로 줄을 맞댔다. 그 뒤 커밋 넷(`ab87137` 코어 어휘표 덧씌우기 · `61c0ce9` 분석 루틴 R2 · `d673846` 분석 루틴 R3 · `7ca3a2e` HA-26)이 모두 `app.py` 를 고쳐 이 열 행의 줄이 0 ~ 108줄 밀렸다 — 행마다 HEAD 줄을 다시 적었다. `deliberation.py` 는 그 뒤 커밋이 0 이라 줄이 같다. 함께 대조한 형제 리포 — SignalForge main `d2a794d`(요청서의 대조 판과 같다) · MXWhitePaper main `bd2e79b`(`f242254` 의 자손이고, 대조한 `dist/llm-docx-toolkit/mcp/api_client.py` 는 그 뒤 커밋 0) · StepForge main `ff308d1` · 포털 main `bf5cd94`(대조한 `infra/personas/he-team.json` · `infra/scripts/sync-he-personas.py` · `backend/config/core_vocab.json` 은 `aec8e29` 뒤 커밋 0). 요청서가 가리키는 QA 보고서 둘(`qa-ontology/QA-CHAT-QWEN-20261030.md` · `qa-digital-worker/QA-DIGITAL-WORKER-20261030.md`)은 이 박스에 없어, 행마다 적힌 cae00 실측 값은 '대조 못 함' 으로 남겼다. |

> 요청서 '한 줄'
>
> - 전문가(운영자)를 고르거나 앱을 핀하거나 문서를 붙인 챗이 LLM 400 으로 모두 실패했다(HA-26). 지금은 박스 우회로 막아 두었다.
> - 자기검증이 맞는 초안을 틀리게 고친다. 10-30 재시험의 PARTIAL · FAIL 넷 가운데 셋이 이 때문이다(HA-27).
> - 디지털 워커가 잡을 LLM 으로 폴링하고(HA-28), 사람에게 묻지 않고 무거운 잡을 건다(HA-29).

## 할 일

### HA-26 · 높음 — 이 턴의 안내가 둘째 system 이라 LLM 400

- **무엇이**: 이 턴의 안내(전문가 · 앱 핀 · 지식카드 발췌 · 붙인 문서)가 있는 챗이 LLM 400 'System message must be at the beginning.' 으로 실패한다.
- **근거**: `_turn_msgs`(`app.py:312-317`)가 `CHAT_STABLE_PREFIX` 켬(기본)일 때 안내를 이력 뒤 · 사람 발화 바로 앞에 두 번째 ("system", …) 로 넣는다. stcx vLLM 의 Qwen 채팅 틀은 맨 앞이 아닌 system 을 거절한다. 10-30 09:52 전문가 턴 1/1 실패 · 자동 재시도 두 번(`app.py:5285`)도 같은 메시지라 같은 400 이었다. 박스 우회(`CHAT_STABLE_PREFIX=0`, 09:55) 뒤 운영자 14명 0/14 실패.
- **할 일**: 안내를 두 번째 system 이 아니라 이번 사람 발화의 머리(같은 user 칸 — '[이번 턴의 안내] …' 뒤에 발화)로 넣는다. 그래도 400 'System message' 가 오면 자동 재시도 때 안내를 첫 system 에 합쳐 보낸다. 앞부분 고정을 끈 대가는 크게 보이지 않았다 — 끈 디지털 워커 시험의 캐시 적중 78.4%, 켠 OT 재시험 68.5%(문항 꼴이 달라 바로 견줄 수는 없다). 대화 고정으로 같은 질문 안의 호출이 캐시를 쓰는 몫이 크기 때문으로 본다.
- **다시 볼 시험**: 전문가 · 앱 핀 · 붙인 문서 챗 각 1회를 우회를 걷은 상태로.

#### 지금 판에서의 자리

- 첫 몫은 main 에 들어갔다 — `7ca3a2e`. `_turn_msgs` 는 HEAD `app.py:384-390` 이다. 안내가 있고 앞부분 고정(`_STABLE_PREFIX` `:363` — `CHAT_STABLE_PREFIX` 기본 켬)이 켜져 있으면 [첫 system(고정) · 이력 · 그림 다시 싣기 · 안내를 앞머리에 단 이번 발화] 를 짓는다(`:390`). 안내는 새 도우미 `_with_turn_notes`(`:368-381`)가 머리 `[이번 턴의 안내 — 시스템이 붙인 것이다. 사람이 쓴 글이 아니다]` 와 꼬리 `[사람의 말]`(`:364-365`)로 싸서 싣고, 그림이 든 발화면 첫 글 조각으로 넣는다. 손잡이를 끄면(`CHAT_STABLE_PREFIX=0`) 종전처럼 첫 system 하나에 잇는다(`:388-389`).
- 기준 판의 둘째 system 꼴(`969e723` `app.py:316-317`)은 HEAD 에 없다. HEAD `app.py` 에서 `("system", …)` 을 짓는 곳은 셋(`:389` · `:390` · `:5649`)이고 모두 메시지 목록의 맨 앞이다. 그림 다시 싣기(`_recap`)는 사람 칸(HumanMessage — `:4779` · `:4789`)이다.
- 시험 — 가짜 LLM 서버가 진짜 틀처럼 맨 앞이 아닌 system 을 400 'System message must be at the beginning.' 으로 거절한다(`tests/fakes/llm_server.py:158-161`). `tests/test_request_1029.py` 의 `test_W3_바뀌는_안내는_사람_발화_앞머리에_싣고_시스템은_맨_앞_하나다_끄면_종전_꼴이다`(`:228`) · `test_HA26_그림이_든_발화도_안내를_첫_글_조각으로_싣고_시스템은_하나다`(`:374`) · `test_HA26_실제_Qwen_채팅_틀은_둘째_시스템_메시지를_거절하고_고친_꼴은_받는다`(`:388`)가 지킨다.
- 재시도 몫은 main 에 아직 없다. 자동 재시도는 HEAD `:5357-5388` 이고(시도 수 `CHAT_AUTO_RETRY` 기본 2 — `:5357`, 요청서 `:5285` 의 실패 print 는 `:5387`), 시도마다 같은 `_turn_msgs(sys_prompt, turn_notes, …)`(`:5368`)로 다시 지어 안내를 첫 system 에 합치는 갈래가 없다. 'System message' 글귀는 HEAD `app.py` 에서 주석(`:361`) 한 곳뿐이다.
- `_turn_msgs` 를 부르는 곳은 셋이다 — 본 턴(`:5153`) · 자동 재시도(`:5368`) · 도구를 예고만 한 턴의 강제 1회 재시도(`:5442`).
- cae00 실측(09:52 전문가 턴 1/1 실패 · 우회 뒤 0/14 · 캐시 적중 78.4% · 68.5%)은 이 박스에서 대조 못 함 — cae00 의 로그 · QA 보고서 몫이다.

#### 우리 쪽 맞물림

- 재시도 몫(그래도 400 'System message' 면 자동 재시도 때 안내를 첫 system 에 합친다)은 이 세션이 가지 `wt1030/ha26r`(`59299af`) 에서 고치는 중이다([checklist](../checklist.md) 1절 둘째 줄).
- OB-91(5절, 우리 몫) — cae00 의 박스 우회 `CHAT_STABLE_PREFIX=0` 은 HA-26 이 cae00 에 들어온 뒤 사람이 줄을 지우고 재기동한다. 요청서 기준 판 `969e723` 에는 첫 몫도 없다(cae00 의 지금 판은 이 박스에서 대조 못 함).
- HA-28 설계서(5절)는 기다림 안내를 도구 결과 안에 싣고 system 메시지를 더하지 않는다고 적었다 — 이 행의 '시스템은 맨 앞 하나' 를 지킨다.
- 7절 둘째 줄 — 우회(OB-91)를 걷은 상태로 전문가 · 앱 핀 · 붙인 문서 챗을 보고 접두 캐시 적중을 다시 잰다.

### HA-27 · 높음 — 자기검증이 맞는 값을 틀리게 고친다

- **무엇이**: 자기검증이 맞는 값을 틀리게 고친다.
- **근거**: OT-04 개발모델 34 → 13 · OT-08 다른 가상검증 항목의 부서 A → 부서 B · OT-09 '20' 을 지우고 '근거 없음 — 추정' · DW-05 직전 기간 값을 지워 '가장 많이 늘어난' 순위가 비었다. 셋은 게이트웨이 읽기 도구로 서버 값을 직접 대조했다(초안이 맞았다). 검토자 입력의 조회 결과를 창에 맞춰 자르고(`app.py:4371` `_sc_fit(res, cap["res"])`), 바꿀 곳을 근거와 다시 대조하지 않고 넣는다(`app.py:4413` 이후). 이번 16문항에서 고침 12 · 의심 3 · 맞음 1, 디지털 워커 18턴에서 고침 15.
- **할 일**: ① 고침의 [새 글] 에 든 숫자는 이번 턴 도구 결과 **원문(자르기 전)** 이나 그 원문 값의 합 · 차 · 비율일 때만 넣는다. 아니면 '짚음(반영 안 함)' 으로 돌린다. ② 초안의 숫자를 지우거나 '근거 없음' 으로 바꾸는 고침은 그 숫자가 원문에 있으면 버린다. ③ 검토자에게 준 결과가 잘렸으면 그 결과에서 온 수치는 고치지 말고 짚기만 하라고 검토자 지시에 밝힌다.
- **다시 볼 시험**: OT-04 · 08 · 09 · DW-05. /health self_check 의 fixed 비율.

#### 지금 판에서의 자리

- 고쳐지지 않았다. 자기검증 블록은 기준 판 `app.py:4243-4480` 과 HEAD `:4345-4582` 가 글자까지 같다(diff 0줄, 102줄 밀림).
- HEAD 자리 — 검토자 입력 `_self_check_messages` `:4456-4496`(조회 결과를 자르는 `_sc_fit(res, cap["res"])` 는 `:4473` — 요청서 `:4371`), 검토자 답 읽기 `_self_check_parse` `:4499-4521`(바꿀 곳 쌍을 읽는 줄 `:4515` — 요청서 `:4413`), 넣기 `_sc_apply` `:4524-4543`, 판정 `_self_check_judge` `:4546-4571`.
- `_self_check_judge` 는 바꿀 곳을 넣은 뒤 길이(`_SELF_CHECK_MIN_RATIO` 0.4, `:4309`)와 잃은 그림만 본다. [새 글] 의 숫자를 조회 결과와 대조하는 코드는 없다. 수치 출처 대조 함수 `unsourced_numbers`(`evidence.py:38`)는 이미 있고, 지금은 초안의 수치를 검토자에게 짚어 줄 때(`:4484-4487`)와 고친 답의 근거 블록(`:4675`)에만 쓴다.
- 검토자가 받는 '조회 결과' 는 `turn_out` 이다(`:5259` 의 `_turn_out_add` — `:3484-3493`). 이 글은 모델이 본 결과, 곧 `_cap_tool.capped` 에서 허브 접기 · `_cap` 을 지난 뒤의 글이고(`:2008` · `:2011`), 좁은 창이면 결과마다 앞 120,000자 · 합 400,000자로 한 번 더 묶인다. 그 뒤 검토자 입력에서 `_sc_fit` 으로 다시 줄어든다.
- `/health` 의 `self_check` 는 상태별 수(ok · fixed · suspect · unreadable · failed · skipped) · ms · 마지막 실패를 싣는다(`_sc_health` `:4367-4373`, `/health` 칸 `:7220`). 다시 볼 시험의 fixed 비율은 이 counts 로 센다.
- OT-04 · 08 · 09 · DW-05 의 값과 '고침 12 · 의심 3 · 맞음 1' · '고침 15' 는 이 박스에서 대조 못 함(cae00 QA 보고서).

#### 우리 쪽 맞물림

- 설계 중이다 — 설계서 [`design-ha27.md`](../design-ha27.md)(커밋 전)의 한 줄은 '검토자가 낸 바꿀 곳([원문] · [새 글] 쌍)을 초안에 넣기 전에, 코드가 쌍마다 이번 턴 도구 결과 원문(접기 · 자르기 전)과 다시 대조해 넣음 · 짚음 · 버림을 정한다. 원문은 `_cap_tool.capped` 한 자리에서 턴마다 붙잡아 두고(문자 상한), 검토자에게는 결과마다 잘렸는지를 머리에 밝힌다. 검토자 호출은 지금처럼 한 번이다' 이다. 새 모듈 `sc_gate.py`, 손잡이 `CHAT_SELF_CHECK_GATE`(`1` · `num` · `0`) · `CHAT_SELF_CHECK_RAW_CHARS`(6,000,000), 새 상태 flagged, `/health` self_check 의 `fixed_ratio` · `gate` 칸을 둔다고 적었다(8 · 10절). 화면 후속(flagged 표시)은 포털 몫이고, update-all §7 의 관문 한 줄은 HP-55 와 함께 더하기를 권했다(11절 · Q12). 구현 · 반대 검토 전이라 바뀔 수 있다.
- 설계 차례는 [PLAN](../PLAN.md) '어떻게 하나' 1(높음 넷은 설계 에이전트가 먼저 안을 낸다)이다. 원문 붙잡기가 HA-28 · HA-29 · HA-30 과 같은 래퍼(`capped`)에 자리를 잡는다.
- 6절 셋째 줄 — 10-29 자기검증 패치 방식('바꿀 곳만 받는다')은 들어왔고, HA-27 은 그 방식의 정확도 문제다.
- 6절 첫째 줄 — TODO-20261029 R-07(invoke_tool 로 부른 허브 응답을 접지 않는다)은 HA-27 ③ 과 함께 본다. 10만 자 넘는 응답 11건이 그 길이었는지 가를 접기 흔적은 HA-34 가 남긴다(고치는 중).
- HA-28 설계서(5절)는 기다림 안내의 수(분 · 초 · 횟수 · 진행률)를 근거 글(outputs)에 넣어 '출처 없는 수' 로 잡히지 않게 한다고 적었다.
- DP-01(다시)(Datahub 플랫폼 — 사람이 보낸다, [outbound](../outbound.md) 2절) — 허브 응답이 여전히 커서 챗 문맥과 자기검증 입력을 크게 차지한다는 원천 몫이다.

### HA-28 · 높음 — 잡 상태를 LLM 으로 폴링한다

- **무엇이**: 잡 상태를 LLM 으로 폴링한다.
- **근거**: DW-02 후속 — run_checklist 를 건 뒤 get_task 를 26번 불렀고 LLM 요청이 29번 · 85초였다. 끝을 못 보고 저장된 옛 결과로 답했다. 같은 도구 네 번째의 '앞 결과를 써라' 꼬리(`app.py:1317`)는 폴링에 맞지 않는다.
- **할 일**: 상태 조회 도구(get_task · job_status · heaxstep_forge_job_status · docforge_status · doe_status · study_get 등 — 도구 쪽 '상태' 표지나 이름 목록)는 에이전트가 코드로 일정 간격(예 10초) · 상한(예 10분)까지 기다렸다가 끝났거나 상한에 닿은 결과만 LLM 에 넘긴다. 기다리는 동안 화면에 진행률을 흘린다.
- **다시 볼 시험**: DW-02 후속 · DW-03 후속.

#### 지금 판에서의 자리

- 요청서 `app.py:1317` 은 기준 판에서 `_turn_tool_calls` 의 주석 줄이다(문턱 `_TOOL_REPEAT_NOTE_AT = 4` 는 `:1320`). HEAD 에서는 `:1411` · `:1414` 이고, 꼬리 '[이 턴에 … 를 N번째 불렀다 — 앞 결과로 답할 수 있는지 먼저 보라 …]' 는 `_chat_result_note`(기준 판 `:1719-1735` → HEAD `:1813-1829`)가 단다. 글은 바뀌지 않았다.
- 챗 길에는 상태 조회를 코드가 기다리는 곳이 없다. get_task · job_status · heaxstep_forge_job_status · docforge_status · doe_status · study_get 은 `app.py` 에 기준 판 · HEAD 모두 0건이고, 도구 표지(readOnlyHint 등)를 읽는 코드도 0건이다.
- 참고 — 분석 루틴 실행기 `routine.py`(`d673846`, 기준 판 뒤)는 심의 단계에서만 `deliberate_status` 를 코드가 직접 되풀이해 본다(`_delib_wait` `routine.py:1535-1570`, 간격 `ROUTINE_DELIB_POLL_S` 기본 20초 `:52-53`). 일반 챗 ReAct 에는 같은 길이 없다.
- 챗에 묶는 도구의 결과는 `_prep_tool`(HEAD `:2085`)이 씌운 `_cap_tool.capped`(`:1832-2016`)를 지난다 — 기다리기를 넣을 래퍼가 HA-29 · HA-30 과 같다.
- DW-02 후속의 get_task 26번 · LLM 29번 · 85초는 이 박스에서 대조 못 함(cae00 QA).

#### 우리 쪽 맞물림

- 설계 중이다 — 설계서 [`design-ha28.md`](../design-ha28.md)(커밋 전)의 한 줄은 '상태 조회 도구(이름 목록으로 안다)가 도는 중을 돌려주면, 이 턴에 건 잡이거나 같은 호출의 되풀이일 때만 도구 래퍼 안에서 코드가 10초마다 다시 조회해 끝나거나 턴의 상한(600초)에 닿을 때까지 기다리고, LLM 에는 마지막 결과 하나와 기다린 사정 한 줄만 넘긴다' 이다. 손잡이 `CHAT_STATUS_WAIT_MAX_S`(600, 0 이면 끔) · `CHAT_STATUS_WAIT_POLL_S`(10) · `CHAT_STATUS_TOOLS` 와 `/health` 칸 `status_wait` 를 둔다고 적었다(4.10 · 4.11). 구현 · 반대 검토 전이라 바뀔 수 있다.
- HA-29 · HA-30 과 같은 래퍼(`_cap_tool.capped`)를 고치므로 맞물림을 함께 본다([PLAN](../PLAN.md) '어떻게 하나' 1). HA-30 설계서 6절 7 은 'HA-30 의 검사는 첫 호출 전에 한 번 돈다 — 다른 허브의 job_id 로는 기다리기를 시작하지 않는다' 로 차례를 적었다.
- StepForge 답(10-30, [outbound](../outbound.md) 1절) ② — `job_status(job_id)` 의 `status` 는 queued · running(도는 중) / done · failed · cancelled(끝), `progress` 0 ~ 100, `error` · `ended` · `result` 이고, 판 전체 측정은 수십 분이라 상한을 넉넉히 둬 달라고 했다. 이 박스 StepForge(`ff308d1`) 코드의 기다리는 상태 낱말은 queued 가 아니라 pending 이다(`app/mcp_server.py:1305` run_job 응답 · `:1372` · `:1575`, `app/` 에 queued 0건) — HA-28 설계서 2.6 도 소스대로 pending 을 적었다.
- DocForge 답(10-30 끝, 같은 표) ② — docforge_status 의 `status` 는 queued · running / done · failed · cancelled, `progress` 0 ~ 100, `stage` S0 ~ S7, `error` 다. 도구 오류는 `{ok:false, error, status:403}` 처럼 `status` 가 숫자라 숫자면 기다리기를 끝낸다. 잡은 한 번에 하나라 queued 는 앞 잡 대기다. DocForge 0.3.1 배치는 그 세션의 사용자 승인 대기다(cae00 release 는 아직 0.3.0).
- ST-12(StepForge, 그 뒤 판) — 합치기 단계 진행률은 StepForge 가 실물 큰 판에서 재 보고 정한다(답 ③). 그 전에는 판 전체 drop_check 의 진행률이 오래 그대로일 수 있다(ST-12 무엇이 — 10% 에 30분).
- 7절 셋째 줄 — DW-02 후속 · DW-03(후속 포함).

### HA-29 · 높음 — 사람에게 묻지 않고 무거운 잡을 건다

- **무엇이**: 사람에게 묻지 않고 무거운 잡을 건다.
- **근거**: DW-03 — StepForge run_job 두 번(graph · 판 전체 drop_check)을 확인 없이 걸었다. drop_check 는 10% 에서 1,812초를 돌다 사용자 결정으로 취소했다(단일 러너를 잡고 있었다). 프롬프트의 '잡 제출은 먼저 확인'(`app.py:162`)이 지켜지지 않는다. 운영자 정의에는 이미 `writes` · `confirm` 목록이 있다(포털 `infra/personas/he-team.json`).
- **할 일**: 잡을 시작하는 도구(run_job · run_checklist · docforge_convert · 클러스터 제출 · 운영자 정의의 `writes`)는, 이번 턴 사람 발화가 그 일을 분명히 시키지 않았으면 코드 단에서 확인 카드로 멈춘다. 도구가 '예상 작업량' 을 주면 확인 문구에 싣는다.
- **다시 볼 시험**: DW-03.

#### 지금 판에서의 자리

- 프롬프트 줄 '등록·발행·삭제·잡 제출처럼 되돌리기 어려운 도구는 무엇을 어디에 하는지 사용자에게 먼저 확인하고 호출하세요.' 는 HEAD `app.py:162-163` 에 그대로 있다(줄도 같다).
- 코드 관문은 없다. run_job · run_checklist · docforge_convert · submit_job 이름도, 도구 표지(readOnlyHint 등) 읽기도 `app.py` 에 기준 판 · HEAD 모두 0건이다.
- 운영자 `writes` · `confirm` 은 지금 에이전트 서버에 코드가 읽을 칸으로 오지 않는다. 포털 동기화 `infra/scripts/sync-he-personas.py` 는 두 목록을 system_prompt 의 '## 상태를 바꾸는 도구' 두 줄로만 만들고(`:71-77`), AIDataHub 에 싣는 `response_config` 는 persona_kind · mcp_apps · key_tools · managed_by 뿐이다(`:169-171`). 에이전트 `_persona_meta`(HEAD `app.py:3997-4051`)도 `response_config` 에서 persona_kind · mcp_apps · key_tools 만 읽는다(`:4039-4042`).
- 포털 main 의 운영자 19명 가운데 writes 가 빈 운영자는 일곱이다(he-cad-odbhub · he-calc-laminate · he-data-signalforge · he-data-arp · he-data-coreontology · he-research-web · he-expert-risk). DW-03 의 run_job 은 he-cad-stepforge 의 writes 에, docforge_convert 는 he-doc-docforge 의 writes 에 이미 있다.

#### 우리 쪽 맞물림

- 설계 중이다 — 설계서 [`design-ha29.md`](../design-ha29.md)(커밋 전)는 막는 도구를 잡 시작(에이전트 코드의 바닥 목록 24개) · 쓰기(운영자 `writes`) · 되돌리기 어려운 것(운영자 `confirm`) 셋으로 가르고, 목록은 에이전트 서버가 형제 리포의 `infra/personas/he-team.json` 을 직접 읽는다고 적었다(HP-53 이 채우면 재기동 없이 들어온다 — 지금 판의 '목록이 칸으로 오지 않는다' 를 이 길로 메운다). 관문 `_confirm_gate` 는 `capped` 안 한 자리이고, 막으면 도구를 부르지 않고 턴을 끊어 확인 카드(SSE `confirm` 사건 + 본문 끝 글, 번호 `cf-…`, 서버 메모리 30분)를 낸다. 승인하면 서버가 그 호출을 인자 그대로 한 번 보낸다. 손잡이는 `CHAT_CONFIRM_GATE`(기본 1), `/health` 칸은 `confirm_gate` 이고, 화면(확인 카드)은 포털 프론트가 받는다(5.5 · 5.6). 게이트웨이 `/tools-map` 의 `write` 표지는 dev 실측에서 docforge_convert · 낙하 제출을 놓쳐 출처로 쓰지 않는다(1.5). 구현 · 반대 검토 전이라 바뀔 수 있다.
- 차례 — HA-30 설계서 6절 5 는 확인 카드를 HA-30 의 다른 허브 id 검사 뒤에 두라고 적었다(틀린 id 의 호출로 확인을 받으면 그 확인이 헛것이 된다). HA-28 설계서 5절은 확인 카드를 부르기 전 관문으로 보고, 사람이 확인한 턴에 걸린 잡을 그 턴의 상태 조회가 기다린다고 적었다.
- HP-53(포털, 고치는 중) — 운영자 정의의 writes · confirm 을 채운다. 요청서는 '근본 고침은 HA-29 이고 이 행은 그 관문이 읽을 목록을 채우는 짝' 이라 적었다. 판단 C-5 — ODB 몫도 목록(writes · confirm)은 지금 채우고 todo · key_tools 는 OB-26 뒤다. HA-29 설계서 7절은 관문이 켜지면 동기화가 만드는 운영자 프롬프트 두 줄과 시스템 프롬프트 넷째 규칙(`app.py:161-163`)을 '서버가 확인 카드로 승인을 받는다 — 글로 따로 묻지 않는다' 쪽으로 바꾸기를 권했다(이중 확인을 피한다).
- KR-23(KooRemapper, 답 기다림) — recipe_propose · recipe_register 가 운영자 writes 에 없어 확인 카드에 걸리지 않는다. 포털 몫은 HP-53(DynaForge 운영자 writes 에 레시피 도구)이다.
- StepForge 답 ① — 시작 전 작업량은 이미 있는 읽기 도구 `estimate_cost(project_id, job, args)`(칸 `expected_s` · `cost_basis` · `gateway_verdict`(over · may_exceed · under · no_basis) · `basis_note` · `advice`)로 셀 수 있고, ST-12 (2)가 판 전체 작업량 칸을 여기와 run_job 시작 응답에 더한다(칸 이름은 짓고 알린다).
- DocForge 답 ③ — readOnlyHint 는 읽기 넷(capabilities · list_inputs · status · package)에만 있어 docforge_convert · docforge_cancel 에는 없다.
- HP-54(조건부, 판단 C-4) — OB-92 에서 둘째 길을 고르면 ste 의 submit_job · set_job_sync 가 writes, ste_cancel_job 이 confirm 에 든다(요청서 HP-54 할 일). HA-29 할 일의 '클러스터 제출' 에 드는 도구다.
- AD-21(AIDataHub, 판단 C-7 로 이 세션이 고치는 중) — 운영자 정의 동기화가 저장 뒤 500 에 첫 건에서 멈춘다. HP-53 · HP-54 가 이 동기화를 탄다(요청서 AD-21 근거). 포털은 저장 여부를 다시 읽어 확인하고 이어 가게 고치는 중이다([outbound](../outbound.md) 2절 셋째). HA-29 설계서 7절은 관문이 동기화와 무관하게 he-team.json 을 읽어 AD-21 을 기다리지 않는다고 적었다.
- 7절 셋째 줄 — DW-03(후속 포함).

### HA-30 · 중간 — 허브를 건널 때 앞 허브의 id 를 그대로 넘긴다

- **무엇이**: 허브를 건널 때 앞 허브의 id 를 그대로 넘긴다.
- **근거**: OT-07 — failuretrace_graph_neighbors 에 자주검증 id 를 넘겨 APP-GRAPH-0001 이었다(규칙 ⑤ 가 있는데도).
- **할 일**: 허브 도구를 부를 때 object_id 가 다른 허브의 결과에서 온 것이면(이번 턴 결과에서 그 id 를 낸 도구의 앱으로 안다) 코드가 key 로 그 허브에서 다시 resolve 하거나, 부르기 전에 '이 id 는 ○○ 허브 것 — key 로 다시 풀어라' 를 돌려준다.
- **다시 볼 시험**: OT-07.

#### 지금 판에서의 자리

- 규칙 ⑤ 는 HEAD `app.py:193`(어휘표가 없을 때의 기본 글 `_CORE_RULES_DEFAULT`)과 `:303`(어휘표로 짓는 `_core_rules_text` — '다른 허브' 이름은 어휘표 apps 의 role sibling 에서 온다, `:291`)에 있다(기준 판 `:193` · `:271`). 프롬프트 글뿐이다.
- 코드 관문은 없다. `object_id` 는 `app.py` 에 기준 판 · HEAD 모두 0건이다.
- 결과를 낸 앱을 아는 자리는 있다 — 챗 도구 결과 머리 '[이 결과는 ○○ 앱의 … 이다]'(`_chat_result_note` HEAD `:1813-1818`, 라벨은 `_app_label_cached` `:1804` 의 캐시). 유령 ID 막이(`_learn_ids` `:1437-1444` · `capped` 안 `:1919-1937`)는 이번 턴 결과의 정수만 모으고 어느 앱의 결과였는지는 적지 않는다. `_phantom_id_arg`(`:1606-1616`)는 정수 값만 보므로 UUID 글 id 에는 닿지 않는다.
- OT-07 의 APP-GRAPH-0001 실측은 이 박스에서 대조 못 함. HA-30 설계서(10절 7)도 dev 게이트웨이에 허브가 붙어 있지 않아 OT-07 을 dev 에서 실물로 다시 볼 수 없다고 적었다.

#### 우리 쪽 맞물림

- 설계 중이다 — 설계서 [`design-ha30.md`](../design-ha30.md)(커밋 전)의 결정은 '이 턴에 허브 도구가 성공으로 돌려준 결과의 UUID 를 허브별로 적고, 허브 도구를 부르기 직전 인자의 UUID 가 다른 허브에서만 본 것이면 보내지 않고 대상 허브의 key 로 다시 풀 정확한 다음 호출과 함께 돌려준다' 이다. 요청의 첫째 안(코드가 대신 key 로 다시 풀어 바꿔 보내기)은 고르지 않았다(5절). 손잡이는 `CHAT_XHUB_ID_GATE` 다(9.1 R1). 구현 · 반대 검토 전이라 바뀔 수 있다.
- HA-28 · HA-29 와 같은 래퍼를 고친다 — 설계서 6절이 차례(거부 둘 → 유령 ID 막이 → HA-30 검사 → HA-29 확인 카드 → 인자 기본값 → HA-28 기다리기가 감싸는 호출 → 접기 · 자르기 뒤 배우기)를 적었다.
- 허브 판정은 포털 `core_vocab.json` 의 canonical · role sibling 에서 온다(설계서 2.1 · 3.2). 같은 파일에 HA-32 가 칸을 더하는 중이다(포털 가지 `wt1030/vocab`).
- 설계서 9.2 Q9 — 개인 Claude(게이트웨이 MCP 직접 연결)에는 이 관문이 없어, 허브의 '객체를 찾을 수 없습니다' 문구에 'key 로 object_resolve' 한 줄을 DP-14(조건 주소 예)와 같은 묶음으로 청하자고 권했다(사람이 보낸다 — 권고 단계).
- 이 요청서에서 HA-30 을 가리키는 다른 행은 없다.

### HA-31 · 중간 — 전문가 검색 가로채기

- **무엇이**: 전문가 검색 가로채기 — 질문을 LLM 없이 '전문가 추천' 목록으로 답한다.
- **근거**: DW-13 — 'PCB 내부 크랙을 잘 아는 전문가 에이전트를 추천하고, 추천 근거가 된 기록 수를 알려줘.' 가 `is_agent_search`(`app.py:2587-2591` — 80자 이하 + '(전문가 · 에이전트) … (추천 · 알려 · 찾 …)')에 걸려 `run_agent_search`(`:2602`, 부르는 곳 `:5646`)로 갔다. LLM 0회 · 추천 10명 중 절반 무관(로그 플랫폼 · MCP 레지스트리 · 카메라 MIPI 등) · '기록 수' 는 답하지 않았다. 전문가(AI 데이터 허브 운영자)를 고른 대화에서도 가로챘다.
- **할 일**: 빗금 트리거('/전문가' 등)만 결정적 목록으로 답하고, 자연어는 질문에 다른 물음(수 · 근거 · 비교 · 조건)이 없을 때만 가로챈다. 전문가를 고른 대화에서는 가로채지 않는다. 추천 순위에 무관한 사람이 오르는 까닭(recommend 점수 · 분야 섞기)을 본다.
- **다시 볼 시험**: DW-13.

#### 지금 판에서의 자리

- main 은 고쳐지지 않았다. `is_agent_search` 는 HEAD `app.py:2681-2685`(빗금 트리거 `:2676` · 자연어 정규식 `:2677-2678`), `run_agent_search` 는 `:2696`, 질문 전체를 q 로 넘기는 recommend_agents 호출은 `:2712`(AD-19 가 적은 기준 판 `:2618`), 부르는 곳은 `chat()` `:5754-5756` 이다. 글은 기준 판과 같고 줄만 밀렸다(+94 · +108).
- `chat()`(`:5708-`)의 가지는 `req.pinned_agent` · `req.pinned_agents`(ChatRequest `:1063` · `:1068`)를 보지 않고 `is_agent_search` 로 가른다 — 전문가를 고른 대화도 가로챈 자리다.
- 같은 판정이 권한 검사에도 쓰인다 — `_denied_feature`(`:1117-1137`)는 `is_agent_search(m)` 이면 `feat:expert-chat` 을 요구한다(`:1127-1128`, 주석 '트리거 순서는 chat() 과 같다'). 판정을 좁히면 이 권한 길도 함께 바뀐다.
- 가지 `wt1030/ha31`(`90daab8`) 에서 고치는 중이다 — 커밋 제목은 '전문가 검색 가로채기를 좁힌다 — 빗금 트리거('/전문가' 등)만 늘 목록이고, 자연어는 다른 물음(수 · 근거 · 비교 · 조건, …' 으로 이어진다(main 에 합치기 전 · 반대 검토 중).

#### 우리 쪽 맞물림

- AD-19(AIDataHub) — 요청서가 'HA-31 끝의 '추천 순위 까닭' 몫은 이 행이 받는다' 고 적었다. 나눔은 [outbound](../outbound.md) 2절 둘째 — 에이전트는 '추천 근거 · 기록 수' 처럼 다른 물음이 든 질문을 가로채지 않게 고치고, 추천 점수의 낱말 겹침 항은 AIDataHub 몫이다. 판단 C-7(사용자 결정 10-30)로 AIDataHub 코드 행(AD-19 · AD-20 포함)도 이 세션이 고치는 중이다([checklist](../checklist.md) 3b).
- AD-20 — 추천의 근거 기록 수와 전문가 기록 목록이 두 저장소로 어긋날 수 있다. HA-31 뒤 DW-13 의 '기록 수' 를 챗 에이전트가 답할 때 그 수가 닿는 자리다.
- 7절 다섯째 줄 — DW-13.

### HA-32 · 낮음 — 없는 코어 타입 이름을 지어내 부른다

- **무엇이**: 없는 코어 타입 이름을 지어내 부른다.
- **근거**: DW-22 — object_resolve(type_slug='management_standard')(실제는 criterion).
- **할 일**: 코어 규칙 글에 어휘표 낱말 → 타입 이름 대응(고장모드 → failure_mode · 관리 기준 → criterion · 시험항목 → test_item …)을 한 줄로 싣는다(`core_vocab.json` 에 칸을 더해 만든다).
- **다시 볼 시험**: DW-22.

#### 지금 판에서의 자리

- main 은 고쳐지지 않았다. 코어 규칙 글은 `_core_rules_text`(HEAD `app.py:286-306`)가 어휘표의 rule_words · canonical · relations · apps 로 짓고, 낱말 → 타입 이름 대응 줄은 없다.
- 어휘표 정본은 포털 `backend/config/core_vocab.json` 이다 — 에이전트가 형제 리포 경로로 읽고(`:247-253`), 바뀐 시각마다 다시 읽는다(`_core_vocab` `:309-348`, 읽는 칸 `build` `:323-325`). 포털 main 의 이 파일은 `aec8e29` 뒤 커밋 0(마지막 `c398230`)이고, 칸은 `_doc` · version · canonical · rule_words · search · relations · apps 뿐이다. search 의 영어 낱말(failure mode · test item · virtual validation · criterion)은 타입이 아니라 도구 이름에 잇는 칸이다(`_doc` 의 search 설명).
- 박스 덧씌우기 `core_vocab.local.json`(`ab87137`, 기준 판 뒤)도 merge patch 로 받는다. 칸을 더하면 `/health` `core_vocab` 의 지문(`:393-401`)이 게이트웨이와 함께 바뀐다 — 두 서비스가 같은 파일을 같은 셈으로 읽는다(주석 `:251-252`, 가드 `tests/test_request_1029.py:356-371`).
- 가지에서 고치는 중이다 — 에이전트 서버 `wt1030/vocab`(`ac2aec0` — 코어 규칙 ① 끝에 타입 이름 대응 한 줄) · 포털 `wt1030/vocab`(`e3e2ad2` — 어휘표 칸 `types`). 둘 다 main 에 합치기 전이다.

#### 우리 쪽 맞물림

- 포털 `backend/config/core_vocab.json` 도 함께 바뀐다 — 요청서대로 줄은 어휘표의 새 칸으로 만들므로 포털 커밋이 같이 가야 cae00 에 그 줄이 선다. 게이트웨이도 같은 파일을 읽는다(어휘표 `_doc` — search · canonical.tagline).
- 같은 파일을 HP-56 도 만진다 — 포털 가지 `wt1030/vocab` 의 `f780255` 가 발동 낱말에 '전작' · '후속 모델' 을 더하는 중이다(맨 '후속' 은 심의 낱말을 가로채서 넣지 않는다고 적었다).
- HA-30 설계가 같은 어휘표의 canonical · sibling 으로 허브를 가른다.
- 다시 볼 시험 DW-22 는 행의 칸에만 있다(7절 표에는 없다).

### HA-33 · 중간 · 심의 — VOC 미리보기가 search_voc 의 새 반환 꼴을 못 펼친다

- **무엇이**: (중간 · 심의) 심의 전 VOC 미리보기가 `search_voc` 의 새 반환 꼴(객체 안 `results`)을 펼치지 않아, 실패 표시 없이 0건이 된다.
- **근거**: `app.py:6015`(search_voc 호출) · `:6021`(`_parse_json_multi` 결과의 원소마다 `_voc_row`). `_parse_json_multi`(`deliberation.py:2139` · `:2153`)는 객체 하나를 `[객체]` 로 돌려주고, `_voc_row`(`app.py:5980`)는 맨 위에 본문 칸이 없어 text 가 빈다. 빈 text 는 `:6026` 에서 걸러지고 실패로 세지 않아 `degraded` 도 거짓이다(`:6032`). SignalForge `d2a794d` `mcp-server/server.py:195` · `:209-217` 은 늘 `{total, results, strategy, match_mode, notes}` 를 돌려준다.
- **할 일**: 결과가 객체이고 `results` 가 목록이면 그 목록을 펼쳐 읽는다. 펼친 뒤에도 0건이면 `notes` 를 미리보기에 싣는다. 펼칠 것이 없는데 결과 글이 비지 않았으면 0건 대신 `degraded` · `partial` 로 센다.
- **출처**: TODO-20261029 R-06 · reflection-1028/08 3절 1 · reflection-1028/00-SUMMARY 4절

#### 지금 판에서의 자리

- main 은 고쳐지지 않았다. HEAD `app.py` — `_voc_row` `:6088`(본문은 맨 위 칸 content_translated · content_original 만 본다 `:6090`), `/deliberate/voc-preview` `deliberate_voc_preview` `:6104-6144`, search_voc 호출 `:6123`, 원소마다 `_voc_row` `:6129`, 빈 text 거르기 `:6134`, `degraded` `:6140` · `partial` `:6141`. 글은 기준 판과 같고 줄만 +108 밀렸다.
- `_parse_json_multi` 는 `deliberation.py:2139`(객체 하나면 `[객체]` — `:2153`)이고, `deliberation.py` 는 기준 판 뒤 커밋 0 이라 줄이 같다.
- SignalForge 는 이 박스 HEAD 가 요청서 대조 판과 같은 `d2a794d` 다. `mcp-server/server.py:195-196` 의 설명이 '반환은 늘 객체입니다 — {total, results, strategy, match_mode, notes}' 이고, `:209-217` 의 두 길(semantic 끔 · 켬)이 모두 그 꼴을 돌려준다(끔 길에는 truncated 도 있다 — `:212`).
- 가지 `wt1030/ha33`(`9255db2`, main 위 커밋 둘) 에서 고치는 중이다(main 에 합치기 전 · 반대 검토 중).

#### 우리 쪽 맞물림

- SignalForge 가 `{results, notes}` 봉투의 칸 이름을 지켜야 이 고침이 맞다 — signalforge-c6 에 SG-04(다시) · SG-19 와 함께 '칸 이름을 지켜 달라' 를 보냈고 답은 기다림이다([outbound](../outbound.md) 1절).
- 이 요청서의 HA-/HG-/HP- 행 가운데 VOC 미리보기를 만지는 다른 행은 없다.

### HA-34 · 낮음 — 허브 응답 접기가 걸렸는지 흔적이 없다

- **무엇이**: (낮음) 허브 응답 접기가 실제로 걸렸는지 로그 · `/health` 어디에도 남지 않는다. 그래서 10-29 · 10-30 두 재시험이 접기의 효과를 가리지 못했다.
- **근거**: `app.py:1656`(`_fold_hub_result`) · `:1909-1917`(invoke_tool 경유도 안쪽 이름으로 접는다). 접은 표지는 LLM 에 가는 결과 글 머리(`:1652` · `:1707`)에만 붙는다. HEAD 에 `fold_count` · `fold_stats` 가 0건이고, 접기 문구가 든 print 도 0건이다.
- **할 일**: 허브 응답을 접을 때 로그 한 줄(도구 이름 · 원문 자 수 · 접은 뒤 자 수)을 남기고, `/health` 에 접은 횟수를 싣는다.
- **출처**: QA-CHAT-QWEN-20261030 4절 · 이 요청서 6절 첫 줄(R-07) · TODO-20261029 R-07 ①

#### 지금 판에서의 자리

- main 은 고쳐지지 않았다. HEAD `app.py` — `_fold_hub_lists` `:1722-1747`(접은 표지 `:1746`), `_fold_hub_result` `:1750-1801`(표지 `:1801`), invoke_tool 경유도 안쪽 이름으로 접는 곳 `:2002-2013`(요청서 `:1909-1917` → `:2003-2011`). 글은 기준 판과 같다.
- `fold_count` · `fold_stats` 는 기준 판 · HEAD 모두 0건이고, 접기 문구가 든 print 도 0건이다. 표지는 LLM 에 가는 결과 글 머리에만 붙는다. `/health` 는 `:7182` 이다.
- 가지 `wt1030/ha34`(`f450a69`, main 위 커밋 둘) 에서 고치는 중이다(main 에 합치기 전 · 반대 검토 중).

#### 우리 쪽 맞물림

- 6절 첫째 줄(R-07) — 10만 자 넘는 응답 11건이 invoke_tool 길이었는지 가르지 못했다. HA-27 ③ 과 함께 본다.
- HA-28 설계서는 `/health` 의 기다림 칸 · 로그 한 줄을 'HA-34 의 교훈(흔적이 없으면 재시험이 효과를 못 가린다)' 으로 두고 자물쇠도 HA-34 와 같은 꼴로 한다고 적었다(4.10). HA-30 설계서 9.2 Q8 은 막은 수를 로그 한 줄만 두고, 필요해지면 HA-34 의 `/health` 칸 옆에 둔다고 적었다.
- OB-96(5절, 사람 몫) — 허브 큰 응답 견본에서 사람 이름을 지워 개발 쪽에 넘기면 개발이 칸 모양에 맞춰 접기 규칙을 짓는다. 끝 절 HA-34 · DP-01(다시)와 맞물린다.
- DP-01(다시)(사람이 보낸다, [outbound](../outbound.md) 2절) — 원천 몫(objects_list 의 ref_labels · objects_summary 의 group_options · object_get 의 related)은 그대로다.

### HA-08(다시) · 낮음 · 심의 — 위키 꺼짐 글귀가 MX 백서 문구와 어긋난다

- **무엇이**: (낮음 · 심의) 위키 도구가 실린 채 꺼진 박스에서, 엔진이 찾는 꺼짐 글귀와 MX 백서 MCP 문구가 어긋난다. 그러면 챗에 보이는 심의 결정문 단마다 종전 오류 문구가 다시 붙는다. 지금은 위키 도구가 실리지 않아(MW-01) 잠복 상태다.
- **근거**: `deliberation.py:3294`(`_WIKI_OFF_HINTS` = 'wiki_disabled' · '위키는 아직 열리지 않았다') · `:3387`(도구 결과 글에서만 찾는다). MXWhitePaper `f242254` `dist/llm-docx-toolkit/mcp/api_client.py:104` 의 문구는 '…열리지 않았습니다' 이고, wiki_disabled 는 예외의 code 칸에만 둔다(`:487-488`). 10-30 게이트웨이 `/tools-map` 에 wiki_* 는 0개다.
- **할 일**: 꺼짐 글귀를 '열리지 않았' 까지로 줄이거나, MX 백서 MCP 문구도 함께 받는다.
- **출처**: reflection-1028/03 HA-08(일부) · TODO-20261029 R-07 ③ · 90-OURS OB-64 · OB-65

#### 지금 판에서의 자리

- main 은 고쳐지지 않았다. `deliberation.py` 는 기준 판 뒤 커밋 0 이다 — `_WIKI_OFF_HINTS` `:3294` = ('wiki_disabled', '위키는 아직 열리지 않았다'), 도구 결과 글에서만 찾는 줄 `:3387`(맞으면 `_WIKI_OFF_NOTE` `:3295-3296` 한 줄). 위키 도구가 아예 없으면 `_wiki_submit`(`:3368`)이 `:3374-3378` 에서 같은 한 줄을 낸다.
- MXWhitePaper 는 이 박스 HEAD `bd2e79b`(`f242254` 의 자손)이고 `dist/llm-docx-toolkit/mcp/api_client.py` 는 `f242254` 뒤 커밋 0 이다 — `WIKI_OFF_MESSAGE` `:104` 'MX 백서 AI 위키는 아직 열리지 않았습니다 — 문서 찾기는 search_documents 를 쓰세요', `wiki_disabled` 는 예외의 code 칸(`:487-488`). 엔진 글귀 '위키는 아직 열리지 않았다' 는 이 문구('…않았습니다')의 부분 글이 아니다.
- 10-30 cae00 게이트웨이 `/tools-map` 의 wiki_* 0개는 이 박스에서 대조 못 함.
- 가지 `wt1030/ha08` 에서 고치는 중이다(main 에 합치기 전이라 바뀔 수 있다). 첫 커밋 `fb506f9` 의 제목은 꺼짐 글귀를 'MX 백서 두 문구가 함께 쓰는 줄기 '위키는 아직 열리지 않았'' 로 줄인다는 것이고, 둘째 `ae861fe` 는 반대 검토 고침이다(제목 — '꺼짐 시험을 진짜 MCP 사슬로 돌리고 줄기 '위키는 아직' 과 code 꼴 wiki_disabled 를 따로 고정, …').

#### 우리 쪽 맞물림

- MW-01(다시) — MX 백서 답(10-30 끝, [outbound](../outbound.md) 1절)은 `bd2e79b`(MW-01) · `bb0a6a1`(MW-12)다. `_wiki_switch` 가 켜짐 · 꺼짐 · 모름 셋이 되어 http 모드는 모름이면 `wiki_*` 를 싣지 않고 10초마다 다시 봐 켜짐일 때 14개를 싣는다. 꺼짐 문구 '…열리지 않았습니다' 는 그대로 두고 HA-08 이 받는다. cae00 은 update-all 의 git 받기로 간다.
- OB-64 · OB-65(5절, 사람 몫) — 위키 버튼 숨김(M-11 · M-12)과 위키 질문(M-13)을 웹 챗에서 본다. 끝 절의 HA-08(다시) · MW-01(다시)와 맞물린다.

## 끝나면

- **보고할 곳** — HWAX 포털 세션 `hwaxportal-a5`(이 시트의 행은 그 세션이 고친다). 행마다 main 에 합친 커밋 번호를 [checklist](../checklist.md) 1절 그 줄에 적고 `[x]` 로 바꾼다.
- **올리기 전** — 행마다 그 행의 시험 · 설계만 읽은 블랙박스 시험 · 반대 검토 · 변이 시험([PLAN](../PLAN.md) '어떻게 하나' 3 ~ 5). 가지를 main 에 차례로 합친 뒤 에이전트 서버 전체 회귀를 한 번 돈다 — 리포마다 한 번에 하나이고, 도는 동안 그 리포에 커밋하지 않는다(판단 C-6 · PLAN 4).
- **배포물** — 에이전트 서버는 SIF · Drive 판이 없다(`start.sh` 가 리포의 `.venv` 로 띄운다). `git push`(끝난 리포부터) 뒤 cae00 은 update-all 이 리포를 받고 §4 에서 재기동한다. 도는 심의가 있으면 새 심의를 멈추고 `HWAX_DELIB_WAIT_S`(기본 600초)까지 기다리며, 넘기면 재기동을 미루고 ○ 로 남긴다(`infra/scripts/update-all.sh` 머리 주석). HA-08(다시)의 `deliberation.py` 도 이 재기동으로 반영된다. HA-32 의 어휘표 칸과 HP-56 은 포털 커밋으로 같이 간다(포털도 update-all 이 받는다). HA-27 · HA-29 가 설계대로 들어가면 포털 화면(자기검증 flagged 표시 · 확인 카드)도 바뀌어 프론트 빌드 + Drive 가 따라간다([PLAN](../PLAN.md) '어떻게 하나' 6).
- **cae00 사람 몫** — `docs/request-1030/server-setup.md` 에 명령 · 기대값으로 적는다(대조 시각에 아직 없다 — [checklist](../checklist.md) 4절 · [PLAN](../PLAN.md) 성공 기준).
  - OB-91 — 박스 우회 `CHAT_STABLE_PREFIX=0`(에이전트 서버 .env, 10-30 09:55 재기동) — HA-26 이 들어오면 줄을 지우고 재기동한다. 상태 — 들어가 있다(Knox 봇 연동 세션, 백업 `~/portal-backups/agent.env.stableprefix-*`).
  - HA-27 — `/health` 의 `self_check.counts` 로 fixed 비율을 고치기 전 · 뒤로 견준다(설계대로면 `fixed_ratio` · `gate` 칸이 생긴다).
  - HA-34 — 허브 응답을 접은 턴의 에이전트 로그 한 줄과 `/health` 의 접은 횟수를 본다(칸 이름은 구현이 정한다).
  - HA-27 ~ HA-30 — 설계대로 들어가면 새 손잡이(HA-27 `CHAT_SELF_CHECK_GATE` · `CHAT_SELF_CHECK_RAW_CHARS`, HA-28 `CHAT_STATUS_WAIT_MAX_S` · `CHAT_STATUS_WAIT_POLL_S` · `CHAT_STATUS_TOOLS`, HA-29 `CHAT_CONFIRM_GATE`, HA-30 `CHAT_XHUB_ID_GATE`)의 기본값과 끄는 법, 새 `/health` 칸(`status_wait` · `confirm_gate`)의 기대값을 함께 적는다. 설계 단계라 이름은 바뀔 수 있다.
- **7절 — 이 플랫폼의 다시 볼 시험**

| 시험 | 언제 | 볼 것 |
|---|---|---|
| OT-04 · 08 · 09 · DW-05 | HA-27 뒤 | 초안의 맞는 값이 그대로 나간다. |
| 전문가 · 앱 핀 · 붙인 문서 챗 | HA-26 뒤, 우회(OB-91)를 걷은 상태로 | 400 이 없다. 접두 캐시 적중을 다시 잰다. |
| DW-02 후속 · DW-03(후속 포함) | HA-28 · HA-29 뒤 | 상태 조회가 LLM 왕복 없이 기다린다. 잡은 확인 뒤에만 건다. |
| DW-13 | HA-31 뒤 | 질문이 챗 에이전트로 가고 '기록 수' 를 답한다. |

- **행의 칸에만 있는 다시 볼 시험** — HA-30 의 OT-07 · HA-32 의 DW-22(7절 표에는 없다). OT-07 은 dev 게이트웨이에 허브가 없어 cae00 에서만 볼 수 있다(HA-30 설계서 10절 7).
- **5절의 사람 몫 가운데 이 행들과 묶인 것**
  - OB-63 — 자기검증 손 시험 — 도구 없는 턴의 '(근거 없음 — 추정)' 재현 · 짧은 답 건너뛰기 · 긴 답 중지(M-7 ~ M-10).
  - OB-64 · OB-65 — 위키 버튼 숨김(M-11 · M-12)과 위키 질문(M-13)을 웹 챗에서 본다. 끝 절의 HA-08(다시) · MW-01(다시)와 맞물린다.
  - OB-96 — 허브 큰 응답(graph_neighbors · object_fields · object_references) 견본에서 사람 이름을 지워 개발 쪽에 넘긴다. 개발이 그 칸 모양에 맞춰 접기 규칙을 짓는다(포털 `docs/request-1029` checklist O-12 · context-notes C-22).
- **이 시트의 행이 아닌데 에이전트 서버를 가리키는 것**
  - AD-07(다시) — 그 행의 할 일이 '에이전트 서버 HA-11 이 이것을 기다린다' 다. AIDataHub 코드는 판단 C-7 로 이 세션이 고치는 중이고, 그 뒤에 에이전트 HA-11(10-27 행)이 온다([checklist](../checklist.md) 3b).
  - HP-42(다시) — 에이전트 HA-20(ui_resource SSE, 2단계)이 먼저다. 지금은 손대지 않는다(판단 C-2).
  - HP-55 — update-all 문구를 에이전트의 `CHAT_TOOL_SCHEMA_BUDGET` 예산 셈(요청서 `app.py:2296` → HEAD `:2390`)에 맞춘다. 에이전트 코드는 그대로다.
  - OB-97 — `arp_upload_open` 실측이 오면 패널 전용 도구 집합에 더한다(요청서 `app.py:2718-2719` 주석 → HEAD `:2812-2813`, 집합 `_CHAT_PANEL_TOOLS` `:2814-2815`).
  - OB-71 · OB-93 · OB-95 — 에이전트 서버 손잡이 · 측정(사람 몫)이다. '예고만 하는' 호출(잦으면 그때 따로 청한다) · `CHAT_TOOL_SCHEMA_BUDGET` 40000 → 30000 · `CHAT_LLM_REASONING_EFFORT` high · medium.
  - DP-01(다시) — 에이전트 쪽 접기는 이미 들어왔다(그 행의 근거 `app.py:1618-1625` · `:1909-1917` → HEAD `:1712-1719` · `:2003-2011`). 원천 몫만 남았다.
