# 90 우리 몫(cae00 박스 · 사람) — 10-30 요청에서 할 일

- **받는 곳** — cae00 운영(사람). 세션으로 보내지 않는다.
- **어떻게 갔나** — 보내지 않는다(요청서 5절 '우리 몫(보내지 않음)'). 요청서는 이 몫을 머리의 건수에 넣지 않았다. 사람이 cae00 에서 칠 명령 · 기대값은 합친 뒤 [`../checklist.md`](../checklist.md) 4절이 쓰는 `server-setup.md`(아직 없다)에 옮긴다.
- **요청서 정본** — [`../../request_261030.md`](../../request_261030.md) 5절 '우리 몫(보내지 않음)' 표의 스물일곱 줄 전부다 — OB-91 ~ OB-103 과, 끝 절이 '우리 몫은 5절 표 끝(OB-96 이후)에 더했다' 고 적은 OB-01 ~ OB-89. 이 행들에 닿는 7절 '다시 볼 시험' 은 끝의 '끝나면' 에 옮겼다. 같은 요청의 계획 · 판단 · 체크리스트 · 보낸 것은 [`../PLAN.md`](../PLAN.md) · [`../context-notes.md`](../context-notes.md) · [`../checklist.md`](../checklist.md) · [`../outbound.md`](../outbound.md) 다.
- **cae00 기준 판** — 없다(`-`). 이 시트는 한 리포의 판에 묶이지 않는다. 행이 든 `파일:줄` 은 요청서 머리의 기준 판(포털 `aec8e29` · 에이전트 서버 `969e723` · 게이트웨이 `44f4b8d`)의 줄이다(요청서 5행 — '줄 번호는 위 기준 판의 것이다'). 셋 다 이 박스에 있고 각 리포 HEAD 의 조상이다.
- **이 박스(dev)에서 대조한 판** — 포털 `bf5cd94` · 에이전트 서버 `7ca3a2e` · 게이트웨이 `67d8d00`(master) · AIDataHub `ac42bc6` · StepForge `ff308d1` · DocForge `559ec87` · SignalForge `d2a794d` · MXWhitePaper `bd2e79b` · SmartTwinMCP main `a98b9a7`(체크아웃 가지 `feat/cuboid-scatter-drop` `97c0e0b`) · 대조 시각 2026-10-30 18:13 KST. 형제 워크트리(`*-wt-1030-*`)는 열지 않았다 — 고치는 중인 행은 요청서 · 체크리스트 · 판단 · 보낸 글에 적힌 계획으로만 적었다. cae00 박스의 값(`.env` · crontab · 박스 권한표 · `provision.env` · Drive · 떠 있는 서비스)은 이 세션이 닿지 않아 대조하지 않았다.
- **읽는 법** — 5절 표에는 심각도 칸이 없어 제목의 심각도 자리에 '우리 몫' 을 적었다. 행마다 정본 두 칸(할 일 · 상태)을 글자 그대로 옮기고 '무엇을 기다리나' 를 붙였다. 그 아래 '지금 판에서의 자리' 는 행이 든 것을 이 박스 리포와 맞댄 결과이고, '우리 쪽 맞물림' 은 이 요청의 우리 고침(HA- · HG- · HP- 행과 판단 C-7 로 이 세션이 맡은 AD- 코드 행)이 이 행 둘레에서 바꾸는 것이다.

## 할 일

행은 네 묶음으로 나눠 실었다.

| 묶음 | 행 | 풀어 주는 것 |
|---|---|---|
| 1. 지금 할 수 있는 것 | OB-01 · OB-02 · OB-03 · OB-59 · OB-93 · OB-95 · OB-71 · OB-33 · OB-99 · OB-85 · OB-96 · OB-97 · OB-100 · OB-101 · OB-102 · OB-60 · OB-61 · OB-62 | 막는 것이 없다. OB-01 ~ OB-03 은 날짜(11-10 무렵 알림 · 11-14 전)에 묶였다. OB-59 는 요청서가 '개발 SIF 대기' 로 적었지만 이 리포 기록으로는 그 SIF 가 올라갔다(그 행). |
| 2. 우리 고침이 cae00 에 닿은 뒤 | OB-91 · OB-98 · OB-63 · OB-64 · OB-65 · OB-68 | HA-26(1부는 에이전트 main `7ca3a2e`, 재시도 몫은 고치는 중) · HG-22 · HA-27 · HA-08(다시) · HA-33 — 모두 고치는 중이고 update-all 로 cae00 에 간다. |
| 3. 다른 플랫폼 답 뒤 | OB-94 · OB-103 · OB-34 · OB-25 · OB-87 · OB-89 | DocForge 0.3.1 배치 · SimFlow 와 RA 회신 · SmartTwinMCP 의 PA-16 · PA-19 · AIDataHub 데이터 단계(AD-05 · AD-06 dev 지우기, AD-04 측정 — 사용자 OK 뒤). OB-89 는 잰 값이 온 뒤 사람이 정한다. |
| 4. 사람 결정 | OB-92 · OB-26 · OB-04 | 지금 정할 수 있다. 정하면 포털 몫이 열린다 — OB-92 의 둘째 길이면 HP-54, 첫째 길이면 OB-34 · OB-25, OB-26 이 '둔다' 면 HP-53 의 ODB todo · key_tools, OB-04 는 박스 권한표 라벨. |

---

**묶음 1 — 지금 할 수 있는 것**

### OB-01 · OB-02 · OB-03 · 우리 몫 — stcx 챗 LLM 잡을 11-14 전에 다시 띄우기

- **할 일** — stcx 챗 LLM 잡을 11-14 전에 다시 띄운다. 키를 바꾸면 포털 `infra/.env` 의 `CHAT_LLM_API_KEY` 를 고치고, 다른 사용 서비스 담당에게 11-10 무렵 미리 알린다.
- **상태** — 90-OURS 그대로 — 11-14 전(TODO-20261029 T-01 · T-02).
- **무엇을 기다리나** — 없다. 날짜에 묶였다 — 11-10 무렵 다른 사용 서비스 담당에게 알리고, 11-14 전에 다시 띄운다.

#### 지금 판에서의 자리

- 절차는 이 리포에 있다. [`../../followups-1017/server-setup.md`](../../followups-1017/server-setup.md) 5절은 Slurm 잡 한도가 30일이라 2026-11-15 전후에 끝나고, 끝나도 챗은 GLM 으로 넘어간다고 적었다(`/health` 의 `chat_llm.fallback.count`). 명령은 `~/stcx-llm/llmctl.sh rolling`(또는 `start-all`)이다. [`../../chat-llm-stcx/server-setup.md`](../../chat-llm-stcx/server-setup.md) 9.5절(275행)은 그 rolling 이 잡 한도(30일)도 새로 잡아, 11-14 전에 하면 '11-14 전 rolling' 을 겸하고 다음 만료는 rolling 한 날 + 30일이라고 적었다. stcx 의 지금 잡 상태는 대조 못 함(이 세션은 stcx 에 닿지 않는다).
- 키 이름 `CHAT_LLM_API_KEY` 는 포털 `infra/.env.example:65` 에 있다. update-all 3.5c 가 `infra/.env` 의 `CHAT_LLM_*` 를 에이전트 서버 `.env` 로 옮기고(`infra/scripts/update-all.sh:1277` · 키는 `:1297` · `:1315`), 1g2 가 허브 앱 `.env` 로 옮긴다(`:761` · `:779`). 챗 서버가 키를 거절하면 update-all 이 'infra/.env 의 CHAT_LLM_API_KEY 를 본다(stcx 는 ~/stcx-llm/api_key 가 원본 · 값은 추적 파일에 적지 않는다)' 로 알린다(`:1342`). 줄 번호는 포털 `bf5cd94` 의 것이다 — `aec8e29` 뒤 update-all.sh 를 바꾼 커밋은 `5969dcb`(§7 어휘표 덧씌우기 지문) 하나다.
- '다른 사용 서비스' 가 어디인지는 TODO-20261029 T-01 · T-02 원문이 이 박스에 없어 대조 못 함.

#### 우리 쪽 맞물림

- 이번 요청의 우리 고침에 이 행과 맞물리는 것은 없다.

### OB-59 · 우리 몫 — StepForge 과제 찾기(프로젝트 이름 · 마케팅명) 새 SIF 받기 · OT-14 · OT-15 다시 보기

- **할 일** — StepForge 과제 찾기의 프로젝트 이름 · 마케팅명 길은 개발 main 에만 있다. 개발이 SIF 를 올렸다고 알리면 `infra/scripts/drive-drift.sh heax` 로 대조하고 update-all 뒤 OT-14 · OT-15 를 다시 본다.
- **상태** — 90-OURS 그대로 — 개발 SIF 대기(TODO-20261029 W-01 · 포털 `docs/request-1029` C-28).
- **무엇을 기다리나** — StepForge 개발의 'SIF 를 올렸다' 알림이다. 이 리포에는 그 알림이 이미 적혀 있다(아래). 남은 것은 cae00 에서 대조하고 받는 일이다.

#### 지금 판에서의 자리

- 이 박스의 StepForge main 은 `ff308d1`(D-648)이고, 프로젝트 이름 · 별칭(마케팅명) 길 D-647 `c65c92a`(10-29 21:09 KST)를 담는다(조상 확인). 코드 자리는 `core/sp_core.py:1315`(과제가 속한 프로젝트의 key · 이름 · 별칭 — `matched_by` `project:<프로젝트 key>`)와 `app/mcp_server.py:31304`(find_plm_task 설명)다.
- 포털 [`../../request-1029/server-setup.md`](../../request-1029/server-setup.md) 1절 표의 StepForge 줄(14행 — 커밋 `5ba7a33`, 10-30 12:59 KST)은 이 판의 SIF 를 Drive 에 올렸다고 적었다 — `dist-20261030-034158Z`, SIF 안 BUILD_INFO = `ff308d1`, '이 판 뒤의 update-all 에서 든다'. 요청서는 '개발 SIF 대기' 로 적었다. cae00 에서 그 글을 쓴 시각은 대조 못 함. Drive 의 실제 판도 이 시트에서 보지 않았다(drive-drift 를 돌리지 않았다).
- `infra/scripts/drive-drift.sh` 는 `heax` 를 받는다(머리 주석 — `portal | heax | koorm | mxwp | ste`, 종료코드 0 일치 · 1 드리프트 · 2 확인 불가). `aec8e29` 뒤 이 파일을 바꾼 커밋은 없다.
- 판단 C-28([`../../request-1029/context-notes.md`](../../request-1029/context-notes.md))은 StepForge 가 라이브 교체를 하지 않고 main 에만 넣었다고 적었다.

#### 우리 쪽 맞물림

- 이번 요청의 우리 고침에 이 행과 맞물리는 것은 없다.
- 7절은 OT-15 를 'SG-04 결정 뒤' 에도 다시 본다(DW-21 · OT-15). SG-04(다시)는 SignalForge `signalforge-c6` 에 보냈고 답을 기다린다([`../outbound.md`](../outbound.md) 1절). 같은 문항을 두 까닭으로 보는 셈이라, OB-59 로 볼 때의 결과를 따로 적어 둔다.
- 같은 SIF 길로 StepForge ST-12 판이 뒤따른다(StepForge 답 — '지금 다른 묶음(온톨로지 그래프 도구) 착지 중이라 ST-12 는 그 뒤 판').

### OB-93 · 우리 몫 — 도구 설명 예산 견주기

- **할 일** — 도구 설명 예산 비교(`CHAT_TOOL_SCHEMA_BUDGET` 40000 → 30000) — 같은 16문항 · 첫 호출 첫 토큰 · search_tools 왕복.
- **상태** — 남았다(10-30 재시험 보고서 6절).
- **무엇을 기다리나** — 막는 것은 없다. 다만 update-all 의 챗 도구 문구는 HP-55(고치는 중)가 고치기 전까지 이 견주기와 어긋난다(아래).

#### 지금 판에서의 자리

- 손잡이는 에이전트 서버 `.env` 의 `CHAT_TOOL_SCHEMA_BUDGET`(기본 0 — 에이전트 `7ca3a2e` `app.py:2115`, 기준 판 `:2021`)이다. 값이 있으면 그 값을, 없으면 챗 창의 45% 를 예산으로 쓴다(`app.py:2390`, 기준 판 `:2296` — 요청서 HP-55 가 든 줄). 손잡이는 W-2 `4514199` 로 들어왔고 기준 판 `969e723` 에 든다.
- 같은 견주기가 10-29 회차 사람 몫 O-3 으로 있다 — [`../../request-1029/server-setup.md`](../../request-1029/server-setup.md) 4절(에이전트 서버 `.env` 에 `CHAT_TOOL_SCHEMA_BUDGET=30000` → 도는 심의가 없을 때 `./start.sh -d` → 같은 16문항, `40000` 으로 한 번 더, 나은 값을 남기거나 줄을 지운다)과 [`../../request-1029/checklist.md`](../../request-1029/checklist.md) 84행(아직). 되돌리기는 같은 server-setup 5절 표다(줄을 지우고 에이전트 서버 재기동).
- 실제로 걸린 예산은 `/health` 의 `tool_cut.budget` 으로 본다(`app.py:7225` — 같은 칸이 `chat_llm.tool_cut` 에도 있다, `:6965`). 그 칸은 도구를 뺐을 때만 적힌다(`_fit_schema`, `app.py:2305` · `:2325-2327`). 요청서 HP-55 는 10-30 값을 tool_cut 1,379 → 209 · budget 88,473 으로 적었다.

#### 우리 쪽 맞물림

- HP-55(포털 — 고치는 중) — update-all §1 이 TOOL_MAX=0 인 박스에 '미설정 → 기본 200' 이라 적고 §7 이 '챗 창의 45% 안이면 전부 바인딩' 이라 적어, 이 견주기 때 틀린 말이 된다(요청서 HP-55 — 출처에 OB-93). 고친 판이 cae00 에 들기 전에는 update-all 로그의 챗 도구 줄 대신 `/health` 를 근거로 쓴다.
- 견주는 두 판 사이에 update-all 이 끼면(에이전트 판이 바뀌면) 견주기가 섞인다 — HA-26 · HA-27 · HA-28 이 같은 챗 길을 고치는 중이다.

### OB-95 · 우리 몫 — 생각 강도 high · medium 견주기

- **할 일** — 생각 강도 비교(`CHAT_LLM_REASONING_EFFORT` high · medium) — 디지털 워커 시험의 생각 글이 한 턴에 1,886 ~ 36,293자다.
- **상태** — 남았다.
- **무엇을 기다리나** — 없다.

#### 지금 판에서의 자리

- 손잡이는 에이전트 서버 `.env` 의 `CHAT_LLM_REASONING_EFFORT` 다. 기본은 `xhigh` 이고 생각을 켰을 때만 보낸다(`app.py:802`, 기준 판 `:726` · 설명 주석 `:494`). 주석이 드는 값은 xhigh · medium · low 이고 코드는 적은 값을 그대로 넘긴다 — 'high' 를 stcx 서버가 받는지는 대조 못 함.
- 걸린 값은 `/health` 의 `chat_llm.thinking` · `chat_llm.effort` 로 본다(`app.py:811-812` · `_chat_llm_health` `:6956`).
- 같은 견주기가 10-29 회차 사람 몫 O-4 로 있다([`../../request-1029/checklist.md`](../../request-1029/checklist.md) 49 · 85행 — W-6 · 결정 D-4, 아직). 10-29 계획 W-6 은 '질의 종류(조회 · 집계 · 분석)에 따라 강도를 바꾸는 길은 그 시험 결과를 보고 정한다' 고 적었다. 재기동은 도는 심의가 없을 때 `cd ~/Projects/HWAXAgentServer && ./start.sh -d` 다([`../../request-1029/server-setup.md`](../../request-1029/server-setup.md) 5절).

#### 우리 쪽 맞물림

- 이번 요청의 우리 고침에 생각 강도를 바꾸는 행은 없다. OB-71 도 생각 손잡이라, 같은 재기동 차례에 함께 재면 재기동이 준다.
- 견주는 두 판 사이에 update-all 이 끼지 않게 한다 — HA-27 · HA-28 이 같은 챗 길(자기검증 · 상태 조회 폴링)을 고치는 중이다.

### OB-71 · 우리 몫 — '예고만 하는' 호출을 생각 켬 · 끔으로 다시 재기

- **할 일** — 챗 모델의 '예고만 하는' 호출을 생각 켬 · 끔으로 다시 잰다. 잦으면 그때 에이전트 서버에 따로 청한다.
- **상태** — 90-OURS 그대로 — 두 QA 보고서에는 이 현상 기록이 없다(TODO-20261029 H-06).
- **무엇을 기다리나** — 없다.

#### 지금 판에서의 자리

- 손잡이는 에이전트 서버 `.env` 의 `CHAT_LLM_ENABLE_THINKING`(기본 1 — `app.py:801`, 기준 판 `:725` · 설명 주석 `:492`)이다. 0 이면 끈다.
- 현상은 에이전트 로그의 `[agent] 도구 미호출(예고만) — 강제 지시로 1회 재시도` 줄로 센다(`app.py:5439`, 기준 판 `:5337`).
- 재는 법은 10-27 답에 있다 — [`../../request-1027/answers.md`](../../request-1027/answers.md) 101-102행. 그 턴의 생각 글에 `<tool_call>` · `"arguments"` 가 있는지와, 같은 질의를 생각을 끈 채 돌린 결과를 함께 보면 생각 칸 안의 호출인지 갈린다. 여전히 잦으면 따로 청하라 했고, 그때 생각 칸의 호출을 읽는 길을 붙인다고 했다. TODO-20261029 H-06 원문은 이 박스에 없다.

#### 우리 쪽 맞물림

- 이번 요청의 우리 고침에 이 현상을 고치는 행은 없다.
- 강제 재시도 턴도 이 턴의 안내를 싣고 `_turn_msgs` 로 다시 부른다(`app.py:5442`). 그래서 OB-91 우회가 켜졌을 때와 걷은 뒤(HA-26 의 새 자리 — 사람 발화 머리)는 안내의 자리가 다르다. 잴 때 OB-91 우회가 켜져 있었는지 함께 적는다.

### OB-33 · 우리 몫 — hwax-batch 앱 설명 문안 고치기

- **할 일** — hwax-batch 앱 설명 문안을 고쳐 search_tools 의 앱 설명 적중을 바로잡는다. 10-30 `/tools-map` 에서 자주검증 허브 설명은 옛 문안이고 부서 허브 설명은 빈 칸이다.
- **상태** — 90-OURS 그대로 — 남았다.
- **무엇을 기다리나** — 없다.

#### 지금 판에서의 자리

- 게이트웨이는 앱 라벨 · 설명을 `_app_meta`(게이트웨이 `67d8d00` `gateway.py:2321`, 기준 판 `:2316`)에서 읽는다 — 허브 레지스트리 > 백엔드 설정 > 큐레이션 표 순이다. `search_tools` 는 앱 라벨과 설명을 질의 낱말과 맞대는 자리(`hay_app`, `:3268`, 기준 판 `:2932`)에 넣는다. 설명이 옛 문안이거나 비면 그 앱 도구의 앱 설명 적중이 어긋난다.
- 10-27 문서는 그 문안의 정본을 'hwax-batch CSV → 게이트웨이의 hwax-batch 블록, 손으로 고치지 않는다' 로 적었다([`../../request-1027/02-HWAXMcpGateway.md`](../../request-1027/02-HWAXMcpGateway.md) 96행). CSV · 블록 · 그 생성기는 이 박스 리포에 없다 — 포털 `backend` · `infra` 와 게이트웨이 리포에서 `hwax-batch` 는 시험 주석 한 줄(`backend/tests/test_access_control.py:45`)뿐이다. 문안의 지금 값은 대조 못 함.

#### 우리 쪽 맞물림

- 이번 요청의 우리 고침에 앱 설명을 바꾸는 행은 없다.
- OB-99(search_tools 순위 다시 재기)보다 먼저 하면 순위를 한 번만 잰다 — 설명이 순위에 든다(위).
- 허브 도구 설명 첫 줄의 설치별 tagline 은 Datahub 플랫폼 몫이다(10-27 DP-03 — 같은 96행).

### OB-99 · 우리 몫 — 챗이 던진 search_tools 질의 8건으로 cae00 순위 다시 재기

- **할 일** — 챗이 실제로 던진 search_tools 질의 8건으로 cae00 순위를 다시 잰다(포털 `docs/request-1029` context-notes C-14, 절차는 reflection-1028/02 2절 8번).
- **상태** — 남았다. 10-30 재시험의 근거 블록에는 search_tools 호출이 0회였다.
- **무엇을 기다리나** — 막는 것은 없다. OB-33 뒤에 재면 한 번으로 끝난다. 떠 있는 게이트웨이로 재는 창구(아래)는 다음 update-all 로 cae00 에 든다.

#### 지금 판에서의 자리

- 질의 여덟의 출처는 포털 [`../../request-1029/context-notes.md`](../../request-1029/context-notes.md) C-14 다 — 요청서에 이름이 나온 일곱(가상검증 · 관리 기준 · 철판 낙하 기준 · 낙하 해석 담당 · 규격 실패모드 · '가상검증 항목 …' · '관리 기준 개수')과 OT-07 의 영어 질문. 원문 여덟은 cae00 게이트웨이 질의 기록에 있고, '낙하 해석 담당' 은 코어 낱말이 없어 합성 카탈로그에서 정본 읽기 도구가 0개였다. 절차 원문(reflection-1028/02 2절 8번)은 이 박스에 없어 대조 못 함.
- 게이트웨이의 검색 고리 창구 — `/search-log` · `/search-review` · `/search-eval`(`1c7fcc1`)과 `tool_search_eval/run.py live`(`9e9a8c0`)는 기준 판 `44f4b8d` 뒤의 커밋이다. 받은 뒤 쓰는 법은 [`../../request-1029/server-setup.md`](../../request-1029/server-setup.md) 7.3절이다(화면의 '평가 돌리기' 또는 `run.py live --detail`).

#### 우리 쪽 맞물림

- HP-56(포털 — 고치는 중) — '전작' · '후속' 을 코어 발동 낱말(`rule_words`)에 더할지는 '심의 낱말을 가로채지 않는지 게이트웨이 검색 평가와 함께 본다'(요청서 HP-56). 같은 평가를 돌릴 때 함께 보면 한 번에 끝난다.
- OB-93 의 30000 판에서는 `search_tools` → `invoke_tool` 왕복이 늘 수 있다(10-29 server-setup 4절 O-3). 실사용 질의 기록은 그때 더 쌓인다.

### OB-85 · 우리 몫 — 챗 사용자 우회 안내 걷기

- **할 일** — 챗 사용자 우회 안내(질문에 허브 · 도구 이름을 쓰거나 첫 질문에서 앱을 핀하기)를 걷는다.
- **상태** — 90-OURS 그대로 — 걷을 조건이 찼다(10-30 OT-06 ~ 10 첫 도구 코어 5/5 · 정본 허브를 부른 시험 14/16).
- **무엇을 기다리나** — 없다(상태 칸 — 걷을 조건이 찼다).

#### 지금 판에서의 자리

- 그 안내가 어디에 실렸는지 이 리포에서 찾지 못했다 — 포털 업데이트 이력(`backend/config/changelog.yaml`)과 `docs` 에 '허브 · 도구 이름을 쓰거나 첫 질문에서 앱을 핀하라' 는 우회 글이 없다. 실린 자리는 대조 못 함.
- 조건의 근거(10-30 OT-06 ~ 10 첫 도구 코어 5/5 · 정본 허브를 부른 시험 14/16)는 cae00 QA 보고서(`qa-ontology/QA-CHAT-QWEN-20261030.md`)에 있고 이 박스에 없다.

#### 우리 쪽 맞물림

- 걷는 일을 막는 우리 고침은 없다.
- 안내가 권하던 '첫 질문에서 앱을 핀하기' 는 HA-26 의 400 이 걸리던 챗(앱 핀)이다. 지금은 OB-91 박스 우회로 돌고, OB-91 을 걷은 뒤의 7절 시험(전문가 · 앱 핀 · 붙인 문서 챗)이 그 길을 다시 본다.

### OB-96 · 우리 몫 — 허브 큰 응답 견본(사람 이름 지운 것)을 개발에 넘기기

- **할 일** — 허브 큰 응답(graph_neighbors · object_fields · object_references) 견본에서 사람 이름을 지워 개발 쪽에 넘긴다. 개발이 그 칸 모양에 맞춰 접기 규칙을 짓는다(포털 `docs/request-1029` checklist O-12 · context-notes C-22).
- **상태** — 남았다. 끝 절의 HA-34 · DP-01(다시)와 맞물린다.
- **무엇을 기다리나** — 막는 것은 없다. HA-34(고치는 중)가 cae00 에 들면 어느 응답이 실제로 접혔는지 로그로 보고 견본을 고를 수 있다.

#### 지금 판에서의 자리

- 견본을 받는 '개발' 은 에이전트 서버의 허브 접기다. 칸 이름으로 접는 셋(`_HUB_FOLD` — objects_summary · objects_list · object_get, 에이전트 `7ca3a2e` `app.py:1712`, 기준 판 `:1618`)과 견본 없이 일반 규칙으로 접는 셋(`_HUB_FOLD_LISTS` — graph_neighbors · object_fields · object_references, `:1717`, 기준 판 `:1623`)이 있다. 일반 규칙은 응답이 `_HUB_BIG_CHARS`(60,000자)를 넘을 때만 `_HUB_LIST_HEAD`(50)개를 넘는 배열을 앞 50개와 '전체 N개 중' 한 줄로 줄인다(`:1718-1719`). 본체는 `_fold_hub_result`(`:1750`, 기준 판 `:1656` — 요청서 HA-34 가 든 줄)다.
- 그 일반 규칙은 10-29 판단 C-22(에이전트 `d01a53b` — 기준 판에 든다, [`../../request-1029/context-notes.md`](../../request-1029/context-notes.md))이고 '견본이 오면 칸 모양에 맞춰 다시 본다' 고 적었다. 견본 줄은 [`../../request-1029/checklist.md`](../../request-1029/checklist.md) 88행 O-12 로 아직 열려 있다.

#### 우리 쪽 맞물림

- HA-34(에이전트 — 고치는 중) — 허브 응답을 접을 때 로그 한 줄(도구 이름 · 원문 자 수 · 접은 뒤 자 수)을 남기고 `/health` 에 접은 횟수를 싣는다. 지금 판에는 둘 다 없다(요청서 HA-34 근거).
- DP-01(다시)(Datahub 플랫폼 — 사람이 보낸다, [`../outbound.md`](../outbound.md) 2절) — 원천에서 응답을 줄이는 몫이다. 요청서가 이 행과 맞물린다고 적었다.
- 6절 첫 줄(TODO-20261029 R-07 — invoke_tool 로 부른 허브 응답을 접지 않는다)과 HA-27 ③(잘린 결과의 수치는 짚기만)도 큰 응답을 두고 맞물린다. 요청서는 10만 자 넘는 응답 11건이 그 길이었는지 가르지 못했다고 적었고, HA-34 의 출처에 이 6절 첫 줄(R-07)을 들었다.

### OB-97 · 우리 몫 — 'simflow 로 수지 도포 돌려줘' 시작 도구 보기 · arp_upload_open 응답 재기

- **할 일** — 포털 챗에서 'simflow 로 수지 도포 돌려줘' 가 패널 도구가 아니라 prepare_run 으로 시작하는지 한 번 본다. arp_upload_open 이 무엇을 돌려주는지 재어 개발 쪽에 넘긴다(에이전트 `app.py:2718-2719` — 실측이 오면 패널 전용 도구 집합에 더한다고 적혀 있다).
- **상태** — 남았다(reflection-1028/03 HA-05 확인).
- **무엇을 기다리나** — 없다.

#### 지금 판에서의 자리

- 요청서가 든 줄(에이전트 `969e723` `app.py:2718-2719`)은 패널 전용 도구 집합 위 주석의 끝 두 줄이다 — '… ARP 의 arp_upload_open 은 무엇을 돌려주는지 실측이 없어 넣지 않았다(같은 꼴로 확인되면 더한다).' 에이전트 `7ca3a2e` 에서는 `app.py:2812-2813` 이다. 집합 `_CHAT_PANEL_TOOLS`(`:2814-2815`, 기준 판 `:2720-2721`)와 그 둘레 주석은 기준 판과 글자가 같다 — arp_upload_open 은 아직 없다. 기준 판 뒤 app.py 를 바꾼 네 커밋(`ab87137` · `61c0ce9` · `d673846` · `7ca3a2e`)은 이 자리를 건드리지 않았다.
- 그 집합의 도구를 invoke_tool 로 부르면 '같은 일을 하는 일반 도구(예: 실행 준비 prepare_run · 업로드 도구)로 한다' 는 실패 글을 돌려준다(`app.py:1895-1897`, 기준 판 `:1802`).
- 볼 것은 10-27 '다시 볼 시험' 의 HA-05 확인과 같다 — '포털 챗에서 'simflow 로 수지 도포 돌려줘' 가 `open_*_panel` 이 아니라 `prepare_run` 으로 시작한다'([`../../request-1027/03-HWAXAgentServer.md`](../../request-1027/03-HWAXAgentServer.md) 147행). reflection-1028/03 원문은 이 박스에 없다.

#### 우리 쪽 맞물림

- 잰 값은 에이전트(우리 리포)로 간다 — 같은 꼴이면 `_CHAT_PANEL_TOOLS` 에 더한다(그 주석). 이번 요청의 고치는 중 행에는 없다.
- HP-42(다시)(포털 — 2단계, 손대지 않는다 — 판단 C-2) — 포털 챗이 패널을 그리게 되면 이 집합을 푼다(같은 주석). 에이전트 HA-20 이 먼저다.

### OB-100 · 우리 몫 — 15자리 접수 · 문서 번호가 IMEI 꼴로 가려지는지 보기

- **할 일** — 15자리 접수 · 문서 번호가 Luhn 검사를 우연히 통과해 가려지는지 본다(게이트웨이 `gateway.py:609` — IMEI 꼴은 어느 글에서든 가린다). HG-21 의 '.' 거르개로는 낱개 15자리 번호가 풀리지 않는다. 보이면 HG-21 에 덧붙인다.
- **상태** — 남았다.
- **무엇을 기다리나** — 막는 것은 없다. 보이면 HG-21 에 덧붙이므로, HG-21 을 고치는 지금 볼수록 같은 판에 실린다.

#### 지금 판에서의 자리

- 요청서가 든 줄(게이트웨이 `44f4b8d` `gateway.py:609`)은 '· IMEI 꼴(15자리, Luhn 검사 통과)은 어느 글에서든 가린다.' 주석이다. 게이트웨이 `67d8d00` 에서는 `:610` 이다. 꼴은 `_IMEI_RX`(`:625`, 기준 판 `:624` — 앞뒤 거르개 `(?<![\w-])` · `(?![\w-])`)이고 Luhn 검사는 `_luhn_ok`(`:629`)다. 기준 판 뒤 이 가림 절(기준 판 `:604-640`)은 한 줄 밀렸을 뿐 글자가 같다.

#### 우리 쪽 맞물림

- HG-21(게이트웨이 — 고치는 중) — 앞뒤 거르개에 '.' 을 넣고, 따옴표 없는 JSON 수는 IMEI 칸 이름일 때만 가린다. 요청서대로 낱개 15자리 번호는 이것으로 풀리지 않는다.
- HG-23(계산 앱은 IMEI 숫자 꼴 검사를 건너뛰는 보조 안)은 닫았다(판단 C-1 — 앱별로 건너뛰면 그 앱 결과의 자유 글에 든 진짜 단말 번호가 빠져나간다). C-1 은 이 행을 '사람이 cae00 에서 보고, 보이면 그때 HG-21 에 덧붙인다' 로 적었다.

### OB-101 · 우리 몫 — StepForge 코어 받기 cron 에 주 1회 `--full`

- **할 일** — StepForge 코어 받기 cron 에 주 1회 `--full` 을 더한다. 허브에서 빠진 과제가 find_plm_task 결과에 남지 않게 한다.
- **상태** — 남았다(TODO-20261029 T-17).
- **무엇을 기다리나** — 없다.

#### 지금 판에서의 자리

- StepForge `ff308d1` 의 받기 CLI 는 `scripts/plm_sync.py` 다. `--full` 은 since 없이 처음부터 다시 받고, 끝까지 받은 뒤 이번에 안 온 것을 비활성으로 둔다(`:7` 쓰는 법 · `:31` 인자). 머리 주석은 '주기 받기는 이 CLI 를 바깥 cron · systemd 타이머로 부른다(앱 안 주기는 없다 — 예: 매일 증분 · 주 1회 `--full`)' 다(`:16`).
- cae00 crontab 의 지금 줄은 대조 못 함. TODO-20261029 T-17 원문도 이 박스에 없다.

#### 우리 쪽 맞물림

- 이번 요청의 우리 고침에 이 행과 맞물리는 것은 없다.
- 같은 find_plm_task 를 OB-59 가 다시 본다. cron 을 고친 뒤 첫 `--full` 이 돈 다음에 OT-14 · OT-15 를 보면 빠진 과제가 남는지도 함께 보인다.

### OB-102 · 우리 몫 — DocForge 길 한 번(평문 pptx)

- **할 일** — DocForge 길 한 번 — 평문 pptx 를 'Report Archive — 정밀 변환' 과 '이 대화에서 분석' 으로 보낸다. DRM 파일은 PC 에서 만들지 않는다.
- **상태** — 남았다(TODO-20261029 H-05).
- **무엇을 기다리나** — 없다. 이 길은 cae00 의 DocForge 0.3.0 에도 있다(DW-10 이 본 도구 다섯 — convert · status · package · capabilities · cancel). HH-14 의 0.3.1 은 입력 상자 목록 도구라 이 길과 다르다.

#### 지금 판에서의 자리

- 포털의 두 길 — 'Report Archive 정밀 변환'(`backend/app/agent/routes.py:1736`, 기준 판 `:1668`)과 '이 대화에서 분석 — DocForge(DF-D19)'(`:1784`, 기준 판 `:1716`)다. 둘 다 DocForge 잡으로 맡기고 끝나면 패키지를 읽는다(`backend/app/agent/docforge_delivery.py:62` — purpose ra · chat). '이 대화에서 분석' 은 DocForge 가 맡지 않으면 AI 데이터 허브 변환기로 간다(`routes.py:1800` 로그 줄). 기준 판 뒤 routes.py 를 바꾼 커밋은 `aa5cb8a`(분석 루틴 중계) 하나이고 이 두 길은 줄만 밀렸다.
- 패키지의 리소스가 `docforge_ra_file_max_mb`(기본 25 — `backend/app/config.py:285`)를 넘으면 올리지 않고 알린다. cae00 `backend/.env` 의 값은 대조 못 함. TODO-20261029 H-05 원문은 이 박스에 없다.

#### 우리 쪽 맞물림

- AD-03(다시)(AIDataHub — 판단 C-7 로 이 세션이 고치는 중) — '이 대화에서 분석' 의 AIDataHub 변환이 NASCA DRM 파일을 `DRM_PROTECTED` 로 따로 알리게 한다. 이 행은 평문 pptx 라 닿지 않는다. DRM 파일 쪽은 OB-60 · OB-61 · OB-62 의 M-6 이 본다.
- HH-14 · DocForge 0.3.1 과 체크리스트 3c(`he-doc-docforge` 고침 셋 — 판단 C-8)는 챗 운영자의 길이라 이 포털 배달 길과 다르다.

### OB-60 · OB-61 · OB-62 · 우리 몫 — 챗 업로드 손 시험(목적지 · 큰 파일 · DRM, M-1 ~ M-6)

- **할 일** — 챗 업로드 손 시험 — 목적지 · 큰 파일 · DRM 파일(M-1 ~ M-6).
- **상태** — 90-OURS 그대로 — 10-29 · 10-30 QA 는 돌리지 않았다.
- **무엇을 기다리나** — 목적지 · 큰 파일은 없다. DRM 파일의 AIDataHub 문구(아래 AIDataHub 쪽 M-6)는 AD-03(다시)(고치는 중)이 cae00 에 든 뒤에 보면 바뀐 문구를 본다.

#### 지금 판에서의 자리

- M 번호의 원문(10-25 시험)은 이 박스에 없다. 이 리포의 10-27 '다시 볼 시험' 표가 옮긴 볼 것은 이렇다 — M-1(HP-32 뒤 — 목적지 목록에 세 개만 보이고 '정밀 변환' 은 없다) · M-3(HP-30 뒤 — 칩 H1 이 `<계정>-chat-<8자>-…` 가 아니다) · M-4(HP-29 뒤 — 'AI 데이터 허브' 로 보낸 뒤 `~/aidh-inbox` 에 사본이 남지 않는다) · M-5(HP-02 · HP-03 뒤 — 약 27 MB 평문 .pptx 를 RA 로 보내면 올리기 전에 막히고 사유가 보이며, 감사에 failed 줄이 남는다) · M-6(HP-14 뒤 — DRM .pptx 를 끌어 놓으면 PC 도우미 안내가 뜬다)([`../../request-1027/01-HWAXPortal.md`](../../request-1027/01-HWAXPortal.md) 159-163행). AIDataHub 쪽 M-3 · M-6 은 [`../../request-1027/10-AIDataHub.md`](../../request-1027/10-AIDataHub.md) 110-111행이다(M-6 — NASCA 로 암호화된 .pptx 를 넣고 오류 문구를 그대로 적는다, DRM 문서라는 별도 문구가 나와야 한다). M-2 는 이 박스 문서에서 찾지 못했다.
- **AIDataHub 쪽 M-6 의 바른 길(10-30 AD-03(다시) 고침 `643fb65` 뒤, AIDataHub 고친 세션이 바로잡음)** — NASCA .pptx · .docx · .pdf 는 브라우저가 PC 도우미 안내로 돌려 AIDataHub 에 닿지 않는다(그것은 포털 HP-14 의 M-6 이다). AIDataHub 문구를 포털에서 보려면 NASCA 로 암호화된 **.xlsx** 를 웹 챗에 놓고 'AI 데이터 허브로' 를 고르거나, `plat:docforge` 가 없는 계정으로 '이 대화에서 분석' 을 고른다(있으면 DocForge 가 먼저 맡는다). 기대 문구는 'convert_file: 사내 DRM(NASCA)으로 암호화된 문서라 서버가 열 수 없습니다. PC 에서 파일을 열어 필요한 내용을 복사해 챗에 붙여 넣으세요.' 다. 암호를 건 .xlsx(OLE)는 '다시 저장' 안내가 붙는다. pptx 문구를 AIDataHub 에서 직접 보려면 박스 inbox 의 파일로 게이트웨이 MCP `convert_file` 을 부르거나(code `drm_protected`) REST `POST /api/convert/` 를 쓴다(422 `DRM_PROTECTED`) — 떠 있는 서비스를 부르므로 사람이 정해서 한다.
- 포털 자리 — 목적지 표는 `backend/app/agent/upload.py`(SimFlow 목적지 `:88-98`), DRM 머리 판정은 `frontend/src/components/chat/docAttach.ts:34`(`DRM_HEAD` — HP-14), RA 보내기 한도는 `ra_import_max_mb` 25(`backend/app/config.py:288` — 주석 '실측 26.2 MB 통과 · 27.5 MB 거절이라 25 MB 로 둔다 — 정확한 값은 RA 회신(RP-16) 뒤')다. 셋 다 기준 판 `aec8e29` 뒤 바뀐 커밋이 없다.

#### 우리 쪽 맞물림

- AD-03(다시)(AIDataHub — 판단 C-7 로 이 세션이 고치는 중) — `convert_file` 앞에서 DRM 머리를 보고 `DRM_PROTECTED` 로 따로 알린다(포털 `docAttach.ts` 의 머리 표와 같게). AIDataHub 는 update-all 로 받는 플랫폼이다(요청서 머리).
- 이번 요청의 포털 고침(HP-51 ~ HP-56)에 업로드 길을 바꾸는 행은 없다.

---

**묶음 2 — 우리 고침이 cae00 에 닿은 뒤**

### OB-91 · 우리 몫 — 박스 우회 `CHAT_STABLE_PREFIX=0` 걷기

- **할 일** — 박스 우회 `CHAT_STABLE_PREFIX=0`(에이전트 서버 .env, 10-30 09:55 재기동) — HA-26 이 들어오면 줄을 지우고 재기동한다.
- **상태** — 들어가 있다(Knox 봇 연동 세션, 백업 `~/portal-backups/agent.env.stableprefix-*`).
- **무엇을 기다리나** — HA-26 이 cae00 에 드는 것. 1부(안내를 이번 사람 발화의 머리로)는 에이전트 main `7ca3a2e` 에 들어갔고, 재시도 몫(그래도 400 'System message' 면 재시도 때 안내를 첫 system 에 합친다)은 고치는 중이다([`../checklist.md`](../checklist.md) 1절). 둘 다 든 판이 update-all 로 cae00 에 든 뒤 줄을 지운다.

#### 지금 판에서의 자리

- 손잡이는 에이전트 `_STABLE_PREFIX`(`app.py:363`, 기준 판 `:309`)이고 `_turn_msgs`(`:384`, 기준 판 `:312` — 요청서 HA-26 이 든 `:312-317`)가 읽는다. `7ca3a2e` 의 `_turn_msgs` 는 안내를 `_with_turn_notes`(`:368`)로 사람 발화 앞머리에 싣고 시스템 메시지는 맨 앞 하나만 둔다. 손잡이가 0 이면 종전처럼 한 시스템 메시지에 잇는다(`:388`).
- 재시도 몫은 이 판에 없다 — HEAD 에서 'System message' 는 주석(`:361`)에만 나온다.
- 이 손잡이 값은 `/health` 에 실리지 않는다(`_STABLE_PREFIX` 를 읽는 곳은 `:388` 하나다). 걷었는지는 에이전트 서버 `.env` 줄과 재기동 시각, 그리고 7절 시험에 400 이 없는지로 본다.
- cae00 의 `.env` 줄과 백업 파일은 대조 못 함. 재기동은 도는 심의가 없을 때 `cd ~/Projects/HWAXAgentServer && ./start.sh -d` 다([`../../request-1029/server-setup.md`](../../request-1029/server-setup.md) 5절 — 같은 손잡이의 되돌리기 줄).
- update-all 로 함께 드는 에이전트 커밋은 기준 판 뒤 넷이다 — `ab87137`(코어 어휘표 박스 덧씌우기) · `61c0ce9`(분석 루틴 R2) · `d673846`(분석 루틴 R3) · `7ca3a2e`(HA-26 1부). 재시도 몫은 고치는 중이라 그 뒤에 붙는다.

#### 우리 쪽 맞물림

- HA-26(에이전트) — 위와 같다. 요청서는 앞부분 고정을 끈 대가가 크게 보이지 않았다고 적었다(끈 디지털 워커 시험의 캐시 적중 78.4% · 켠 OT 재시험 68.5%, 문항 꼴이 달라 바로 견줄 수 없다). 7절은 걷은 뒤 접두 캐시 적중을 다시 잰다.
- 걷은 뒤 400 이 다시 나면 줄을 되살리는 길(`CHAT_STABLE_PREFIX=0` → 재기동)이 그대로 있다(10-29 server-setup 5절).

### OB-98 · 우리 몫 — 외부 연결 앱 손 시험(needs_connect · whoami 신원 칸)

- **할 일** — 외부 연결 앱 손 시험 — 토큰이 없는 사용자에게 list_tool_apps 가 needs_connect 를 보이는지, 등록한 사용자의 whoami 신원 칸이 가림에 걸리지 않는지 본다(username 이 가림의 이름 칸에 든다 — 게이트웨이 `gateway.py:612-613`).
- **상태** — 남았다(02-HWAXMcpGateway 7절 M-16 · reflection-1028/02 HG-10).
- **무엇을 기다리나** — HG-22(게이트웨이 — 고치는 중)가 cae00 에 드는 것. HG-22 가 가림 칸과 꼴을 넓히므로, 신원 칸이 가림에 걸리는지는 그 판에서 봐야 뜻이 있다. needs_connect 쪽은 지금도 볼 수 있다(HG-10 이 기준 판에 든다).

#### 지금 판에서의 자리

- 요청서가 든 줄(게이트웨이 `44f4b8d` `gateway.py:612-613`)은 `_PII_KEYS` 의 머리와 '이름' 칸 목록이다 — 그 목록에 `username` · `user_name` 이 들어 있다. 게이트웨이 `67d8d00` 에서는 `:613-614` 이고 글자가 같다. '계정' 칸 목록은 `author_id` · `account_id` · `account_name` · `handle` · `user_handle` 이다(`:617`). 가림은 백엔드 도구 결과와 rest_call 에만 걸린다(주석 `:611`).
- needs_connect — `_needs_connect`(`:3428`, 기준 판 `:3074`)와 `list_tool_apps` 항목의 `status: needs_connect`(`:3509-3510`, 기준 판 `:3155-3156`)다. HG-10 커밋 `5fe6ea0` 이 기준 판에 든다. 이 둘레(기준 판 `:3074-3175`)는 기준 판과 글자가 같다.
- 볼 것은 10-27 '다시 볼 시험' M-16 과 같다 — '개인 토큰이 없는 사용자에게 `list_tool_apps` 가 needs_connect 를 보이고, 등록한 사용자의 dynaforgeprod_whoami 는 본인 이메일로 답한다'([`../../request-1027/02-HWAXMcpGateway.md`](../../request-1027/02-HWAXMcpGateway.md) 146행).

#### 우리 쪽 맞물림

- HG-22(게이트웨이 — 고치는 중) — 칸 이름에 owner · partOwner · submitter · user · email · assignee 꼴을 더하고, 메일 꼴 · 사내 계정 꼴(영문.영문숫자)과 사설 IP 꼴은 칸 이름과 상관없이 가리고, REST 다리 출력도 같은 가림을 거치게 한다(요청서 HG-22). 그대로 들어가면 whoami 의 본인 이메일 · 계정도 게이트웨이를 지나며 가려질 수 있다 — M-16 의 '본인 이메일로 답한다' 와 부딪힌다. 게이트웨이 가지가 whoami 를 어떻게 다루는지는 이 시트에서 보지 않았다(형제 워크트리를 열지 않았다). 가려지면 그 결과를 HG-22 에 알린다.

### OB-63 · 우리 몫 — 자기검증 손 시험(M-7 ~ M-10)

- **할 일** — 자기검증 손 시험 — 도구 없는 턴의 '(근거 없음 — 추정)' 재현 · 짧은 답 건너뛰기 · 긴 답 중지(M-7 ~ M-10).
- **상태** — 90-OURS 그대로 — 두 QA 는 도구 턴의 판정 · 지연만 쟀다.
- **무엇을 기다리나** — HA-27(에이전트 — 고치는 중)이 cae00 에 드는 것. 자기검증의 고침 규칙이 그 행으로 바뀌므로, 지금 판에서 보면 곧 바뀔 동작을 재게 된다.

#### 지금 판에서의 자리

- M 번호의 원문(10-25 피드백)은 이 박스에 없다. 10-27 '다시 볼 시험' 표가 옮긴 볼 것은 '도구 없는 턴의 '(근거 없음 — 추정)' 재현 여부(M-9), '검증 ✓ (N초)' 와 지연, 중지 동작(M-10)' 이다([`../../request-1027/03-HWAXAgentServer.md`](../../request-1027/03-HWAXAgentServer.md) 145행). M-7 · M-8 이 각각 무엇인지는 대조 못 함.
- 자기검증 스위치는 에이전트 서버 `.env` 의 `CHAT_SELF_CHECK`(기본 켬 — `app.py:4346`)다. 요청서 HA-27 이 든 자르기 줄 `_sc_fit(res, cap["res"])`(기준 판 `:4371`)은 `7ca3a2e` 에서 `:4473` 이다.
- 10-29 server-setup 6절 — '자기검증이 고칠 곳을 초안에서 못 찾으면 고치지 않고 초안을 그대로 낸다 — 답 아래 '검증하지 못해 초안을 그대로 보였습니다' 와 까닭이 뜬다(정상 동작).' 손 시험에서 이 줄을 결함으로 적지 않는다.

#### 우리 쪽 맞물림

- HA-27(에이전트 — 고치는 중) — ① 고침의 [새 글] 숫자는 이번 턴 도구 결과 원문(자르기 전)이나 그 합 · 차 · 비율일 때만 넣고, 아니면 '짚음(반영 안 함)' 으로 돌린다. ② 원문에 있는 숫자를 지우거나 '근거 없음' 으로 바꾸는 고침은 버린다. ③ 잘린 결과의 수치는 짚기만 하라고 검토자 지시에 밝힌다(요청서 HA-27). 그 판이 든 뒤 7절의 OT-04 · 08 · 09 · DW-05 와 같은 차례에 보면 자기검증을 한 번에 본다.

### OB-64 · OB-65 · 우리 몫 — 위키 버튼 숨김 · 위키 질문(M-11 ~ M-13)

- **할 일** — 위키 버튼 숨김(M-11 · M-12)과 위키 질문(M-13)을 웹 챗에서 본다. 끝 절의 HA-08(다시) · MW-01(다시)와 맞물린다.
- **상태** — 90-OURS 그대로 — 남았다.
- **무엇을 기다리나** — HA-08(다시)(에이전트 — 고치는 중)이 cae00 에 들고, MX 백서 MW-01(다시)(`bd2e79b` — 끝)이 update-all 로 드는 것. 버튼 숨김(M-11)은 지금도 볼 수 있다.

#### 지금 판에서의 자리

- M-11 · M-12 의 볼 것은 10-27 표에 있다 — '위키가 꺼져 있으면 버튼 · 심의 옵션이 보이지 않고 결정문에 오류 문구가 붙지 않는다'(HP-16 뒤, [`../../request-1027/01-HWAXPortal.md`](../../request-1027/01-HWAXPortal.md) 164행)와 '위키가 꺼져 있으면 심의가 위키 제출을 시도하지 않고, 결정문 끝에 오류 문구가 단마다 붙지 않는다'(M-12 · HA-08 뒤, [`../../request-1027/03-HWAXAgentServer.md`](../../request-1027/03-HWAXAgentServer.md) 146행). M-13 의 정의는 이 박스 문서에 없어 대조 못 함.
- 엔진의 꺼짐 글귀 `_WIKI_OFF_HINTS`(에이전트 `deliberation.py:3294` — 'wiki_disabled' · '위키는 아직 열리지 않았다')는 기준 판과 `7ca3a2e` 가 같다(기준 판 뒤 deliberation.py 를 바꾼 커밋이 없다).
- MX 백서 쪽 — 이 박스의 MXWhitePaper main `bd2e79b` 는 MW-01(`bd2e79b`)과 MW-12(`bb0a6a1`)를 담는다. 받은 답([`../outbound.md`](../outbound.md) 1절)은 MW-01 을 '`_wiki_switch` 가 켜짐 · 꺼짐 · 모름 셋 — http 모드는 모름이면 `wiki_*` 를 싣지 않고 10초마다 다시 봐 켜짐일 때 14개를 싣는다' 로 적었다. cae00 확인은 'mxwp-mcp tools/list 의 `wiki_*` 0개(위키 꺼짐), MCP 가 API 보다 먼저 떴으면 로그에 '위키 도구를 미루고 다시 본다' 한 줄이 있고 '미뤄 둔 위키 도구 N개를 실었다' 는 없어야 맞다' 다. 새 이미지 없이 update-all 의 git 받기로 가고, migrate.sh 가 이관 0059 · 0060 을 돈다.

#### 우리 쪽 맞물림

- HA-08(다시)(에이전트 — 고치는 중) — 꺼짐 글귀를 '열리지 않았' 까지 줄이거나 MX 백서 문구도 함께 받는다. outbound 1절에서 MX 백서에 'HA-08 이 '…열리지 않았습니다' 도 받는다 — 문구는 그대로 둬도 된다' 로 알렸고, MX 백서는 문구를 그대로 두었다.
- 둘이 cae00 에 든 뒤에는 위키가 꺼진 박스에 위키 도구가 실리지 않고(MW-01), 실려도 엔진이 꺼짐 글귀를 알아본다(HA-08). M-12 · M-13 은 그 판에서 본다.

### OB-68 · 우리 몫 — VOC 화면 손 시험(M-18) · get_voc_summary(제품 B)

- **할 일** — VOC 화면 손 시험(M-18)과 get_voc_summary(제품 B) 한 번.
- **상태** — 90-OURS 그대로 — 남았다(reflection-1028/08 '운영 확인 필요').
- **무엇을 기다리나** — get_voc_summary 한 번은 지금도 된다. VOC 화면(M-18)이 심의 전 'VOC 먼저 보기' 라면 HA-33(에이전트 — 고치는 중) 뒤에 본다 — 지금 판은 `search_voc` 의 새 반환 꼴을 펼치지 않아 실패 표시 없이 0건이 된다(요청서 HA-33).

#### 지금 판에서의 자리

- M-18 의 정의는 이 박스 문서에 없어 대조 못 함(10-25 피드백 원문 · reflection-1028/08 이 이 박스에 없다).
- 포털에서 VOC 를 보이는 화면은 심의 전 'VOC 먼저 보기' 다 — 포털 `backend/app/agent/routes.py:2423`(기준 판 `:2355`)이 에이전트로 넘기고, 에이전트가 `search_voc` 결과를 `_voc_row`(`app.py:6088`, 기준 판 `:5980`)로 줄 세운다.
- `get_voc_summary` 는 SignalForge `mcp-server/server.py:344` 에 있다(SignalForge `d2a794d` — 끝 절이 든 cae00 판과 같다).

#### 우리 쪽 맞물림

- HA-33(에이전트 — 고치는 중) — 결과가 객체이고 `results` 가 목록이면 펼치고, 펼친 뒤 0건이면 `notes` 를 싣고, 펼칠 것이 없는데 글이 비지 않았으면 `degraded` · `partial` 로 센다(요청서 HA-33). outbound 1절에서 SignalForge 에 `{results, notes}` 칸 이름을 지켜 달라고 했다.
- SG-04(다시) · SG-19(SignalForge `signalforge-c6` — 기다림) — 제품 해석이 한 프로젝트의 모델을 다른 프로젝트의 제품 코드로 푸는 것과 search_voc · resolve_product_keyword 의 느림이다. 제품 B 요약을 볼 때 다른 프로젝트의 VOC 가 섞였는지도 본다.

---

**묶음 3 — 다른 플랫폼 답 뒤**

### OB-94 · 우리 몫 — DocForge 입력 상자에 시험 파일 하나(DW-10 다시 보기)

- **할 일** — DocForge 입력 뿌리에 시험 파일 하나(DW-10 다시 보기).
- **상태** — 남았다.
- **무엇을 기다리나** — DocForge 0.3.1 배치. DocForge 는 HH-14 를 main 에서 끝냈고(`e72cbe5` · `ab5547e`), 배치(release · HEAXHub 등록 사본 · SIF · Drive)는 그 세션의 사용자 승인을 기다린다([`../outbound.md`](../outbound.md) 1절 답). 7절도 DW-10 을 'HH-14 뒤' 로 둔다.

#### 지금 판에서의 자리

- 이 박스의 DocForge main 은 `559ec87` 이고 HH-14 를 담는다 — 새 읽기 도구 `docforge_list_inputs`(`docforge/mcp_server.py:58`), 운영자 입력 상자 `<데이터>/inbox`(`docforge/config.py:166-167`). 상자 밖 경로는 '허용된 입력 뿌리 밖의 경로다 — 고를 수 있는 파일은 docforge_list_inputs 로 본다' 로 거절한다(`docforge/service.py:41-42`).
- cae00 release 는 0.3.0 `3ba0f6f` 다(받은 답 · 이 박스의 `origin/release` 참조도 `3ba0f6f`). 그 판의 `docforge/config.py` 에는 inbox 가 없다 — 입력 상자는 0.3.1 부터라, 시험 파일은 0.3.1 이 든 뒤에 둔다.
- DocForge 답 ⑤ — 새 박스 값은 없다. 0.3.1 을 받은 뒤 `/apps/doc_forge/api/v1/capabilities` 의 version 이 0.3.1 인지, 게이트웨이 `/refresh` 뒤 docforge_* 가 여섯인지 본다. 시험 파일은 그 상자(SIF `/data/inbox`, 호스트 `~/Projects/HEAXHub/var/app_data/doc_forge/inbox/`)에 평문 pptx 하나를 둔다. dev 상자는 비워 둔다(build-all 이 dev 앱 데이터를 cae00 에 심는다).

#### 우리 쪽 맞물림

- 체크리스트 3c(포털 — 0.3.1 이 cae00 게이트웨이에 실린 뒤) — `he-doc-docforge` 의 key_tools · can · pitfalls 고침 셋은 DocForge 가 Drive 판 이름을 알린 뒤에 커밋한다(판단 C-8 — 운영자 동기화는 게이트웨이에 없는 도구 이름을 만나면 멈춘다).
- HA-28(에이전트 — 고치는 중) — 상태 조회 도구(docforge_status 포함)는 코드가 기다렸다가 끝났거나 상한에 닿은 결과만 LLM 에 넘긴다. DocForge 답 ② — 도구 오류는 `{ok:false, error, status:403}` 처럼 `status` 가 숫자라, 숫자면 기다리기를 끝낸다.
- HA-29(에이전트 — 고치는 중) — docforge_convert 는 요청서가 든 잡 시작 도구다. 이번 턴 사람 발화가 변환을 분명히 시키지 않았으면 확인 카드로 멈춘다. DW-10 을 다시 볼 때는 변환을 말로 시킨다.

### OB-103 · 우리 몫 — SimFlow 목적지 첫 실주행

- **할 일** — SimFlow 목적지 첫 실주행 — 회신(입력 확장자 · 업로드 상한, RA 가져오기 상한)이 오면 포털 `backend/.env` 로 맞추고 한 번 보낸다.
- **상태** — 회신 대기(TODO-20261029 W-03 · W-04 · 01-HWAXPortal HP-15).
- **무엇을 기다리나** — SimFlow 회신(입력 확장자 · 업로드 상한 — 포털 설정 주석의 14-Partner-apps PA-12)과 RA 회신(가져오기 상한 — 같은 설정 주석의 RP-16)이다. 둘 다 사내 파트너 몫이고 이 세션이 닿지 않는다.

#### 지금 판에서의 자리

- 포털 설정 `backend/app/config.py:289-294` — `simflow_upload_exts` 기본 `x_t` · `simflow_upload_max_mb` 500 · `simflow_ready_wait_s` 120(DRM 문서를 SimFlow 가 drm_pending → ready 로 푸는 동안 기다리는 초)이다. 주석은 'SimFlow 쪽 확인(14-Partner-apps PA-12 — 확장자 목록 · 500 MB 와 600 MB 중 어느 것인지) 전' 이라 적었다. RA 가져오기 한도는 `ra_import_max_mb` 25(`:288`)다. 설정은 `backend/.env` 에서 읽는다(`:19-22`) — 이름은 `SIMFLOW_UPLOAD_EXTS` · `SIMFLOW_UPLOAD_MAX_MB` · `RA_IMPORT_MAX_MB` 꼴이다. 기준 판 `aec8e29` 뒤 바뀐 커밋은 없다.
- SimFlow 목적지는 게이트웨이에 SimFlow 의 `run_workflow` 가 있어야 고를 수 있다(`backend/app/agent/upload.py:88-98` — 'SimFlow 도구가 게이트웨이에 없으면(dev) 고를 수 없다'). cae00 `backend/.env` 의 지금 값은 대조 못 함. TODO-20261029 W-03 · W-04 원문은 이 박스에 없다.

#### 우리 쪽 맞물림

- 이번 요청의 우리 고침에 SimFlow 목적지를 바꾸는 행은 없다. 10-27 포털 HP-15(확장자 · 한도를 박스 설정으로)는 기준 판에 들어 있다.

### OB-34 · OB-25 · 우리 몫 — SmartTwinMCP 게이트웨이 등록 · 둘째 터널

- **할 일** — OB-92 의 잇기 길 — :5013 이 뜨면 게이트웨이 `provision.env` 로 SmartTwinMCP 를 등록하고(OB-34), 둘째 터널을 정한다(OB-25). 선행은 끝 절의 PA-16 · PA-19(다시)다.
- **상태** — 90-OURS 그대로 — stcx 답 대기(TODO-20261029 W-02).
- **무엇을 기다리나** — stcx 의 PA-16(:5013 운영 배포)과 PA-19(environment 덮어쓰기 잠금)이다. SmartTwinMCP `smarttwinmcp-4c` 에 다시 물었고('PA-19 코드 몫만이라도 먼저') 답을 기다린다([`../outbound.md`](../outbound.md) 1절). 끝 절 PA-16 · PA-19(다시)는 'OB-92 의 잇기 길은 둘이 끝난 뒤에 연다' 로 적었다. 그리고 OB-92 에서 이 길을 골라야 한다.

#### 지금 판에서의 자리

- 등록 길은 게이트웨이 `provision-config.sh` 다 — `provision.env` 에 `SMARTTWIN_MCP_URL` 이 있으면 smart-twin-mcp 백엔드를 만들고(`:47-49` · `:566-580`), 없으면 '켜려면 provision.env 에 SMARTTWIN_MCP_URL=<SmartTwinMCP 주소> …' 를 남기고 건너뛴다. 기준 판 `44f4b8d` 뒤 이 파일을 바꾼 커밋은 없다. 10-27 문서는 '`gateway_config.json` 손 편집 금지' 를 함께 적었다([`../../request-1027/02-HWAXMcpGateway.md`](../../request-1027/02-HWAXMcpGateway.md) 182행).
- PA-19 — 이 박스의 SmartTwinMCP(main `a98b9a7` · 체크아웃 가지 `feat/cuboid-scatter-drop` `97c0e0b`)에서 시나리오 덮어쓰기는 `tools/_shared/scenario_builder.py:79` 의 `deep_merge` 가 받는데, `environment` 를 거르지 않는다. 이 박스 판에는 잠금이 없다. stcx 에 떠 있는 판은 대조 못 함.
- '둘째 터널' — 이 리포에서는 [`../../request_1015.md`](../../request_1015.md) 3457행이 'smart-twin-cluster(:5012, slurm)를 두 번째 터널로 cae00 에 붙일지 정한다' 로 적었다. OB-25 가 같은 터널인지는 TODO-20261029 W-02 원문이 이 박스에 없어 대조 못 함.

#### 우리 쪽 맞물림

- HA-29(에이전트 — 고치는 중) — 잡 시작 도구와 운영자 정의의 `writes` 는 사람이 시키지 않았으면 확인 카드로 멈춘다. he-sim-smarttwin 의 writes 에 fullangle_drop_simulation · single_drop_simulation 이 있다(포털 `infra/personas/he-team.json:116`). 다만 요청서는 확인 카드가 아니라 PA-16 · PA-19 를 잇기의 선행으로 적었다.
- HP-51(포털 — 고치는 중) — 운영자 앱이 그 박스 게이트웨이에 없다는 줄을 update-all 미리보기 · 새 앱 점검에, 표지를 전문가 고르기 화면에 단다. 잇고 나면 he-sim-smarttwin 의 그 줄과 표지가 사라지는지로 잇기를 확인할 수 있다.

### OB-87 · 우리 몫 — 빈 전문가 · 데모 카드의 cae00 몫 지우기

- **할 일** — 빈 전문가 · 데모 카드의 cae00 몫을 지운다.
- **상태** — 90-OURS 그대로 — 끝 절 AD-05 · AD-06(다시) 뒤.
- **무엇을 기다리나** — AIDataHub AD-05 · AD-06(다시)의 dev 지우기다. 판단 C-7 로 AIDataHub 코드 행은 이 세션이 맡지만, 박스 데이터를 만지는 단계(AD-05 · AD-06 dev 지우기)는 사용자 OK 뒤다([`../checklist.md`](../checklist.md) 3b 의 '[-]'). 그 뒤 새 덤프가 cae00 에 병합된 다음이 이 행이다.

#### 지금 판에서의 자리

- 지울 것은 끝 절 AD-05 · AD-06(다시)대로 빈 전문가(dynaforge-report) · 데모 전문가(kooremapper-modelmeta)와 데모 카드 3장이다. 요청서는 10-30 포털 nginx 경유 `GET /ai-data-hub/api/agents/<키>` 가 둘 다 200 · 설명 0자 · data_types [] 였다고 적었다. 이 박스에서 그 행을 열지는 않았다.
- 순서는 10-27 AD-13 답에 있다([`../../request-1027/review-10-AIDataHub.md`](../../request-1027/review-10-AIDataHub.md) 142-155행) — dev 에서 레코드를 소프트 삭제 → dev 에서 전문가를 지운다 → 새 덤프 → cae00 에서 병합 → cae00 에서 전문가를 지운다(이 행) → 다음 병합 뒤 확인. cae00 에서만 지우면 전문가 행은 다음 병합 때 다시 들어온다. 같은 답은 '병합이 3 으로 끝나면 표식이 남지 않아 옛 덤프가 다시 들어간다(`update-all.sh:1162-1167`). 그러니 표식을 꼭 본다.' 고 적었다(줄은 10-27 판의 것).
- 같은 문서의 AD-05 '권하는 길' — 지우기 전에 그 2행에 묶인 레코드를 sim-drop-impact 로 다시 묶을지 먼저 정한다(그냥 지우면 그 레코드는 어느 좌석에도 걸리지 않는다). 10-27 표는 지우기 전에 OB-73(박스 화면 확인)을 두었는데([`../../request-1027/10-AIDataHub.md`](../../request-1027/10-AIDataHub.md) 98행), 10-30 5절 표에는 OB-73 이 없다 — 마쳤는지는 대조 못 함.
- AIDataHub HEAD 는 `ac42bc6` 이고 끝 절이 든 cae00 판과 같다.

#### 우리 쪽 맞물림

- AD-19 · AD-20(AIDataHub — 판단 C-7 로 이 세션이 고치는 중) — 낱말 겹침 항에서 요청 낱말을 빼고, 기록 · 표본 신호가 0 인 전문가가 겹침만으로 상위에 오르지 않게 한다. 빈 전문가가 추천 위로 오르는 일은 그 판에서 먼저 준다. 지우는 일은 이 행 그대로 남는다.
- HA-31(에이전트 — 고치는 중) — 자연어 질문을 '전문가 추천' 목록으로 가로채는 길을 좁힌다(DW-13).

### OB-89 · 우리 몫 — 지식카드 본문 검색 스위치를 켤지 정하기

- **할 일** — 지식카드 본문 검색 스위치를 켤지 정한다.
- **상태** — 90-OURS 그대로 — 끝 절 AD-04(다시)의 잰 값 대기.
- **무엇을 기다리나** — AD-04(다시)의 잰 값(dev DB 사본에서 `EXPLAIN ANALYZE`)이다. 판단 C-7 로 그 측정은 박스 데이터 단계라 사용자 OK 뒤다([`../checklist.md`](../checklist.md) 3b 의 '[-]'). 값이 오면 사람이 정한다.

#### 지금 판에서의 자리

- 스위치는 AIDataHub `api_server/src/api/config.py:42` 의 `aidh_records_q_body_search: bool = False`(env `AIDH_RECORDS_Q_BODY_SEARCH`)다. 설명 주석(`:37-41`)은 켜도 전문가 필터가 있을 때만 본문 절을 본다고 적었다. AIDataHub HEAD `ac42bc6` 은 끝 절이 든 cae00 판과 같다.
- 켤 때 env 를 둘 파일은 AIDataHub `deploy/apptainer/.env` 다(10-27 AD-15 답 — `start_api.sh` 의 `load_env` 가 읽는다, [`../../request-1027/review-10-AIDataHub.md`](../../request-1027/review-10-AIDataHub.md)). 재는 법도 같은 문서 AD-04 에 있다 — `EXPLAIN (ANALYZE, BUFFERS)` 를 건수 질의와 쪽 질의 둘 다에 걸고, 2글자 낱말과 3글자 이상 낱말로 나눠 잰다.
- 포털 검색칸 문구는 지금 '제목·요약에서 낱말로 찾기' 다(`frontend/src/components/chat/AgentDeepView.tsx:323` — 스위치가 꺼진 지금은 맞다).

#### 우리 쪽 맞물림

- HP-21(다시)(포털 — 조건부, 판단 C-3) — 켤 때 AIDataHub 응답에 스위치 상태를 싣게 하고 포털 문구를 그 칸에 맞춘다. 그 칸은 [`../outbound.md`](../outbound.md) 2절 1번이 AD-04(다시)에 덧붙여 청한 것이다.

---

**묶음 4 — 사람 결정**

### OB-92 · 우리 몫 — SmartTwin 운영자를 살리는 길 고르기

- **할 일** — SmartTwin 운영자 — cae00 게이트웨이에 SmartTwin MCP 를 잇거나, 이 박스의 he-sim-smarttwin 정의를 연결된 클러스터 앱으로 바꾼다.
- **상태** — 남았다.
- **무엇을 기다리나** — 사람의 선택이다. 첫째 길(cae00 게이트웨이에 SmartTwin MCP 를 잇기)은 PA-16 · PA-19(SmartTwinMCP — 기다림)가 끝난 뒤에 연다(끝 절 PA-16 · PA-19(다시) — '이 요청서 OB-92 에 이 선행 조건이 적혀 있지 않다'). 둘째 길(이 박스의 정의를 연결된 클러스터 앱으로 바꾸기)을 고르면 HP-54 가 산다.

#### 지금 판에서의 자리

- he-sim-smarttwin 은 포털 `infra/personas/he-team.json:94-127`(요청서 HP-54 가 든 줄 — 키 · 앱 · 선택 몫까지)이다. `apps` 는 smart-twin-mcp(`:95`)이고 선택 몫은 smart-twin-cluster 하나, `writes` 에 fullangle_drop_simulation · single_drop_simulation 등(`:116`), `confirm` 은 job_stop(`:117`)이다. 기준 판 `aec8e29` 뒤 이 파일을 바꾼 커밋은 없다. 이 파일에서 ste 도구(cluster_info · submit_job · set_job_sync · ste_cancel_job)를 묶는 운영자는 없다(grep 0건 — 요청서 HP-54 와 같다).
- 운영자 동기화는 기본 앱이 그 게이트웨이에 없으면 그 운영자를 건너뛴다(`infra/scripts/sync-he-personas.py:133-135` — '이 게이트웨이에 앱이 없다 … 붙어 있는 박스에서 돌리면 생긴다'). cae00 의 SmartTwin 운영자가 비는 것이 이 길이다.
- 첫째 길의 게이트웨이 쪽 자리와 이 박스 SmartTwinMCP 의 PA-19 자리는 OB-34 · OB-25 에 적었다.

#### 우리 쪽 맞물림

- HP-54(포털 — 조건부, 판단 C-4) — 둘째 길을 고르면 he-sim-smarttwin 에 ste 선택 몫(cluster_info 는 조회, submit_job · set_job_sync 는 writes, ste_cancel_job 은 confirm)을 두고, 기본 앱이 없어도 선택 앱만으로 운영자를 만드는 규칙을 둔다. 박스에서 손으로 고치면 다음 git 받기 · 병합에 사라지므로(요청서 HP-54) 정본에서 고친다.
- HP-51(포털 — 고치는 중) — 운영자 앱이 그 게이트웨이에 없다는 줄과 화면 표지다(DW-12 의 he-sim-smarttwin 이 그 예).
- 운영자 정의를 바꾸면 동기화가 AIDataHub 에 저장한다 — AD-21(저장 뒤 500 — 판단 C-7 로 이 세션이 고치는 중)과 포털 동기화의 '저장 여부를 다시 읽어 확인하고 이어 가기'([`../outbound.md`](../outbound.md) 2절 3번 — 고치는 중)가 그 길이다.
- HA-29(에이전트 — 고치는 중) — 어느 길이든 그 운영자의 writes 는 확인 카드를 탄다.

### OB-26 · 우리 몫 — ODB 허브 운영자(he-cad-odbhub)를 둘지 정하기

- **할 일** — ODB 허브 운영자(he-cad-odbhub)를 둘지 정한다. '둔다' 면 끝 절 HP-53 의 ODB 몫이 산다.
- **상태** — 90-OURS 그대로 — 사용자 결정(10-30 DW-02 는 이 운영자로 PASS).
- **무엇을 기다리나** — 사람 결정이다. 막는 것은 없다.

#### 지금 판에서의 자리

- he-cad-odbhub 는 포털 `infra/personas/he-team.json:61` 에서 시작한다(앱 `odb-hub` — `:62`). `todo`('cae00 에서 실제 도구를 보고 작업 순서·함정·key_tools 를 보강한다.') · `key_tools` · `writes` · `confirm` 이 `:84-87` 이고 뒤 셋은 빈칸이다(요청서 HP-53 근거와 같다). 기준 판 뒤 바뀐 커밋은 없다. 이 운영자의 개념 줄은 '사내망 전용 서비스라 cae00 게이트웨이에서만 도구가 붙는다' 라(`:78`), dev 에서는 그 도구를 볼 수 없다.

#### 우리 쪽 맞물림

- HP-53(포털 — 고치는 중) — 판단 C-5 대로 ODB 쪽 목록(run_checklist · run_analysis · run_compare · run_curvature · create_modified_odb · import_modified_odb)은 운영자를 두든 말든 지금 `writes` · `confirm` 에 채우고, `todo` · `key_tools` 는 이 행이 '둔다' 일 때 쓴다(요청서 HP-53 — 'ODB 몫은 OB-26 이 '둔다' 일 때다').
- HA-29(에이전트 — 고치는 중) — 그 코드 관문이 이 목록을 읽는다.
- 정의를 바꾸면 동기화가 AIDataHub 에 저장한다 — AD-21 과 포털 동기화 이어 가기(OB-92 와 같다).

### OB-04 · 우리 몫 — 운영 앱 둘의 '(시험)' 라벨 바로잡기

- **할 일** — 운영 앱 둘(dynaforge-prod · stepforge-prod)의 '(시험)' 라벨을 박스 권한표에서 바로잡는다. 목록 · 검색 숨김은 들어왔지만 list_tool_apps 는 두 앱을 그 라벨로 보인다(게이트웨이 `gateway.py:3101`).
- **상태** — 90-OURS 그대로 — 사용자 확인(포털 checklist O-5).
- **무엇을 기다리나** — 사용자 확인이다(포털 [`../../request-1029/checklist.md`](../../request-1029/checklist.md) 86행 O-5 — 아직).

#### 지금 판에서의 자리

- 요청서가 든 줄(게이트웨이 `44f4b8d` `gateway.py:3101`)은 `_list_tool_apps`(`:3094`) 안의 `for t in exposed_tools:` 다. 게이트웨이 `67d8d00` 에서는 `:3455`(함수 `:3448`)이고 둘레는 글자가 같다. 이 함수는 노출 도구 전부를 앱별로 묶고 사용자가 끈 앱만 따로 뺀다. 시험 사본 숨김(`_visible_tools`, `:5055-5063`, 기준 판 `:4026`)은 tools/list · search_tools 쪽이라 list_tool_apps 에는 걸리지 않는다.
- 라벨은 `_app_meta`(`:2321`)가 허브 레지스트리 > 백엔드 설정 > 큐레이션 표 순으로 읽는다. 10-27 HG-19 는 '(시험)' 라벨이 박스 권한표(`backend/config` 의 `*.local.yaml`, 62-89행 중 label 66 · 78행 · 안내 문구 85행)에서 온다고 적었다([`../../request-1027/02-HWAXMcpGateway.md`](../../request-1027/02-HWAXMcpGateway.md) 86행). cae00 박스 파일이라 대조 못 함 — 이 박스 리포에는 `access.local.yaml` 이 없다.
- 게이트웨이는 라벨의 '(시험)' 을 사본 표지로도 읽는다(`_COPY_LABEL`, `:2944`, 기준 판 `:2728`).
- 포털 `backend/config/core_vocab.json:36-37` 은 두 앱을 역할 `staging`(라벨 'StepForge 시험 사본' · 'DynaForge 시험 사본')으로 둔다. 목록 · 검색 숨김의 근거다(10-29 R-6 · 결정 D-2, 게이트웨이 `ab3fcff` — 기준 판에 든다).

#### 우리 쪽 맞물림

- 이번 요청의 우리 고침에 이 라벨을 바꾸는 행은 없다(10-27 결정 D-1 — 박스 권한표 일이라 코드는 바꾸지 않는다).
- 함께 확인할 것 하나 — 요청서는 두 앱을 '운영 앱' 이라 부르고, 10-27 HG-19 의 주의('두 앱은 10-23 가동 · 10-27 코어 연결로 실제 운영 데이터를 가진 앱이 됐다. '(시험)' 라벨이 낡았을 수 있다.')도 같은 쪽이다. 10-29 결정(D-2 · R-6)은 같은 둘을 '시험 사본' 으로 숨겼다. 라벨을 바로잡을 때 어휘표의 역할 칸도 같은 뜻인지 함께 정한다.

## 끝나면

이 시트의 일은 cae00 에서 사람이 한다. 커밋 · SIF · Drive 판은 없다 — 박스 파일(`.env` · crontab · `provision.env` · 박스 권한표)은 추적하지 않는다. 끝낸 것은 포털 세션 `hwaxportal-a5` 에 알리고, 포털 세션은 그것을 `server-setup.md`(합친 뒤 [`../checklist.md`](../checklist.md) 4절에서 쓴다)와 [`../outbound.md`](../outbound.md) 에 옮긴다. 알릴 때 키 · 토큰 값과 내부 주소는 적지 않는다.

1. **박스 손질을 마친 것** — 무엇을 언제 했나. OB-91(줄을 지운 시각 · 에이전트 재기동 시각), OB-01 ~ OB-03(rolling 한 날 · 키를 바꿨는지만), OB-101(주 1회 `--full` 줄을 넣었는지), OB-85(걷은 날 · 걷은 자리), OB-33(고친 앱 설명이 `/tools-map` 에 보이는지), OB-34 · OB-25(등록 뒤 smart-twin-mcp 가 게이트웨이에 서는지), OB-87(AD-13 순서의 몇째 걸음까지 했나), OB-59(drive-drift 결과 · update-all 뒤 StepForge 판), OB-94(0.3.1 확인 두 줄 · 둔 파일 이름).
2. **잰 값** — OB-93(30000 · 40000 각각의 16문항 결과 · 첫 호출 첫 토큰 · search_tools 왕복 · `/health` tool_cut), OB-95(강도별 생각 글 길이 · 지연), OB-71(예고만 로그 횟수 — 생각 켬 · 끔, 그때 OB-91 우회가 켜져 있었는지), OB-99(질의 여덟의 순위).
3. **개발에 넘길 것** — OB-96(사람 이름을 지운 견본 → 에이전트 허브 접기), OB-97(arp_upload_open 이 돌려준 꼴 → 에이전트 `_CHAT_PANEL_TOOLS`), OB-100(가려진 번호가 보였으면 그 꼴 → HG-21), OB-98(신원 칸이 가려졌으면 → HG-22).
4. **결정** — OB-92(어느 길), OB-26(둔다 · 두지 않는다), OB-04(라벨 · 역할 칸), OB-89(켬 · 끔). 포털 세션이 그에 맞춰 HP-54 · HP-53 의 ODB 몫 · HP-21(다시)을 연다.
5. **손 시험 결과** — OB-60 ~ OB-62 · OB-63 · OB-64 · OB-65 · OB-68 · OB-102 — M 번호마다 통과 · 실패와 화면에 뜬 오류 문구 그대로.

### 7절에서 이 시트에 닿는 다시 볼 시험(정본 그대로)

| 시험 | 언제 | 볼 것 |
|---|---|---|
| 전문가 · 앱 핀 · 붙인 문서 챗 | HA-26 뒤, 우회(OB-91)를 걷은 상태로 | 400 이 없다. 접두 캐시 적중을 다시 잰다. |
| DW-10 | HH-14 뒤 | 입력 파일을 골라 변환까지 한다. |

첫 줄은 OB-91 을 걷은 뒤, 둘째 줄은 OB-94 의 시험 파일을 둔 뒤다.

### 나머지 7절 시험(정본 그대로)

그 플랫폼 시트의 몫이지만, 두 QA 처럼 cae00 에서 사람이 SSO 로 로그인한 웹 화면으로 돌린다.

| 시험 | 언제 | 볼 것 |
|---|---|---|
| OT-04 · 08 · 09 · DW-05 | HA-27 뒤 | 초안의 맞는 값이 그대로 나간다. |
| DW-02 후속 · DW-03(후속 포함) | HA-28 · HA-29 뒤 | 상태 조회가 LLM 왕복 없이 기다린다. 잡은 확인 뒤에만 건다. |
| DW-07 · DW-03 · 06 · 12 · 22 | HG-21 · HG-22 뒤 | 숫자가 그대로 나오고, 사람 이름 · 메일 · 사설 IP 가 가려진다. |
| DW-13 | HA-31 뒤 | 질문이 챗 에이전트로 가고 '기록 수' 를 답한다. |
| DW-21 · OT-15 | SG-04 결정 뒤 | 프로젝트 A 의 VOC 에 프로젝트 B 가 섞이지 않는다. |

### 받은 답이 만든 cae00 사람 몫(5절 행이 아니다)

[`../outbound.md`](../outbound.md) 1절 '답' 칸에서 옮겼다. 정본 글은 그 칸이다.

- **DocForge** — 0.3.1 을 받은 뒤 확인 두 줄과 시험 파일(OB-94 에 적었다).
- **MX 백서** — 새 이미지 없이 update-all 의 git 받기로 가고 migrate.sh 가 이관 0059 · 0060 을 돈다. 확인은 OB-64 · OB-65 에 적었다.
- **SmartTwinExplorer** — PA-20 끝(`4f5e0e0`). 'Drive `ApptainerImages:SmartTwinExplorer/staging` 번들(4f5e0e0)을 `infra/scripts/deploy-ste.sh` 로 반영(MCP `ste-mcp.service` 도 같이 재기동), 그 뒤 DW-12 다시 보기'.
