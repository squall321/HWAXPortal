# 12 Datahub 플랫폼(허브 셋 — hwax-batch) — 10-30 요청에서 할 일

| 항목 | 내용 |
|---|---|
| 받는 곳 | 사내 다른 팀(Datahub 플랫폼 담당 — 허브 셋 자주검증 · FailureTrace · 부서 허브). 이 박스에서 닿는 세션이 없어 사람이 전한다. |
| 어떻게 갔나 | 사람이 보낼 차례다. cae00 의 Datahub 요청서(12-Datahub-platform)와 한 묶음으로 보낸다([`../outbound.md`](../outbound.md) 2절 'Datahub 플랫폼(허브 셋 — hwax-batch) · ARP · 사내 파트너'). 18:06 KST 대조 때 그 절에 보냈다는 기록도 답도 없다. |
| 요청서 정본 | [`../../request_261030.md`](../../request_261030.md) 4절 '박스 밖 플랫폼'(DP-14 · DP-15)과 끝 절 '이전 회차에서 남은 챗 · 디지털 워커 요청 (10-30 대조)' 의 'Datahub 플랫폼(허브 셋 — hwax-batch)' 표(DP-01(다시) · DP-02(다시) · DP-04 · DP-05(다시) · DP-07(다시) · DP-08(다시) · DP-06(다시) · DP-09(다시)). 행 아홉(번호 열) — 높음 2 · 중간 3 · 낮음 4. 7절 '다시 볼 시험' 에는 이 플랫폼 줄이 없다. |
| 허브 셋 | 게이트웨이 백엔드 `rootdesigndatahub`(자주검증 Datahub — 코어 정본) · `failuretrace`(FailureTrace) · `caegroupdatahub`(요청서의 '부서 허브')이고, cae00 박스 권한표의 `hwax-batch` 블록이 한 플랫폼으로 묶는다(포털 `backend/config/core_vocab.json:4-8` · `:33-35`, `backend/tests/test_access_control.py:45-47`). 셋 다 같은 틀(StandardPlatform)로 띄운 설치다 — 그 틀의 운영 안내(아래 옛 사본의 `deploy/README_OPERATOR.md:737`)가 「자주검증 Datahub」 · 「Failure Trace」 를 같은 번들의 인스턴스로 든다. |
| cae00 기준 판 | 판 sha 가 없다. Datahub 플랫폼은 update-all 로 받지 않는다(정본 머리 3줄 'Datahub 플랫폼은 아니오'). 기준은 cae00 문서 12-Datahub-platform(10-27 플랫폼별 요청서 — 포털 `docs/request-1027/02-HWAXMcpGateway.md` · `03-HWAXAgentServer.md` 가 그 이름으로 가리킨다)과 10-29 · 10-30 cae00 QA 실측이다. 행이 인용한 HWAX 줄의 기준은 에이전트 서버 `969e723` · 게이트웨이 `44f4b8d` · 포털 `aec8e29` 다. |
| 이 박스(dev)에서 대조한 판 | Datahub 플랫폼 배포판 — 이 박스에 리포가 없어 대조 못 함. 근거 문서(QA-CHAT-QWEN-20261029 · 20261030, QA-DIGITAL-WORKER-20261030, 12-Datahub-platform, 90-OURS)도 cae00 문서라 이 박스에 없다. 대신 StepForge · KooRemapper 가 서브모듈(`external/StandardPlatform`)로 고정한 옛 사본 StandardPlatform `f7485c0`(0.4.52, 2026-10-13 — `@tool()` 76개)으로 글의 꼴만 견줬다. 배포판은 더 새것이다(10-27 `/tools-map` 에서 허브마다 도구 103개 — 포털 `docs/request-1027/02-HWAXMcpGateway.md` HG-05). HWAX 쪽은 에이전트 서버 main `7ca3a2e` · 게이트웨이 master `67d8d00` · 포털 main `bf5cd94` 와 대조했다 — 2026-10-30 18:06 KST. |

옛 사본(0.4.52)으로 본 것은 배포판의 꼴을 짐작하는 근거일 뿐이다. 배포판에서 같은 줄 · 같은 동작이라고 할 수 없어서, 행마다 '배포판 — 대조 못 함' 과 따로 적었다. 옛 사본의 경로는 그 리포 뿌리 기준이다.

## 할 일

행 차례는 정본 표의 차례다(4절 두 행, 끝 절 일곱 행 — 끝 절 표는 심각도 차례라 DP-06 이 DP-07 · DP-08 뒤에 있다). 각 행의 대상 · 무엇이 · 근거 · 할 일 · 출처는 정본 칸을 글자 그대로 옮겼다. 정본은 이 플랫폼 행에 '다시 볼 시험' 칸을 주지 않았다(맨 끝 '끝나면' 참조).

### DP-14 · 낮음 — 조건 주소 오류에 바른 주소 예가 없다

- **대상**: Datahub 플랫폼(자주검증 · FailureTrace · 부서 허브)
- **무엇이**: 조건 주소 오류(APP-OBJECTS-0073)에 바른 주소 예가 없다.
- **근거**: OT-09 · 11 에서 4번.
- **할 일**: 오류 문구에 그 타입에서 쓸 수 있는 주소 예(`in.applies_to_part` · `out.occurs_in_part` 꼴)를 싣는다. 응답 크기(DP-01)는 그대로다 — 10만 자 넘는 응답 11건(OT 재시험).

**지금 판에서의 자리**

- 배포판 — 이 박스에 리포가 없어 대조 못 함. 근거 OT-09 · 11 도 cae00 QA 문서라 이 박스에 없다.
- 옛 사본(0.4.52)으로 본 것 — 번호는 `code("OBJECTS", 73)` 이 짓는다(머리 `APP` 는 `backend/app/branding.py:48` 의 `ERROR_PREFIX`, 꼴은 `backend/app/shared/errors.py:32-38`). 내는 자리는 `backend/app/modules/objects/conditions.py` 다섯 곳이다 — `:432` · `:436` 은 '없는 칸입니다: <칸>', `:438` · `:465` 는 파일 칸, `:452` 는 주소 해석 실패 글을 그대로 옮긴다. 주소 해석 실패 글(`backend/app/modules/objects/paths.py:381-457`, 머리 '이어진 칸을 쓸 수 없습니다' — `:182-185`)도 꼴만 말하거나(`:409` '주소는 ref.<칸> · out.<관계> · in.<관계> 로 시작합니다.') 이어지지 않는다고만 말한다. 그 타입에서 쓸 수 있는 주소를 늘어놓는 글은 없다.
- 늘어놓을 재료는 옛 사본에 이미 있다 — 한 걸음에 닿는 걸음 목록(`Resolver.hops`, `paths.py:235`)과 화면 고르개의 목록(`Resolver.options`, `:557`), MCP `object_fields`(`mcp_server/server.py:1635-1651`). objects_list 설명도 '주소는 `object_fields` 가 준다 — 추측하지 않는다'(`server.py:1229-1230`)라고 적는다.
- 같은 일이 10-29 요청서 5.5 에 먼저 올랐다('objects_summary 조건 주소를 모델이 틀린다' · APP-OBJECTS-0073 3회(OT-11) — [`../../request_261029.md`](../../request_261029.md) 5.5).
- HWAX 에이전트의 임시 안내(대조함) — `_chat_result_note`(`969e723` `app.py:1719-1735` → 지금 `7ca3a2e` `app.py:1813-1829`)는 같은 턴에 objects_summary · objects_list 를 네 번째(`_TOOL_REPEAT_NOTE_AT = 4`, 지금 `:1414`)부터 부를 때만 결과 꼬리에 '조건 주소(in.applies_to_part 꼴)를 모르면 object_fields 로 확인하고 부른다' 를 붙인다. 첫 세 번은 모델이 허브의 오류 글만 본다.

**우리 쪽 맞물림**

- 요청서가 이 행에 잇는 우리 쪽 고침은 없다. 같은 허브 도구에 모델이 틀린 인자를 넘기는 이웃 일 둘을 우리 쪽에서 고치는 중이다.
  - HA-32(고치는 중) — 없는 코어 타입 이름을 지어내 부르는 일(DW-22 — object_resolve(type_slug='management_standard'), 실제는 criterion). 코어 규칙 글에 어휘표 낱말 → 타입 이름 대응을 한 줄로 싣는다(`core_vocab.json` 에 칸을 더한다).
  - HA-30(고치는 중) — 허브를 건널 때 앞 허브의 id 를 그대로 넘기는 일(OT-07 — failuretrace_graph_neighbors 에 자주검증 id 를 넘겨 APP-GRAPH-0001). 설계 초안([`../design-ha30.md`](../design-ha30.md))은 부르기 전에 막고 '이 id 는 ○○ 허브 것 — key 로 다시 풀어라' 를 돌려주는 쪽이다.
- HA-30 설계 초안의 덧붙임 권고(9.2 Q9) — 개인 Claude(게이트웨이 MCP 직접 연결)에는 에이전트 관문이 없으니, 허브의 '객체를 찾을 수 없습니다'(GRAPH-0001 — 옛 사본 `backend/app/modules/graph/routes.py:429`)에도 '다른 설치의 id 일 수 있다 — key 로 object_resolve' 한 줄을 DP-14 와 같은 묶음으로 청하자고 적었다. 정본 요청서의 행이 아니고 [`../outbound.md`](../outbound.md) 에도 아직 없다. 덧붙일지는 사람이 보낼 때 정한다.
- OT-09 는 7절 첫 줄(HA-27 뒤 다시 볼 시험)에도 든다. 그때 APP-OBJECTS-0073 이 몇 번 나는지도 함께 세면 이 행의 바탕값이 된다.

### DP-15 · 낮음 — 부서 허브의 해석 기록 적재 계획(질문)

- **대상**: 부서 허브(Datahub)
- **무엇이**: 해석 기록이 비었다(같은 key 고장모드에 이어진 기록 0건).
- **근거**: 10-29 EX-01 — 해석 기록 타입 자체가 비었다.
- **할 일**: 해석 기록 적재 계획을 묻는다(질문).

**지금 판에서의 자리**

- 배포판 · 데이터 — 이 박스에 리포도 데이터도 없어 대조 못 함. 고칠 코드가 아니라 답할 질문이다.
- 10-29 요청서 5.5 에 같은 실측이 있다 — 해석 기록 타입이 비어 이어진 기록 0건(`log_counts` 빈 배열), 관계 자체는 정본과 같다(대표 메커니즘 8개 — 10-29 직접 대조). 그 허브의 '코어 사본 + CAE 해석 결과 아카이브' 라는 설명에 맞춰 물은 것이다([`../../request_261029.md`](../../request_261029.md) 5.5).
- 옛 사본(0.4.52)의 graph_neighbors 는 나를 가리키는 기록(`usage="log"`)을 이웃에 싣지 않고 `log_counts` 로 센다(`mcp_server/server.py:1778-1780`, `backend/app/modules/graph/routes.py:402-404`). 10-29 실측이 본 빈 배열이 이 칸이다.

**우리 쪽 맞물림**

- 요청서가 이 행에 잇는 우리 쪽 고침은 없다. 질문 행이라 답(적재 계획 · 일정)을 받아 [`../outbound.md`](../outbound.md) 에 옮긴다.

### DP-01(다시) · 높음 — 허브 응답 크기를 원천에서 줄인다

- **무엇이**: (높음) 허브 응답이 여전히 커서 챗 문맥과 자기검증 입력을 크게 차지한다. 이 요청서에는 DP-14 의 곁말로만 있다.
- **근거**: QA-CHAT-QWEN-20261030 4절 — 10만 자 넘는 응답 11건이다. 에이전트 쪽 접기는 들어왔다(`969e723` `app.py:1618-1625` · `:1909-1917`). 원천 몫은 그대로다.
- **할 일**: objects_list 의 ref_labels 를 쪽에 한 번만 싣고, objects_summary 의 group_options 를 기본에서 빼고, object_get 의 related 를 접는다.
- **출처**: 12-Datahub-platform DP-01 · QA-CHAT-QWEN-20261030 4절 · 이 요청서 DP-14

**지금 판에서의 자리**

- 근거의 HWAX 줄(대조함) — `969e723` `app.py:1618-1625` 는 에이전트 접기 표다. `_HUB_FOLD`(`:1618-1619`)가 objects_summary 의 group_options 와 objects_list 의 ref_labels · properties_schema 를 걷고 object_get 의 related 를 관계별 수와 앞 다섯(바로 윗줄 `_HUB_RELATED_HEAD = 5`)으로 접게 한다. `_HUB_FOLD_LISTS` · `_HUB_BIG_CHARS` · `_HUB_LIST_HEAD`(`:1623-1625`)는 graph_neighbors · object_fields · object_references 응답이 6만 자를 넘을 때 50개를 넘는 배열을 앞 50개로 줄이게 한다. `:1909-1917` 은 도구 래퍼(`_cap_tool` 안 `capped`)가 invoke_tool 경유면 안쪽 도구 이름으로 `_fold_hub_result` 를 부르는 자리다.
- 지금 판 — 에이전트 서버 main `7ca3a2e` 에 같은 코드가 `app.py:1712-1719` · `:2003-2011` 로 있다(94줄 밀림). `969e723..7ca3a2e` 의 app.py 커밋 넷(`ab87137` · `61c0ce9` · `d673846` · `7ca3a2e`)은 접기 자리를 건드리지 않았다. 접기가 걸렸는지 남기는 `fold_count` · `fold_stats` 는 지금 main 에도 0건이다(HA-34 근거 그대로).
- 배포판(허브 셋) — 이 박스에 리포가 없어 대조 못 함.
- 옛 사본(0.4.52)으로 본 것 — 세 칸 모두 그 꼴이다. objects_list 는 쪽 하나의 참조 이름표(`_ref_labels`)를 한 번 읽어 **모든 줄에** 통째로 싣는다(`backend/app/modules/objects/routes.py:1946` · `:1952-1959` · `_out` 의 `:281`). objects_summary 는 쓸 수 있는 기준 전부(`group_options`)를 늘 싣는다(`routes.py:621-630`, MCP 설명 `mcp_server/server.py:1600`). object_get 의 related 는 양방향 관계 전부를 상한 없이 싣는다(`routes.py:2236` · `_related` `:2849-2922`).

**우리 쪽 맞물림**

- HA-34(고치는 중) — 허브 응답을 접을 때 로그 한 줄(도구 이름 · 원문 자 수 · 접은 뒤 자 수)과 `/health` 의 접은 횟수를 남긴다. 10-29 · 10-30 재시험은 접기가 걸렸는지 가리지 못했다. 이것이 들어오면 원천이 줄인 뒤에도 접기가 걸리는지, 얼마나 줄었는지를 cae00 에서 잰다. 18:06 KST 에 가지 `wt1030/ha34`(`264b50f`)에 커밋이 있고 main 에는 아직 없다.
- HA-27 ③(고치는 중) — 자기검증 검토자에게 준 조회 결과가 창에 맞춰 잘렸으면(`_sc_fit(res, cap["res"])` — `969e723` `app.py:4371`, 지금 `7ca3a2e` `:4473`) 그 결과에서 온 수치는 고치지 말고 짚기만 하게 한다. 이 행의 '자기검증 입력을 크게 차지한다' 와 같은 자리다. 요청서 6절 첫 줄은 10만 자 넘는 응답 11건이 invoke_tool 경유(R-07)였는지 가르지 못했다며 HA-27 ③ 과 함께 보자고 했다.
- OB-96(우리 몫, 남았다) — 큰 응답(graph_neighbors · object_fields · object_references) 견본에서 사람 이름을 지워 dev 에 넘기면 dev 가 칸 모양에 맞춰 접기 규칙을 짓는다. 요청서 5절이 이 행 · HA-34 와 잇는다. 허브 쪽에 청하는 일이 아니다.
- 우리 쪽에서 다시 볼 자리(요청서 밖의 관찰) — 지금 접기는 objects_list 의 ref_labels 와 objects_summary 의 group_options 를 크기 · 깊이와 상관없이 칸 이름으로 걷는다(`_fold_hub_result` 의 `walk`, 지금 `app.py:1750-`). 원천이 ref_labels 를 쪽에 한 번만 싣게 바꿔도 칸 이름이 같으면 챗에는 가지 않는다. DP-01 이 들어오면 그 칸을 살릴지 우리 쪽에서 다시 본다.

### DP-02(다시) · 높음 — FailureTrace 솔더 접합 분류의 'hip' 오탐

- **무엇이**: (높음) FailureTrace 의 솔더 접합 불량 분류 약 82% 가 'hip' 글자 오탐이라, 챗이 내는 문제점 수가 부풀어 있다.
- **근거**: QA-CHAT-QWEN-20261029 5.5 — 389건 중 319건으로 10-27 과 같다. 10-30 OT-12 는 389건을 정답으로 셌고 오탐을 짚지 않았다.
- **할 일**: 자주검증 Datahub 의 그 분류 match_pattern 에서 짧은 영문 낱말(hip · pillow 등)에 낱말 경계를 두고, FailureTrace 연결을 다시 분류한다(데이터 · 관리 입력).
- **출처**: 12-Datahub-platform DP-02 · 90-OURS OB-58

**지금 판에서의 자리**

- 배포판 · 데이터 — 이 박스에 리포도 데이터도 없어 대조 못 함. match_pattern 은 허브의 데이터 · 관리 입력이다(할 일 칸).
- 옛 사본(0.4.52)에는 `match_pattern` 과 그 분류 낱말(hip)이 0건이다. 그 분류는 사본의 코드가 아니라 설치의 데이터 · 설정 쪽으로 보인다(대조 못 함).
- 10-29 요청서 5.5 의 FailureTrace 행이 같은 수(389건 중 319건 · 82%, OT-12)와 같은 고칠 곳을 적었다 — 그 분류를 코어 키 `JNT-SLD-01` 로 적었다([`../../request_261029.md`](../../request_261029.md) 5.5). 출처의 90-OURS OB-58 은 cae00 문서라 대조 못 함.

**우리 쪽 맞물림**

- 요청서가 이 행에 잇는 우리 쪽 고침은 없다. 고쳐지기 전까지 챗이 내는 솔더 접합 불량 수는 오탐이 든 수다 — 10-30 OT-12 도 389건을 정답으로 셌다(근거 칸).
- HA-27(고치는 중)이 들어오면 자기검증은 도구 원문의 수를 지키는 쪽이 된다. 원문의 오분류(이 행)는 원천에서만 고쳐진다.

### DP-04 · DP-05(다시) · 중간 — '메인 PBA' · 한국어 마케팅명 resolve 가 none

- **무엇이**: (중간) '메인 PBA' 와 한국어 마케팅명으로 resolve 하면 none 이다.
- **근거**: QA-CHAT-QWEN-20261029 5.5 에서 다시 쟀고 그대로 none 이었다.
- **할 일**: DP-04 — resolve 의 포함 단계에서 질의 안에 낱말로 든 별칭을 후보로 낸다. DP-05(데이터) — 과제 · 개발코드 행에 한국어 마케팅명 별칭을, 기판 부품 행에 '메인 PBA' · '메인 기판' 별칭을 넣는다.
- **출처**: 12-Datahub-platform DP-04 · DP-05

**지금 판에서의 자리**

- 배포판 · 별칭 데이터 — 이 박스에 리포도 데이터도 없어 대조 못 함.
- 옛 사본(0.4.52)으로 본 것 — resolve 는 식별자 → 별칭 · 외부 식별자 → 이름 → 포함 차례로 맞춘다(`backend/app/modules/objects/resolve.py:190-277`, MCP 설명 `mcp_server/server.py:1306-1307`). 포함 단계(`resolve.py:253-271`)는 이름 · 식별자 · 별칭이 **질의 글 전체를 품는지**(`%질의%`)만 본다. 질의 안에 낱말로 든 별칭(거꾸로 품음)은 보지 않는다 — DP-04 가 청하는 것이 이 빈자리다. 포함으로 걸린 것은 하나여도 후보다(`sure=False`, `:271`).
- 10-29 요청서 5.5 '별칭 공백' 행(10-29 다시 잼, none)과 같다. 10-30 에 다시 잰 기록은 요청서에 없다.

**우리 쪽 맞물림**

- 요청서가 이 행에 잇는 우리 쪽 고침은 없다.
- 후보로 내면 우리 코어 운영자는 하나를 고르지 않고 사람에게 묻는다 — 포털 `infra/personas/he-team.json:425`('candidates(여럿)면 고르지 말고 어느 것인지 묻는다') · `:439`(he-data-coreontology, `aec8e29` 뒤 바뀌지 않음). DP-04 의 '후보로 낸다' 는 그 길에 그대로 맞는다.

### DP-07(다시) · 중간 — failuretrace_whoami 한 번이 40초 안팎

- **무엇이**: (중간) failuretrace_whoami 한 번이 40초 안팎이라, '신원부터 확인' 하는 운영자 흐름이 멈춘다.
- **근거**: 게이트웨이 감사(도구 · ms · ok 만 읽음) — 성공 호출이 44,434 ms(10-29) · 39,206 ms(10-30)로 10-27 의 27~33초보다 길다. 같은 때 자주검증 허브 whoami 는 232~521 ms 다.
- **할 일**: facts 를 캐시하거나 근사 건수로 바꾼다.
- **출처**: 12-Datahub-platform DP-07

**지금 판에서의 자리**

- 배포판 — 이 박스에 리포가 없어 대조 못 함. 근거 수치는 cae00 게이트웨이 감사이고, dev 에는 허브 셋이 없어 다시 재지 못한다(포털 [`../../analysis-routines/context-notes.md`](../../analysis-routines/context-notes.md) C-6 '코어 허브 · FailureTrace · PLM · FMEA · ODB 가 dev 에 없고').
- 옛 사본(0.4.52)으로 본 것 — whoami 는 `/api/auth/me` 다음에 `/api/server/profile/live` 를 부른다(`mcp_server/server.py:742-758`). 그 facts 의 타입별 건수(`backend/app/modules/ontology/profile.py:28-42` `_counts`)는 프로세스 안에 60초(`COUNT_TTL`, `:22-24`)만 붙들어 둔다. 그보다 드물게 부르면 지워지지 않은 객체 전부를 타입별로 다시 센다.
- 같은 사본의 안내서는 같은 도구의 플랫폼이 여럿일 때 `whoami` 의 `platform` 을 보라고 하고(`mcp_server/guide/GUIDE.md:16-17` · `:77-79`), 접속 때 자기소개를 2초 안에 못 읽으면(`server.py:358`) 안내문 첫머리가 '자기소개를 읽지 못했다 — `whoami` 의 `platform` 을 본다' 로 바뀐다(`:385-393`). 요청서의 '신원부터 확인' 흐름이 이 길인지는 대조 못 함(배포판은 더 새것).

**우리 쪽 맞물림**

- 요청서가 이 행에 잇는 우리 쪽 고침은 없다.
- 포털 운영자 정의 · 설정(`infra/personas` · `backend/config`), 에이전트(`app.py` · `deliberation.py`), 게이트웨이 어디에도 whoami 를 먼저 부르라는 글이 없다(지금 판 grep — 게이트웨이는 도구 영역 표 `tool_areas.json:67` 의 `_whoami$` 분류에만 이름이 있다). 어느 허브의 결과인지는 에이전트가 결과마다 다는 '[이 결과는 ○○ 앱의 … 이다]' 머리(`_chat_result_note`, 지금 `app.py:1813-1818`)로도 안다. 그래서 이 호출을 우리 쪽 글로 줄일 자리는 찾지 못했다.

### DP-08(다시) · 중간 — pd_defect 글 속 검출자 · 작업자 이름

- **무엇이**: (중간) pd_defect 행의 label · content_text 에 검출자 · 작업자 이름이 그대로 실려 챗으로 나간다. HG-22 는 칸 이름 · 메일 · 계정 · 사설 IP 꼴만 가려 글 속 이름은 걸리지 않는다.
- **근거**: 10-27 온톨로지 시험 N-18 · 개발 결정 D-4(원천에서 가린다 — reflection-1028/03 HA-25). 게이트웨이는 자유 글 속 이름을 꼴로 가르지 않는다(`44f4b8d` `gateway.py:606-608` 주석).
- **할 일**: FailureTrace 출력에서 사람 이름 칸을 가린다. 4절의 원천 쪽 개인정보 요청(AR-10 · PA-20)과 같은 묶음으로 보낸다.
- **출처**: 12-Datahub-platform DP-08 · 03-HWAXAgentServer HA-25 · 90-OURS OB-07

**지금 판에서의 자리**

- 근거의 HWAX 줄(대조함) — `44f4b8d` `gateway.py:606-608` 은 개인정보 가림 머리 주석이다. '원천에서 가리는 몫(FailureTrace 의 label · content_text 안 이름 — D-4, PLM — 보류)은 그쪽에 있다' 와 'JSON 은 **칸 이름**으로 가린다 … 자유 글의 사람 이름은 꼴로 가르지 않는다(오탐이 수치 · 부품명을 지운다)' 가 그 줄이다.
- 지금 판 — 게이트웨이 master `67d8d00` 에 같은 주석이 `gateway.py:607-609` 로 있다(줄 하나 밀림). `44f4b8d..67d8d00` 의 gateway.py 커밋 여섯(`1539b5b` · `8dc2719` · `1c7fcc1` · `00ef0ab` · `cca98c8` · `67d8d00`)은 가림 자리를 건드리지 않았다. 칸 이름 목록 `_PII_KEYS`(지금 `:613-620`)의 '이름' 칸에는 detector · detected_by · inspector · worker_name · 검출자 · 작업자 등이 이미 있지만 label · content_text 는 없다. 이름이 그 두 칸의 글 속에 있어서 걸리지 않는다.
- 결정 기록은 이 박스에 있다 — [`../../request-1027/context-notes.md`](../../request-1027/context-notes.md) D-4('원천(FailureTrace, 12-Datahub-platform DP-08)에서 가린다. 에이전트는 바꾸지 않는다') · [`../../request-1027/03-HWAXAgentServer.md`](../../request-1027/03-HWAXAgentServer.md) HA-25 행. 출처의 90-OURS OB-07 은 cae00 문서라 대조 못 함(10-27 게이트웨이 요청서는 그것을 가림 범위의 결정 기록이라 적었다 — [`../../request-1027/02-HWAXMcpGateway.md`](../../request-1027/02-HWAXMcpGateway.md) '개인정보 가림(HG-20)').
- 배포판(FailureTrace) — 이 박스에 리포가 없어 대조 못 함.
- 옛 사본(0.4.52)으로 본 것 — `pd_defect` · `content_text` 는 0건이다(설치의 타입 · 칸 이름으로 보인다). 코어 객체 출력에 사람 이름을 가리는 자리는 없고, 보는 사람이 못 보는 객체의 이름을 '(볼 수 없는 객체)' 로 바꾸는 것뿐이다(`backend/app/modules/objects/system.py:121-122` · `:154-156` · `:176-180`). 사람 이름을 가명으로 내리는 꼴은 확장의 인력 표 한 곳에 있다('가명이 기본, 실명은 권한이 있을 때만' — `backend/app/extensions/caegroup/services.py:998-1016` · `:1049-1050`).

**우리 쪽 맞물림**

- HG-22(고치는 중) — 칸 이름에 owner · partOwner · submitter · user · email · assignee 꼴을 더하고, 메일 꼴 · 사내 계정 꼴(영문.영문숫자) · 사설 IP 꼴은 칸 이름과 상관없이 가리며, REST 다리 출력도 같은 가림을 거친다. 그래도 label · content_text 안의 사람 이름(검출자 · 작업자)은 꼴로 가르지 않아 걸리지 않는다. 그래서 이 행은 원천 몫 그대로다([`../outbound.md`](../outbound.md) 2절 '포털 쪽 짝'). 18:06 KST 에 게이트웨이 가지 `wt1030/pii` 에는 아직 커밋이 없다(master 와 같은 `67d8d00`).
- 게이트웨이 가림은 게이트웨이를 지나는 응답에만 걸린다 — 같은 주석의 '원문이 필요한 화면은 게이트웨이를 거치지 않고 그 앱에서 본다'(지금 `gateway.py:606-607`).
- 같은 원천 가림 묶음의 다른 곳 — StepForge 는 담당자 칸(ST-12 (3))을 원천에서 가린다고 답했다([`../outbound.md`](../outbound.md) 1절). AR-10 은 사람이 보낼 차례이고, PA-20 은 SmartTwinExplorer 가 10-30 끝냈다고 답했다(`4f5e0e0` — cae00 반영은 사람 몫, 같은 표).

### DP-06(다시) · 낮음 — graph_neighbors 의 최상위 truncated 가 늘 참

- **무엇이**: (낮음) graph_neighbors 의 최상위 truncated 가 간선을 다 받아도 참이라, 챗이 '관계가 잘렸다' 고 답한다.
- **근거**: QA-CHAT-QWEN-20261029 5.5 'DP-06 그대로' · QA-DIGITAL-WORKER-20261030 DW-01 답도 truncated 를 밝혔다.
- **할 일**: 초점 노드의 간선이 잘렸을 때만 참으로 하고, 이웃 쪽에 더 있는 것은 다른 칸으로 낸다.
- **출처**: 12-Datahub-platform DP-06

**지금 판에서의 자리**

- 배포판 — 이 박스에 리포가 없어 대조 못 함. 10-30 DW-01 은 cae00 QA 문서라 대조 못 함.
- 10-29 요청서 5.5 의 부서 허브 행 끝에 'graph_neighbors 최상위 truncated 가 모든 간선을 받아도 참이다(DP-06 그대로)' 가 있다([`../../request_261029.md`](../../request_261029.md) 5.5).
- 옛 사본(0.4.52)으로 본 것 — 최상위 `truncated` 는 실제로 버린 경우(노드 상한 `backend/app/modules/graph/routes.py:486-488`, 간선 상한 `:503-505`) 말고도 실린 **모든 노드**의 '더 있음'(`degree > shown`)을 OR 로 모은다(`:544-545`). 바깥 고리의 이웃은 대개 다른 간선이 더 있으므로, 초점 노드의 간선을 다 받아도 참이 되기 쉽다 — 요청서가 말한 꼴과 맞는다. 노드마다의 `truncated`(`:558`)는 이미 따로 있다.

**우리 쪽 맞물림**

- 에이전트도 graph_neighbors 를 접는다 — 응답이 6만 자를 넘으면 50개 넘는 배열을 앞 50개로 줄이고 결과 머리에 '[포털 챗이 허브 응답을 접었다 — …]' 를 단다(`_HUB_FOLD_LISTS` · `_fold_hub_lists`, 지금 `7ca3a2e` `app.py:1717-1747`). 그래서 챗이 '잘렸다' 고 말한 까닭이 허브의 truncated 인지 에이전트 접기인지는 답 글만으로 가르기 어렵다. HA-34(고치는 중)의 접기 로그가 그것을 가른다 — 원천이 고친 뒤 DW-01 을 다시 볼 때 함께 본다.
- HA-30(고치는 중) — 같은 도구의 다른 일이다. OT-07 에서 failuretrace_graph_neighbors 에 자주검증 id 가 넘어가 APP-GRAPH-0001 이 났다. 에이전트가 부르기 전에 다른 허브의 id 를 걸러 key 로 다시 풀게 한다(설계 초안 [`../design-ha30.md`](../design-ha30.md)). 이 행에서 허브 쪽에 더 청하는 것은 없다.
- 새 칸(이웃 쪽에 더 있는 것)이 생기면, 코어 운영자 글 '허브 응답이 크면 챗이 접는다(관계는 관계별 수와 앞 다섯)'(`infra/personas/he-team.json:435`)와 에이전트 접기가 그 칸을 읽어야 하는지 우리 쪽에서 본다.

### DP-09(다시) · 낮음 — 코어 공백이 챗 답의 빈칸이 된다

- **무엇이**: (낮음) 코어 공백(시험항목의 부하 칸 · 낙하 시험 한 항목의 검출 고장모드 · tests_part 0건)이 챗 답의 빈칸이 된다.
- **근거**: 10-27 뒤 다시 잰 기록이 없다. 10-30 OT-07 · 10 · 11 은 PASS 라 당장의 영향은 작다.
- **할 일**: 그대로 남았다고 알린다(데이터 · 관리 입력).
- **출처**: 12-Datahub-platform DP-09

**지금 판에서의 자리**

- 배포판 · 데이터 — 이 박스에 리포도 데이터도 없어 대조 못 함. 10-27 뒤 다시 잰 기록은 이 박스의 문서에도 없다(`tests_part` 는 이 요청서에만 나온다).
- 옛 사본(0.4.52)에도 견줄 코드가 없다 — 데이터 · 관리 입력이다.

**우리 쪽 맞물림**

- 요청서가 이 행에 잇는 우리 쪽 고침은 없다. 할 일이 '그대로 남았다고 알린다' 라 고치라는 청이 아니라 알림이다.

## 끝나면

- **누구에게** — 답 · 결과는 이 시트를 전한 사람(사용자)에게 준다. 사람이 HWAX 포털 세션 `hwaxportal-a5` 에 옮기면, 세션이 [`../outbound.md`](../outbound.md) 2절의 Datahub 줄과 `../server-setup.md`(cae00 에서 사람이 할 일 — 아직 없는 파일, 체크리스트 4절에서 만든다)에 적는다.
- **반영물** — Datahub 플랫폼은 update-all 로 받지 않는다(정본 머리 3줄). 그래서 우리가 받을 SIF · Drive 판은 없고, 반영은 그쪽 배포로 끝난다. 행마다 어느 허브(자주검증 · FailureTrace · 부서 허브)에 반영했는지, 판(커밋 · 판 번호)과 cae00 에 반영한 시각을 알려 달라.
- **함께 알려 줄 것**
  - 코드 행 — DP-14 는 바뀐 오류 글 한 예, DP-01 은 바꾼 뒤 objects_list · objects_summary · object_get 응답 한 예의 크기와 바뀐 칸 꼴(쪽에 한 번 싣는 ref_labels 의 자리 · group_options 를 다시 받는 길), DP-04 는 질의 안의 별칭이 후보로 나온 한 예, DP-06 은 최상위 truncated 의 새 뜻과 이웃 쪽 칸의 이름, DP-07 은 바꾼 뒤 whoami 한 번의 시간, DP-08 은 가린 칸과 가림 표시 꼴.
  - 데이터 행 — DP-02 · DP-05 는 넣은 날짜와 건수(DP-02 는 다시 분류한 뒤의 솔더 접합 불량 수), DP-09 는 남은 공백 목록, DP-15 는 적재 계획(할지 · 언제 · 어떤 기록을)과 일정.
  - 도구 이름 · 인자 · 칸 이름이 바뀌면 그 목록 — 우리 쪽이 이름으로 읽는 자리가 있다. 에이전트 접기 표(`_HUB_FOLD` 의 group_options · ref_labels · properties_schema · related, `_HUB_FOLD_LISTS` 의 graph_neighbors · object_fields · object_references), 조건 주소 꼬리(`_chat_result_note`), 포털 코어 어휘표(`backend/config/core_vocab.json` 의 object_resolve · objects_list · objects_summary · graph_neighbors · object_get), 코어 운영자 정의(`infra/personas/he-team.json` he-data-coreontology). cae00 에서는 사람이 게이트웨이 `/tools-map` 으로 새 도구가 실렸는지 본다.
- **다시 볼 시험** — 요청서 7절에 이 플랫폼 줄은 없다. 행의 근거가 된 문항으로 다시 본다. DP-14 는 OT-09 · 11(APP-OBJECTS-0073 횟수 — OT-09 는 7절 첫 줄 HA-27 뒤에도 든다), DP-01 은 OT 재시험의 10만 자 넘는 응답 수(QA-CHAT-QWEN-20261030 4절)와 HA-34 의 접기 로그, DP-02 는 OT-12, DP-04 · DP-05 는 '메인 PBA' · 한국어 마케팅명 resolve(QA-CHAT-QWEN-20261029 5.5), DP-06 은 DW-01, DP-07 은 게이트웨이 감사의 failuretrace_whoami ms, DP-08 은 N-18, DP-09 는 OT-07 · 10 · 11 이다. 다시 보는 것은 cae00 에서 사람이 한다(dev 에는 허브 셋이 없다).
- **우리 몫(이 플랫폼에 청하지 않음)** — 허브 셋의 앱 설명 문안(OB-33)과 큰 응답 견본(OB-96)은 요청서 5절의 우리 몫이다. 코어 허브의 쓰기 · 잡 도구(object_create · object_update · objects_delete · object_merge · datasource_sync · bundle_import · job_apply)는 포털 HP-53 이 코어 운영자의 `writes` · `confirm` 에 나눠 넣고, 에이전트 HA-29 가 사람이 시키지 않았으면 확인 카드로 멈춘다. 둘 다 고치는 중이고 허브 쪽 할 일은 없다. 그 도구 이름이 바뀌면 위 목록과 함께 알려 달라.
