# 10-29 후속 4차 — E-2 앱 역할(순위 · 접기 · 노출) · E-4 개인 Claude 묶음 설계

> 설계만이다 — 코드는 고치지 않았다(2026-10-31 KST). 계획 행은 [PLAN.md](PLAN.md) 2.4 의 E-2 · E-4(4차 — 따로 계획)이고, 둘은 재시험 · 평가셋이
> 기준선이라 그 뒤에 본다([context-notes.md](context-notes.md) C-17 · 결정 D-7).
> 기준 판 — 포털 main `dbbb943` · 게이트웨이 master `602bbb2` · 에이전트 서버 main `d6c3a84` · Datahub 플랫폼(SP) `778db2f`(0.4.67, 읽기만).
> 줄 번호는 이 판의 것이다 — 판이 바뀌면 함수 이름으로 찾는다.
> 읽는 사람 — dev 세션(구현) · 사용자(4절 — 세션에서 묻는다) · **cae00 세션(5절 — 이 문서가 포털 리포로 닿으면 그 절만 읽고 잰다)** ·
> 사람(6절 — 다른 플랫폼에 보낸다).

## 0. 한눈에

| | E-2 앱 역할 | E-4 개인 Claude 묶음 |
|---|---|---|
| 지금 | 역할은 포털 어휘표에 있다. 게이트웨이는 정본(소개 줄 · 사본 접기)과 시험(숨김)만 읽고, 형제 · 비코어는 에이전트 서버의 프롬프트 글에만 쓰인다. | 서버 하나(`hwax`)가 권한 안의 도구를 전부 낸다(cae00 10-27 1,612개). 줄이는 길은 앱 끄기뿐이고, 끄면 목록과 검색에서 함께 빠진다. |
| 빈 곳 | 사본 접기가 '설명이 글자까지 같다' 에 기댄다 — 허브 판이 어긋나거나 우리가 청한 설치별 소개(DP-03)가 들어오면 세 줄로 돌아간다. 접두가 '지금 떠 있는 허브끼리 겹치나' 로 정해져 이름이 뒤집힐 수 있다. 검색은 비코어를 모른다. | 검색에는 남기고 목록만 줄이는 길이 없다. 찾기 · 부르기 두 도구만 보이는 모드가 없다. 클라이언트(리포 파이프라인 · 다른 프로젝트 · Desktop)마다 목록을 달리할 길이 없다. |
| 먼저 잴 것 | cae00 재시험(M-1) · 허브 이름 · 설명 대조(M-2 · M-3) · 코어 질의의 역할 분포(M-5) · 검색 평가 기준선(M-6). | 목록 크기(M-3) · 개인 PAT 의 영역 분포(M-4) · 클라이언트(Q-11). |

권장 다섯 줄.

1. 게이트웨이가 어휘표의 역할을 다 읽고(가족 = 정본 + 형제 · 비코어 · 시험) `/health` · `list_tool_apps` 에 싣는다.
2. 허브 가족은 원래 이름으로 접고(설명이 달라도) 늘 접두를 단다 — cae00 의 지금 이름은 그대로다(M-2 로 확인).
3. 비코어 낮추기는 검색 손잡이로 짓되 기본은 끈다. cae00 `/search-eval` 에서 켜고 끈 비교를 본 뒤 박스 덧씌우기로 켠다. 형제 소개 줄은 문안이 오면 덧씌우기로 단다.
4. 개인 Claude 에 보기 셋(전체 · 묶음 · 가벼운)을 두되 `tools/list` 에만 건다 — 검색 · 부르기 · 이름 · 권한은 그대로다.
5. 보기는 포털 사람 설정(앱 끄기와 같은 길)으로 고르고 연결 머리가 그것을 덮는다(리포 `.mcp.json` 은 늘 전체). 묶음 단위는 도구 영역이고, 묶음에는 정본 읽기 다섯이 늘 들고 형제 사본은 빠진다.

## 1. E-2 — 앱 역할로 순위 · 접기 · 노출

### 1.1 지금

| 무엇 | 어디 | 지금 하는 일 |
|---|---|---|
| 역할의 정본 | 포털 `backend/config/core_vocab.json:4-8` · `:37-46`, 역할 셋 `backend/tests/test_core_vocab.py:11` | 정본 `rootdesigndatahub`(소개 줄) · 형제 둘(`failuretrace` · `caegroupdatahub`) · 비코어 여섯(RA · MatNexus · ComponentCore · FMEA · ARP · ODB 허브) · 시험 0 — 10-31 OB-04(`dbbb943`)가 운영 앱 둘을 뺐고 역할 자체는 박스 덧씌우기의 길로 남았다. 박스 덧씌우기 `core_vocab.local.json`(E-7 ②)으로 커밋 없이 고친다. |
| 게이트웨이가 읽는 것 | `gateway.py:3236-3248`(`_core_vocab_parse`) | 검색 낱말 · 정본 키 · 소개 줄 · **시험 셋만** 읽는다. 형제 · 비코어는 읽지 않는다. |
| 에이전트가 읽는 것 | `app.py:299-333`(`_core_rules_text` — ⑤ 형제 · ⑦ 비코어) · `:350-356`(허브 표 — 다른 허브 id 막이 HA-30) | 웹 챗의 프롬프트 글과 id 막이에만 쓴다. 개인 Claude · 심의 좌석에는 닿지 않는다. |
| 이름 | `gateway.py:1283-1336`(`_aggregate`) · `:1089-1099`(별칭 주석) · `:1419-1437`(`_keep_last`) | 지금 붙은 백엔드끼리 이름이 겹칠 때만 `<키>_<이름>` 으로 낸다. 호출 별칭 `<키>_<이름>` 은 늘 있다(목록에는 안 올린다). 허브 셋은 같은 SP 도구(0.4.67 기준 103개 — SP `mcp_server/server.py` 의 `@tool()`)를 내므로 이름이 같고, cae00 에서 셋 다 접두가 붙는다(cae00 의 판 · 수는 M-3). 못 받은 백엔드의 직전 목록은 10회까지 쥔다. |
| 설명 | `gateway.py:1326` · `:3317-3322`(`_core_tagged`) | 정본 도구 설명 앞에만 `[소개 줄]` 을 붙인다. 형제는 정본과 글자까지 같다. SP 는 설치 소개를 서버 안내문에만 싣고(SP `mcp_server/server.py:400-482`) 게이트웨이는 하위 서버의 안내문을 전하지 않는다. SP 도구에는 MCP 주석(readOnlyHint 등)이 없다. |
| 순위 | `gateway.py:3366-3567`(`_search_tools`) | 이름 적중은 노출 이름(접두 포함 — `:3424` · `:3435`), 앱 적중은 라벨 · 설명(`:3427-3437`), 질의가 앱 이름을 부르면 이름 적중과 같은 무게(`:3439-3441`), 쓰기 감점(`:3459-3462`), 점수가 같으면 사본 표지 · 이름 차례(`:3466`). 역할은 순위에 들지 않는다. |
| 접기 | `gateway.py:3476-3496` | 원래 이름 + 소개 줄을 뗀 설명(`:3480`)이 같은 줄을 한 무리로 접고 정본이 무리를 대표한다(정본이 점수 0 이라 줄에 없어도 — `:3481-3492`, C-12). 질의가 사본의 앱 이름을 부르면 그 사본이 대표한다(`:3486`). 접힌 것은 `same_in`(`:3538-3539`), 안내는 '설명까지 같은 사본'(`:3563`). 손잡이 `copy_fold`(`:3114`). |
| 노출 | `gateway.py:5216-5224`(`_visible_tools`) · `:6149-6152`(`tools/list`) · `:3609-3714`(`list_tool_apps`) | 끈 앱 ∪ 시험 앱을 목록 · 검색에서 뺀다(C-18). `list_tool_apps` 는 역할을 싣지 않는다. |
| 건강 줄 | `gateway.py:3293-3304` | `canonical_backend`(정본 키가 이 박스 백엔드에 있나) · `staging_hidden` 만 — 형제 · 비코어 키가 이 박스에 있는지는 말하지 않는다. |
| 이름에 기대는 곳 | 에이전트 `app.py:2636-2642`(`_ONTO_CORE` — 허브 노출 이름 12개) · `:1700-1720`(`_hub_of` · `_hub_tool` — 허브 하나 박스의 맨 이름까지 안다) · 포털 `infra/personas/he-team.json:466-507`(코어 운영자의 key_tools · writes · confirm · optional) · 리포 `.claude/settings.json`(허용 47개) | 노출 이름이 바뀌면 조용히 빠진다. |

### 1.2 빈 곳

- **G1 접기가 설명 글자에 기댄다.** 10-29 에는 허브 설명이 글자까지 같아 C-12 접기가 들었다. 그런데 ① 허브 판이 어긋나면(한 허브만 SP 를 올린 사이) 바뀐 도구는 세 줄로 돌아간다.
  ② 우리가 청한 Datahub 플랫폼 DP-03(설치별 소개를 도구 설명에)이 들어오는 날, 그 소개 때문에 **모든** 허브 도구가 접기에서 빠진다 — 고치라고 청한 것이 C-12 를
  되돌린다. `_core_untagged` 는 게이트웨이가 붙인 줄만 뗀다.
- **G2 이름이 남의 사정으로 바뀐다.** 접두는 '지금 붙은 허브끼리 겹치나' 로 정해진다(`gateway.py:1313-1318`). 한 허브에만 있는 새 도구(판 어긋남)는 맨 이름으로 나왔다가
  나머지가 올라오면 접두 이름으로 바뀐다 — 그 이름을 외운 클라이언트 · 허용 규칙 · 운영자 정의가 `unknown tool` 이 된다(`:1089-1097` 의 경고와 같은 꼴). 허브가 하나뿐인
  박스에서는 허브 도구가 거의 맨 이름이라 `_ONTO_CORE` · `he-team.json` 의 접두 이름이 목록에 없다(에이전트 `_hub_tool` 만 이 경우를 안다).
- **G3 형제가 무엇을 담는지 모델이 모른다.** 형제 설명은 정본과 같고 소개 줄은 정본에만 있다. 개인 Claude 의 전체 목록에는 형제 사본 약 206개(2 × 103)가 구별 없이 실린다.
- **G4 검색이 비코어를 모른다.** OT-06 ~ 10 은 FMEA · ARP · MatNexus · RA 로 갔다. 웹 챗은 프롬프트 규칙 ⑦ 로 막지만 `search_tools` 순위에는 비코어 표시가 없어, 설명에
  '고장모드 · 시험항목' 이 든 비코어 도구가 코어 질문에 오른다. 개인 Claude · 심의 좌석은 규칙 ⑦ 도 받지 않는다.
- **G5 접두가 우연한 앱 신호다.** `failuretrace_` 의 failure 가 동의어에 맞아 '불량' 질문에서 FailureTrace 가 앞선다. 이름 적중을 원래 이름으로 보면 이 신호가 사라져
  '시장 불량 원인 대책' 상위 10에 심의 가족이 올랐다(C-16). 형제가 무엇을 담는지(진짜 신호)는 어디에도 적혀 있지 않다.
- **G6 역할 키가 틀려도 조용하다.** 박스 덧씌우기에 형제 키를 잘못 적으면 그 형제는 어디서도 형제로 안 쓰인다. `/health` 는 정본 키만 대조한다.

### 1.3 안 — 축 다섯, 축마다 둘 · 셋

#### 접기(G1)

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| F-A 가족 접기 | 허브 가족(정본 + 형제)의 줄은 **원래 이름만** 으로 무리 짓는다 — 설명은 보지 않는다. 그 밖의 앱은 지금 열쇠 그대로. 설명이 다른 사본은 `same_in` 에 `differs: true`. | 판 어긋남 · DP-03 에도 한 줄이 남는다. 설명이 같으면 지금과 바이트까지 같다. | 같은 이름인데 인자가 다른 사본(판 어긋남)도 접힌다 — `same_in` 이 다르다고 말하고, 그 이름으로 부르면 그 허브의 인자를 쓴다. 역할 표가 틀리면 엉뚱하게 접는다(G6 의 건강 줄로 막는다). |
| F-B 설명 다듬어 견주기 | 견줄 때 설명 머리의 `[…]` 줄을 떼고 견준다. | 역할 표에 기대지 않는다. | DP-03 이 어떤 꼴로 올지 모른다(머리 · 꼬리 · 줄바꿈). 판 어긋남은 못 막는다. |
| F-C 그대로 | DP-03 · 판 올림 때마다 다시 잰다. | 고칠 것이 없다. | 깨지는 날을 미리 알 수 없다 — 허브 판 올림은 우리 손이 아니다. |

#### 이름(G2)

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| N-A 가족은 늘 접두 | 허브 가족의 도구는 겹침과 상관없이 `<키>_<이름>` 으로 낸다. | cae00 의 지금 이름 그대로다(셋 다 이미 접두 — M-2 로 확인). 판 어긋남 · 허브 하나 박스에서도 이름이 안 뒤집힌다. `_ONTO_CORE` · 운영자 정의가 어느 박스에서나 맞다. | 지금 맨 이름으로 나가는 허브 도구가 cae00 에 있으면 그 이름이 바뀐다(M-2 가 센다 — 0 이 아니면 Q-2). |
| N-B 지금 규칙 + 알림 | 규칙은 그대로, 가족 도구가 맨 이름이면 `/health` · update-all 이 ⚠. | 이름이 안 바뀐다. | 뒤집힘은 그대로 일어나고 사람이 볼 뿐이다. |
| N-C 정본만 맨 이름 | 정본 도구는 맨 이름, 형제만 접두. | 이름이 짧다. | **cae00 에서 정본 103개의 이름이 바뀐다** — `_ONTO_CORE` · 운영자 정의 · 허용 규칙이 깨지고 E-4 의 '이름 그대로' 와 어긋난다. 권하지 않는다. |

#### 형제 알리기(G3 · G5)

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| S-A 소개 줄 + 순위 신호 | 어휘표 `apps.<키>.tagline` 을 그 형제 도구 설명 앞에 붙이고(정본과 같은 길), `apps.<키>.words`(형제가 담는 낱말)를 앱 적중으로 쓰며, 가족의 이름 적중은 원래 이름으로 본다. | 모델과 순위가 함께 형제를 가른다. C-16 의 우연한 신호를 적어 둔 신호로 바꾼다. | 순위가 바뀐다 — C-16 처럼 다른 질의가 밀릴 수 있다. 낱말 고르기가 새 손 표가 된다. |
| S-B 소개 줄만 | `apps.<키>.tagline` 이 있으면 붙인다. 순위는 그대로. | 모델이 목록 · 검색 결과에서 형제를 가른다. 비면 지금과 같다. DP-03 이 오면 걷는다(R-3 과 같은 규칙). | 우연한 신호(G5)는 그대로다. 문안을 사람이 써야 한다. |
| S-C DP-03 을 기다린다 | 게이트웨이는 손대지 않는다. | 겹치는 일이 없다. | 언제 올지 모른다. 그동안 형제는 구별되지 않는다. |

#### 비코어(G4)

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| C-A 코어 질문에서 낮추기 | 코어 질문(어휘표 검색 낱말이 든 질의 — R-5 와 같은 판정)에서 비코어 앱 도구의 점수에 `weights.noncore`(0.5)를 곱한다. 질의가 그 앱 이름을 부르면 낮추지 않는다. 손잡이 `switches.noncore_demote`(**기본 끔**), 순위 기록에 `demote:noncore`. | 웹 챗 · 개인 Claude · 심의 좌석이 함께 받는다. cae00 덧씌우기로 켜고 끈다(C-31). | 코어 낱말이 든 비코어 질문('규격의 고장모드 사례')에서 그 앱이 밀린다 — 앱 이름을 말하지 않으면. |
| C-B 역할을 보이기만 | `list_tool_apps` 앱 줄 · `/tools-map` apps · 검색 결과 줄(가족 · 비코어만)에 `role` 과 비코어의 note 를 싣는다. 순위는 그대로. | 순위를 안 건드린다. 개인 Claude 도 규칙 ⑦ 에 해당하는 것을 읽는다. | 모델이 읽어야 효과가 난다. 결과 글이 조금 는다. |
| C-C 비코어 설명에 꼬리표 | 비코어 도구 설명 앞에 '[코어 아님 — …]'. | 모든 소비자가 본다. | 남의 플랫폼 설명을 우리가 바꾼다(C-30 — 원래 그쪽 몫). 권하지 않는다. |

#### 노출(G3)

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| X-A 전체 보기에서도 형제 사본을 뺀다 | 개인 PAT 의 `tools/list` 에서 형제 도구를 뺀다(검색 · 부르기는 된다). | 개인 목록이 약 206개 준다. | 지금 쓰는 사람의 목록이 바뀐다 — 형제를 직접 쓰던 사람은 재연결 뒤 그 이름을 목록에서 못 본다. |
| X-B 묶음 · 가벼운 보기에서만 뺀다 | 전체 보기는 그대로. E-4 의 묶음 보기는 가족 가운데 정본만 싣는다. | 바뀌는 것은 보기를 고른 사람뿐이다. | 전체 보기의 크기는 그대로다. |

### 1.4 권장 — 걸음

F-A · N-A · S-B · C-A(기본 끔) + C-B · X-B 다. S-A 는 cae00 숫자를 본 뒤로 미룬다.

| 걸음 | 무엇 · 고칠 곳 | 시험 | 받아들임 |
|---|---|---|---|
| E2-1 역할 읽기 · 보이기(C-B · G6) | `_core_vocab_parse`(`gateway.py:3236`)가 가족(정본 + 형제, 어휘표 차례) · 비코어 셋 · 앱별 소개 줄(새 칸 `apps.<키>.tagline`, 비면 없음)을 읽는다. `/health core_vocab.roles` — 가족 · 비코어 키마다 이 박스 백엔드에 있나. `list_tool_apps` 앱 줄 · `/tools-map` apps 에 `role`(가족 · 비코어만). 검색 결과 줄에는 형제 · 비코어에만 `role`. 포털 꼴 시험에 `tagline`(형제에만 · 120자 이내). | 실제 어휘표 + 형제 하나를 더한 덧씌우기로 셋이 맞다 · dev 카탈로그의 `search_tools` 답이 지금 코드와 바이트까지 같다(`_SEARCH_TOOLS_MASTER` — dev 에는 가족 · 비코어 앱이 붙어 있지 않다) · 합성 허브 카탈로그(`test_gateway.py` 의 `_CORE_HUBS`)에서 `role` 이 그 줄에만. | 게이트웨이 · 포털 시험 통과. |
| E2-2 가족 접기(F-A) | 접기 열쇠(`:3480`)와 정본 사본 표(`:3481-3482`) — 가족 줄은 원래 이름, 그 밖은 지금 열쇠. 정본 대표 · 이름 부른 사본 대표는 그대로. 설명이 다른 사본만 `same_in` 에 `differs: true` 를 달고, 그때만 안내 끝에 '형제 허브의 같은 이름 도구 — 담은 데이터가 다르다' 를 붙인다. 손잡이 `copy_fold` 아래(끄면 접지 않는다). | 형제 설명에 DP-03 꼴 머리 줄을 붙인 합성 카탈로그 — 한 줄 · `same_in` 둘 · `differs` · 설명이 같은 합성 카탈로그 — 지금 코드와 바이트까지 같다 · OT-12(사본 앱 이름을 부름) 그대로(`test_R4_같은_도구의_사본은…` 이 그대로 지난다). | 같다. |
| E2-3 가족 접두(N-A) | `_aggregate`(`:1313-1318`) — 가족 키면 늘 접두. 가족이 바뀌면(덧씌우기) 소개 줄처럼 다시 집계를 예약한다(`_REAGG`, `:3287-3289`). `/health core_vocab.roles` 에 '이 규칙으로 접두가 붙은 이름 수'. | 허브 하나 카탈로그 · 한 허브에만 있는 도구 → 접두 · 가족 밖 앱의 맨 이름 그대로 · 허브 셋 카탈로그의 이름이 지금 코드와 같다(목록 대조) · 에이전트 `_ONTO_CORE` 열두 이름을 형제 리포 `app.py` 에서 읽어 허브 셋 · 허브 하나 카탈로그 둘 다에 있는지(C-11 처럼 형제 파일을 읽는 시험 — 형제 리포가 없으면 까닭을 찍고 건너뛴다). | 같다 + cae00 반영 뒤 M-2 에서 '바뀐 이름 0'(0 이 아니면 Q-2 대로). |
| E2-4 형제 소개 줄(S-B) | `_core_tagged` · `_core_untagged`(`:3307-3322`)를 앱별 소개 줄로 넓힌다. 소개 줄은 라벨로 시작하게 쓴다 — 에이전트 `_tag_tool_app`(`app.py:2392-2401`)은 '[' 로 시작하는 설명에 앱 라벨을 다시 붙이지 않는다. 문안은 사람(Q-3)이고 비면 지금과 같다. | 소개 줄이 있는 형제만 붙는다 · 떼면 원문 · 접기 그대로 · 웹 챗 묶음의 `failuretrace_*` 넷 설명이 늘어난 몫을 센다. | 같다. 문안이 오면 cae00 덧씌우기로 먼저 켠다. |
| E2-5 비코어 낮추기(C-A, 기본 끔) | 점수 줄(`:3452-3462` 사이) — 코어 질문 · 비코어 앱 · 그 앱 이름을 안 부름이면 `weights.noncore` 를 곱하고 `via` 에 `demote:noncore`(보정 뺀 점수도 같이 곱해 `boost_only` 판정은 그대로). `search_tuning.json` 에 `switches.noncore_demote: false` · `weights.noncore: 0.5` — 칸이 없으면 켬으로 읽는 지금 규칙(`:3167`) 때문에 기본 끔은 적어 둬야 한다. 평가 판(`_eval_variants`, `:2989-3001`)에 '꺼진 손잡이 하나씩 켬'(`+noncore_demote`)을 더해 `/search-eval` 이 켠 값을 함께 잰다. | 기본값에서 바이트까지 같다 · 켜면 '관리 기준 개수' 의 FMEA · ARP 줄이 정본 읽기 도구 아래로 · 'FMEA 규격 실패모드'(이름 부름)는 그대로 · 코어 낱말 없는 질의는 그대로 · 질의 기록 `via` 에 `demote:noncore`. | 같다. 켜기는 cae00 덧씌우기로(5절 M-6 비교 뒤, Q-1). |
| E2-6 (미룸) 형제 순위 신호(S-A) | 가족의 이름 적중을 원래 이름으로, 형제 낱말을 앱 적중으로. | C-16 의 두 질의(auto-045 · '시장 불량 원인 대책')를 함께 본다. | cae00 M-5 · M-6 에서 형제가 잘못 오르거나 밀리는 것이 보일 때만. |

### 1.5 하지 않는 것

- 노출 이름을 바꾸는 안(N-C)은 하지 않는다.
- 비코어 플랫폼의 설명을 고치지 않는다(C-C) — 그쪽 몫이다(C-30 · E-8 보고서로 돌려준다).
- 웹 챗 묶음은 손대지 않는다 — 에이전트 서버가 예산과 `_ONTO_CORE` 로 고른다(형제 넷이 늘 묶인다, `app.py:2741`).
- 시험 역할은 그대로다 — 기본 표는 비었고(OB-04) 박스 덧씌우기의 길로 남는다.
- 에이전트 `_ONTO_CORE` 의 하드코딩을 어휘표에서 짓는 일은 따로다 — 이 묶음은 이름을 안 바꾸므로 그것 없이 맞는다.

## 2. E-4 — 개인 Claude 묶음 · 가벼운 모드

### 2.1 지금

| 무엇 | 어디 | 지금 |
|---|---|---|
| 등록 | 포털 `frontend/src/lib/setupBat.ts:28`(`/mcp-gw/mcp`) · `:129`(`claude mcp add -s user --transport http hwax …`) · 리포 `.mcp.json`(`hwax` — 토큰은 환경변수) | 서버 하나(`hwax`)다. 도구 이름은 `mcp__hwax__<노출 이름>` 이다. |
| 목록 | 게이트웨이 `gateway.py:6149-6152` → `_visible_tools`(`:5216-5224`) | 권한 안의 백엔드 도구 전부 − 끈 앱 − 시험 앱 + 로컬 도구. dev 지금(10-31) 백엔드 도구 560개 · 로컬 14개, cae00 10-27 1,612개. |
| 크기 | dev 카탈로그 스냅샷(10-16, 백엔드 430개 — `tool_search_eval/run.py snapshot`) | 이름 + 설명 + 스키마 JSON 이 약 417,000자다(도구당 약 970자). 같은 밀도면 cae00 의 전체 목록은 160만 자 안팎이다 — 실측은 M-3. |
| 줄이는 길 | 앱 끄기([`../mcp-app-toggle/`](../mcp-app-toggle/PLAN.md) 1단계) — 포털 `users.hub_muted_apps`(`backend/app/auth/user_store.py:93` · `:401-415`) · `/auth/access/apps`(`backend/app/access/routes.py:159-203`) · 권한 응답 `muted_apps`(`:366-367`) · 게이트웨이 PAT 분기의 머리(`gateway.py:6841-6849`) · 화면 `frontend/src/components/HubAppsPanel.tsx`(토큰 화면 탭 '허브에 보일 앱', `TokenPage.tsx:292`) | 끈 앱은 목록 **과 검색** 에서 빠진다(숨김만 — 이름으로는 부른다). 웹 챗 PAT · 절차 PAT · GW_TOKEN 은 면제(D-2). 게이트웨이가 목록 변경을 알리지 않아 재연결해야 바뀐다. |
| 앱별 서버(2단계) | `docs/mcp-app-toggle/context-notes.md` D-1 | 보류 — 도구 이름이 `mcp__hwax-<앱>__X` 로 바뀌어 허용 규칙 47개(`.claude/settings.json`)가 깨지고, 서버 항목 · PAT 사본 · 프로세스가 앱 수만큼 는다. |
| 찾기 · 부르기 | `search_tools`(`gateway.py:3066-3084` — '기본 노출에서 숨겨진 도구도 여기서는 전부 찾아진다') · `invoke_tool`(`:2608-2626` — 안쪽 이름으로 바꿔 정상 길을 탄다, 로컬 도구도 닿는다 `:6180-6250`) · 지침 1번(`:1789-1791`) | 가벼운 모드의 두 도구는 이미 있다. 07-21 설계([`../MCP-TOKEN-SAVING-DESIGN.md`](../MCP-TOKEN-SAVING-DESIGN.md) §1 A · §3-1 — 머리 `x-hwax-tool-mode: meta`)가 같은 생각을 적었고 구현하지 않았다. |
| 영역 | 게이트웨이 `tool_areas.json`(영역 14 · 앱 기본 34 · 도구 지정 136 · 이름 패턴 7) · `_area_of`(`:2527-2536`) · `list_tool_apps(by='area')`(`:3717-3757`) | 묶음 단위로 쓸 분류가 있다. dev 영역별 도구 수 — cad 144 · mesh 67 · expert 48 · calc 47 · material 45 · knowledge 39 · voc 37 · result 37 · sim 33 · report 31 · system 23 · research 12 · data 11. 허브 셋은 data 다. |
| 가벼운 모드의 값 | 파괴 · 제어 이름 막이(`:2636-2651` · `:6206-6215`) · 패널 도구는 이름으로 직접(지침 1번) · 허용 규칙 47개에 `search_tools` · `invoke_tool` 이 없다 · 서버 지침은 2,048자 안이어야 하는데 지금 2,023자(`:1785-1829`, 주석 `:1820-1821`) | 가벼운 모드에서 파괴 · 제어 도구는 닿지 않고, 패널이 안 뜨고, 모든 호출이 `invoke_tool` 하나의 허락으로 뭉친다(낱낱이 묻거나 통째로 허락하거나). 지침에 줄을 더할 자리가 없다. |
| 파이프라인 | 리포 `infra/pipeline/*.js` 는 리포 `.mcp.json`(개인 PAT)으로 돈다 — `BY_NAME`(mcp-app-toggle D-7 · D-8) | 사람 설정 하나로 목록을 줄이면 이 길도 함께 준다. 이 길을 가를 표지는 `.mcp.json` 머리뿐이다(D-7). |
| 쓰임(dev, 참고) | dev 감사 30일 · 개인 PAT(`via: pat`) | 529회 · 개발자 한 명 · 영역 10개. 상위 3개 영역이 호출의 73%, 상위 5개가 89% — 사람 하나라 운영 판단에 쓰지 않는다(cae00 은 M-4). |

### 2.2 빈 곳

- 목록만 줄이고 검색 · 부르기는 그대로 두는 길이 없다 — 끄기는 검색에서도 뺀다('관심 없다' 와 '목록이 작았으면' 은 세기가 다르다).
- 찾기 · 부르기 두 도구만 보이는 모드가 없다.
- 영역 분류는 있는데 사람이 고르는 단위로 쓰이지 않는다.
- 같은 사람의 클라이언트끼리(리포 파이프라인 · 다른 프로젝트 · Desktop) 목록을 달리할 길이 없다.

### 2.3 안

#### 고르는 자리(V)

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| V-A 포털 사람 설정 | `users.hub_view`(보기 · 영역) → 권한 응답 `view` → 게이트웨이 PAT 분기 → 목록. 끄기와 같은 길 · 같은 면제 · 같은 캐시 깨기. | 한 곳에서 고르고 모든 개인 클라이언트가 받는다. 토큰 · 배치를 다시 만들지 않는다. 화면이 있다. | 사람에 하나 — 리포 파이프라인도 같이 준다. |
| V-B 연결 머리 | 클라이언트 설정의 머리 `X-HWAX-View`(`full` · `light` · `bundle:<영역>,…`). | 프로젝트 · 클라이언트마다 다르게 둔다. 리포 `.mcp.json` 은 `${HWAX_GATEWAY_VIEW:-full}` 로 늘 전체. 포털 저장소가 필요 없다. | 바꾸려면 설정을 고치거나 배치를 다시 돌린다(배치는 사고가 가장 잦던 자리 — `setupBat.ts` 머리 주석). |
| V-C 토큰 칸 | PAT 발급 때 `view` 칸을 박는다(`backend/app/auth/routes/pat.py:95-109`). | 새 통로가 없다. | 바꾸려면 토큰을 새로 낸다. 자격에 선호를 섞는다. 배치 하나가 여러 클라이언트에 같은 토큰을 심어 클라이언트별로도 못 가른다. |

#### 묶음 단위(U)

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| U-A 영역 | `tool_areas.json` 의 영역 키(14개)를 고른다. | 이미 있고 손보고 있다(새 앱 점검 E-6 이 미분류를 짚는다). 앱보다 하는 일에 가깝다. | 미분류 도구는 어느 묶음에도 안 든다(검색으로만). 영역 하나가 클 수 있다(cad — dev 144). |
| U-B 앱 | 앱을 골라 싣는다(끄기의 반대). | 단순하다. | 앱 하나가 크고(StepForge dev 175) 하는 일이 섞인다. |
| U-C 따로 짠 묶음 표 | `bundles.json`(이름 → 영역 · 앱 · 도구). | 이름이 친숙하다. | 새 손 표 하나를 더 손본다. |

#### 가벼운 모드의 도구(L)

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| L-A 둘 | `search_tools` · `invoke_tool`. | 요청 문구 그대로. 목록이 가장 작다. `list_tool_apps` 같은 로컬 도구도 `invoke_tool` 로 닿는다. | 앱 목록을 보려면 한 번 더 거친다. |
| L-B 셋 | + `list_tool_apps`. | 권한 없음 · 끈 앱 안내(지침 9 · 10번)를 바로 부른다. | 하나 더. |
| L-C + 패널 도구 | + 권한 안의 패널 도구(`_meta.ui`). | 패널이 뜬다. | 수가 앱마다 다르고 '두 도구' 가 아니다. |

### 2.4 권장 — 걸음

V-A + V-B(머리가 이기고, 리포 `.mcp.json` 은 늘 전체) · U-A · L-A 다. 묶음 보기에는 정본 읽기 도구(어휘표 search 칸의 다섯 — `object_resolve` · `objects_list` ·
`objects_summary` · `graph_neighbors` · `object_get`)를 늘 싣고 형제 사본은 싣지 않는다(E-2 X-B). V-B 는 따로 서는 기능이 아니라 V-A 의 덮어쓰기다 —
리포 파이프라인을 사람 설정과 떼는 유일한 표지라서 둔다.

| 걸음 | 무엇 · 고칠 곳 | 시험 | 받아들임 |
|---|---|---|---|
| E4-1 게이트웨이 — 목록 함수 가르기 | `_visible_tools`(검색 · 평가 · 앱 목록이 쓴다)는 그대로 두고 `tools/list`(`:6149-6152`)만 새 `_listed_tools` 를 쓴다 — 보기를 얹은 것. 가벼운 = 두 도구. 묶음 = 고른 영역의 백엔드 도구 + 정본 읽기 다섯((정본 키, 원래 이름)으로 고른다 — 노출 이름 규칙과 무관) + 로컬 도구 전부, 형제 사본 뺌. **보기가 검색을 줄이면 안 된다** — `_visible_tools` 에 걸면 가벼운 모드의 `search_tools` 가 빈손이 된다. | 가벼운 — 목록은 두 이름, `search_tools` 답이 전체 보기와 바이트까지 같다, `invoke_tool` 이 목록 밖 도구에 닿고 권한 검사는 그대로 · 묶음 — 목록 이름이 전체 보기 이름의 부분집합(이름을 안 바꾼다), 형제 빠짐, 정본 읽기 다섯 있음 · 끈 앱은 어느 보기에서도 빠진다(끄기가 더 세다). | 게이트웨이 시험. |
| E4-2 게이트웨이 — 보기 정하기 | PAT 분기(`:6799-6853`) — 클라이언트 머리 `x-hwax-view` 가 꼴에 맞으면 그것, 아니면 권한 응답의 `view`, 없으면 전체. 정한 값으로 머리를 갈아 끼운다. 웹 챗 PAT · 절차 PAT 는 늘 전체(끄기 면제와 같다), GW_TOKEN 분기(`:6783-6785`)는 머리를 버린다. `list_tool_apps` 에 `view`(보기 · 영역 · 목록에 실은 수 · 보기로 뺀 수 · 모르는 영역 · '목록 밖은 search_tools → invoke_tool'). `/health` 에 기동 뒤 보기별 `tools/list` 수(채택을 잰다). 지침은 고치지 않는다(2,023 / 2,048자). | 포털 가벼운 + 머리 없음 → 가벼운 · 머리 `full` → 전체 · 틀린 꼴의 머리 → 포털 값 + `view.error` · 웹 챗 · 절차 PAT → 전체 · GW_TOKEN + 머리 → 전체. 끄기 시험의 꼴(`test_gateway.py:2185-2233`)을 따른다. | 같다. |
| E4-3 포털 — 저장 · 창구 | `users.hub_view` 칸(지킨 ALTER — `hub_muted_apps` 와 같다), `GET · PUT /auth/access/view`(세션 + CSRF, 영역은 게이트웨이 `/tools-map` 의 `area_meta` 키만, 묶음이면 영역 하나 이상), 권한 응답에 `view`(`access/routes.py:366-367` 옆), 바꾸면 `_invalidate_gateway_cache`(끄기와 같은 도움 함수, `:198`). | `backend/tests/test_hub_apps.py` 꼴 — 옛 DB 에 칸 만들기 · 꼴 검사 · CSRF 없으면 거절 · 권한 응답 칸 · 캐시 깨기 부름. | 포털 시험. |
| E4-4 포털 화면 | 토큰 화면 '허브에 보일 앱' 탭 위에 보기 고르기(전체 · 묶음 · 가벼운)와 영역 칸(내 권한 안의 도구 수 — `/tools-map` 의 map · areas 와 권한 표로 센다). 알림 넷 — 재연결해야 바뀐다 · 가벼운 모드는 패널이 안 뜨고 파괴 · 제어 도구가 안 닿고 모든 호출이 `invoke_tool` 의 허락으로 묻는다 · 미분류 N개는 묶음에 안 든다(찾기로 닿는다) · 리포 파이프라인은 늘 전체. | 있는 화면 시험의 꼴 · 임시 포털 캡처로 좁은 화면. | `pnpm build` · Drive(cae00 은 짓지 못한다). |
| E4-5 리포 · 문서 | 리포 `.mcp.json` 머리에 `"X-HWAX-View": "${HWAX_GATEWAY_VIEW:-full}"`. `docs/mcp-app-toggle` PLAN 에 '2단계 대신 보기' 한 절 · 업데이트 이력 · cae00 안내(server-setup). | — | — |

### 2.5 지키는 것

- 서버 이름 `hwax` 와 노출 이름은 어느 보기에서도 같다 — 보기는 목록에서 빼기만 한다.
- 보기는 선호다, 권한이 아니다 — 목록 밖 도구도 `invoke_tool` 로 닿고 권한 · 읽기 전용 · 파괴 이름 막이는 그대로 건다. 그래서 머리 `full` 이 사람 설정을 덮어도 넓어지는 것은 그 사람이 이미 쓸 수 있는 목록뿐이다.
- `search_tools` · `list_tool_apps` 는 보기와 무관하다(끈 앱 · 시험 앱만 뺀다).
- 웹 챗 · 절차 · 심의(GW_TOKEN)는 늘 전체다.

### 2.6 하지 않는 것

- 앱별 서버(2단계)는 하지 않는다 — 이름이 바뀐다.
- 목록 변경 알림을 새로 내지 않는다 — 끄기처럼 재연결로 둔다.
- 보기로 검색 순위를 바꾸지 않는다(요청은 '목록만').
- 쓰임에서 묶음을 저절로 고르지 않는다(추천 묶음) — M-4 숫자를 본 뒤의 일이다.

## 3. 둘이 만나는 곳

- **묶음 보기의 허브 가족** — 정본만 싣는다(X-B). 형제는 `search_tools` 에서 앱 이름을 부르면 대표로 나온다(C-12 · E2-2).
- **정본 읽기 다섯** — 코어 질문의 첫 걸음(R-1 · R-7)을 어느 묶음에서나 둔다. 가벼운 모드에는 없다(두 도구).
- **한 응답에 역할 · 보기** — `list_tool_apps` 에 `role`(E2-1)과 `view`(E4-2)가 함께 실린다. 개인 Claude 는 둘을 이 한 곳에서 읽는다.
- **이름** — 두 일 다 이름을 바꾸지 않는다. 바꿀 수 있는 유일한 걸음은 E2-3(가족 접두)이고, 그것도 cae00 에서 0 이어야 그대로 간다(M-2 · Q-2).

## 4. 사용자 결정 — 이 세션에서 묻는다

| # | 정할 것 | 고를 것 | 권장 |
|---|---|---|---|
| Q-1 | 비코어 낮추기(C-A) | a) 손잡이로 짓고 기본 끔 — cae00 비교(M-6) 뒤 덧씌우기로 켠다 · b) 기본 켬 · c) 짓지 않는다(웹 챗 규칙 ⑦ 만) | a |
| Q-2 | 허브 가족은 늘 접두(N-A) | a) 한다 — M-2 의 바뀔 이름이 0 이면 그대로, 있으면 그 이름을 알리고 한다 · b) 지금 규칙 + 알림(N-B) · c) 정본만 맨 이름(N-C — 103개 이름이 바뀐다) | a |
| Q-3 | 형제 소개 줄(S-B)의 문안 | a) 칸만 짓고 문안은 운영자가 cae00 덧씌우기에 쓴다(공개 리포에 안 남는다) · b) 일반 낱말 문안을 추적 파일에 둔다 · c) 짓지 않고 DP-03 을 기다린다 | a |
| Q-4 | 개인 전체 보기의 형제 사본(X) | a) 그대로 — 묶음 · 가벼운 보기에서만 뺀다 · b) 전체 보기에서도 뺀다(개인 목록 약 206개 줄어든다) | a |
| Q-5 | StepForge · DynaForge 의 두 설치(OB-04 뒤 둘 다 보통 앱)를 같은 도구 가족으로 | a) 지금은 허브 셋만 · b) 가족으로 두고 정본을 정한다(어느 쪽인지 함께) | a — 어느 쪽이 정본인지 정해진 적이 없다 |
| Q-6 | 보기를 고르는 자리(V) | a) 포털 사람 설정 + 연결 머리 덮어쓰기 · b) 연결 머리만 · c) 포털 설정만(리포 파이프라인도 같이 준다) · d) 토큰 칸 | a |
| Q-7 | 묶음 단위(U) | a) 도구 영역 14개 · b) 앱 · c) 따로 짠 묶음 표 | a |
| Q-8 | 가벼운 모드의 도구(L)와 파괴 · 제어 도구 | 도구 — a) `search_tools` · `invoke_tool` 둘 · b) + `list_tool_apps` · c) + 패널 도구. 파괴 · 제어 — a) 지금처럼 못 부른다(전체 보기로 바꿔 쓴다) · b) 가벼운 모드에서만 막이를 푼다 | 도구 a · 파괴 a |
| Q-9 | 기본 보기 | a) 모두 전체 — 지금과 같다 · b) 새 사용자는 가벼운 · c) 새 사용자는 묶음(추천 영역) | a |
| Q-10 | E-4 를 언제 하나 — C-17 은 '재시험 뒤' 였다 | a) 재시험과 떼어 M-3 · M-4 와 결정 뒤 시작(E-4 의 기준선은 개인 클라이언트 숫자라 16문항이 아니다) · b) 재시험 뒤 E-2 와 함께 | a |

결정이 아니라 **사람이 아는 것** 하나 — Q-11. 개인 Claude 를 쓰는 사람이 주로 쓰는 클라이언트(Claude Code · Desktop · 그 밖)와, 1,600개 목록 때문에 들은 불편(느린 연결 ·
문맥 · 고르기)이 있나. Q-9 의 근거다.

## 5. cae00 에서 먼저 잴 것 — cae00 세션이 읽고 한다

이 절만 읽어도 할 수 있게 쓴다. 이 문서가 든 포털 판을 받은 뒤(`git pull` 또는 update-all) 한다.

- **읽기만 한다.** 서비스를 다시 띄우지 않고, 박스 파일(덧씌우기 · 설정)을 고치지 않고, 리포에 커밋하지 않는다. 쓰는 파일은 홈의 `~/e2e4-*` 뿐이다.
- **숫자와 도구 이름만 적는다.** 질의 원문 · 사람 이름 · 메일 · 주소는 적지 않는다(아래 조각은 처음부터 찍지 않는다).
- **결과는 `~/e2e4-measure-<날짜>.md` 하나에** — 아래 칸 차례 그대로 적는다. 사람이 그 숫자를 dev 세션에 옮긴다.
- update-all 이 도는 동안에는 하지 않는다. M-6 의 평가는 사람이 적은 때 한다(server-setup 7.3).

| # | 무엇 | 무엇을 적나 | 어디에 쓰나 |
|---|---|---|---|
| M-1 | 16문항 재시험 — 이미 계획한 것([server-setup.md](server-setup.md) 4절 '재시험') | FAIL 수 · OT-06 ~ 10 의 첫 도구 앱과 정본 허브 호출 수 · 자기검증 ms p95 | E-2 의 기준선(D-7 · C-17) |
| M-2 | 허브 가족 이름 · 영역별 도구 수 | 허브마다 도구 수 · 접두 없는 이름 수와 이름 · 영역별 도구 수 · 전체 | E2-3 이 바꿀 이름(Q-2) · 묶음 크기 |
| M-3 | 허브 설명 대조 · 목록 크기 | 목록 글자 합 · 영역별 글자 · 가족 이름 수 · 셋 다 있는 이름 · 한 곳에만 있는 이름 · 설명이 다른 이름 · 가족 글자와 형제 몫 | G1(판 어긋남이 지금 있나) · E-4 의 크기(Q-9 · Q-10) · X(Q-4) |
| M-4 | 개인 PAT 쓰임(감사 30일) | 호출 수 · 사람 수 · 영역별 호출 · 사람마다 상위 1 · 2 · 3 · 5개 영역이 덮는 몫(중앙 · 가장 낮음) · 사람마다 쓴 영역 수 | 묶음이 쓸모 있나(U · Q-9) |
| M-5 | 코어 질의의 역할(질의 기록) | 질의 수 · 코어 질의 수 · 코어 질의 상위 5 의 역할 분포 · 뒤이어 부른 도구의 역할과 성공 | G4 의 크기(Q-1) |
| M-6 | 검색 평가 기준선 | ① `/health` 의 `core_vocab` · `search_tuning` 지문 ② 사람이 관리 → '도구 검색 검토' 에서 10-29 의 HG-01 원문 여덟(C-14)에 정답(정본 읽기 도구 — 예 `rootdesigndatahub:objects_summary`)을 단다 ③ `run.py live --detail` 의 판별 hit@1 · hit@5 · MRR@20(출처별) | E2-5 를 켤지(Q-1) — E2-5 가 들어간 뒤 `+noncore_demote` 판을 같은 쌍으로 다시 잰다 |
| M-7 | 박스 덧씌우기 상태 | `/health` 두 곳의 `overlay.present` · `changed`(칸 이름만) | dev 의 기본값과 박스 값이 어디서 갈리나 |
| M-8 | 허브 셋의 자기소개 | 허브마다 `<그 허브 웹 주소>/api/server/profile`(SP — 로그인 없이 읽힌다, MCP `whoami` 의 `platform` 과 같은 값)의 tagline · summary · notes 가 비었나와 길이 | 형제 소개 줄 문안(Q-3)의 바탕 — 문안 초안은 결과 파일에만 쓴다 |

명령 — M-2 ~ M-5 는 한 번에 돈다. 아래 조각은 리포에 넣지 않는다. dev 에서 같은 조각을 dev 자료(카탈로그 스냅샷 · 감사 기록)와 합성 허브 카탈로그(맨 이름 · 판 어긋남 · 소개 줄)로 돌려 셈이 맞는 것을 봤다.

```bash
cd ~/Projects/HWAXMcpGateway
curl -s --noproxy '*' 127.0.0.1:9110/tools-map > ~/e2e4-toolsmap.json                     # 무인증 — 이름 · 앱 · 영역
../HWAXAgentServer/.venv/bin/python tool_search_eval/run.py snapshot --out ~/e2e4-catalog.local.json   # GW_TOKEN 으로 tools/list 한 번(읽기)
python3 - ~/e2e4-toolsmap.json ~/e2e4-catalog.local.json "${GATEWAY_AUDIT:-audit.jsonl}" \
  ../HWAXPortal/backend/config/core_vocab.json tool_search_eval <<'EOF'
# E-2 · E-4 잼 — 숫자와 도구 이름만 찍는다(질의 원문 · 신원 · 주소는 찍지 않는다)
import collections, datetime, glob, json, os, re, sys
tmap_p, cat_p, audit_p, vocab_p, qdir = sys.argv[1:6]
C = collections.Counter
def load(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"  ({p} 못 읽음: {type(e).__name__})")
def merge(a, b):                                   # 어휘표 박스 덧씌우기와 같은 merge patch
    if not isinstance(b, dict):
        return b
    out = dict(a) if isinstance(a, dict) else {}
    for k, x in b.items():
        if x is None:
            out.pop(k, None)
        else:
            out[k] = merge(out.get(k), x)
    return out
v = load(vocab_p) or {}
loc = vocab_p.replace(".json", ".local.json")
if os.path.exists(loc):
    v = merge(v, load(loc) or {}); print("어휘표 덧씌우기 있음 — 덧씌운 값으로 잰다")
canon = (v.get("canonical") or {}).get("app", ""); apps = v.get("apps") or {}
fam = [canon] + [k for k, a in apps.items() if (a or {}).get("role") == "sibling"]
role = lambda k: "정본" if k == canon else (apps.get(k) or {}).get("role") or "그 밖"
m = load(tmap_p) or {"map": {}, "areas": {}}; area = m.get("areas") or {}
print("== M-2 허브 가족 이름")
own = collections.defaultdict(list)
for n, k in (m.get("map") or {}).items():
    own[k].append(n)
for k in fam:
    ns, pre = own.get(k, []), k.replace("-", "") + "_"
    bare = sorted(n for n in ns if not n.startswith(pre))
    print(f"  {k}: 도구 {len(ns)} · 접두 없는 이름 {len(bare)} {bare[:20]}")
print("  영역별 도구 수", C(a or "미분류" for a in area.values()).most_common(), "· 전체", len(m.get("map") or {}))
print("== M-3 허브 설명 대조 · 목록 크기")
c = load(cat_p)
if c:
    rows = c["tools"]
    size = lambda t: len(json.dumps([t["name"], t["description"], t["inputSchema"]], ensure_ascii=False))
    print("  백엔드 도구", len(rows), "· 목록 글자(이름 + 설명 + 스키마)", sum(map(size, rows)))
    by = C()
    for t in rows:
        by[area.get(t["name"]) or "미분류"] += size(t)
    print("  영역별 글자", by.most_common())
    g = collections.defaultdict(dict)
    for t in rows:
        if t["app"] in fam:                        # 정본 설명 앞 소개 줄([…] )은 떼고 견준다
            d = t["description"]
            g[t["original"]][t["app"]] = d.split("] ", 1)[1] if t["app"] == canon and d.startswith("[") and "] " in d else d
    print("  가족 이름", len(g), "· 모두에 있음", sum(len(d) == len(fam) for d in g.values()),
          "· 한 곳에만", sorted(o for o, d in g.items() if len(d) == 1)[:20],
          "· 설명이 다름", sorted(o for o, d in g.items() if len(set(d.values())) > 1)[:20])
    print("  가족 글자", sum(size(t) for t in rows if t["app"] in fam), "· 형제 몫", sum(size(t) for t in rows if t["app"] in fam[1:]))
print("== M-4 개인 PAT 쓰임(30일)")
since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)).isoformat()
per, tot, n = collections.defaultdict(C), C(), 0
try:
    for line in open(audit_p, encoding="utf-8"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("via") != "pat" or str(r.get("ts", "")) < since or not r.get("backend"):
            continue
        a = area.get(r.get("tool")) or "미분류"
        n += 1; tot[a] += 1; per[r.get("caller") or "?"][a] += 1     # 신원은 셈의 열쇠로만
except OSError as e:
    print(f"  (감사 기록 못 읽음: {type(e).__name__})")
print("  호출", n, "· 사람", len(per), "· 영역별", tot.most_common())
for k in (1, 2, 3, 5):
    cov = sorted(sum(x for _, x in cnt.most_common(k)) / sum(cnt.values()) for cnt in per.values())
    if cov:
        print(f"  사람마다 상위 {k}개 영역이 덮는 몫 — 중앙 {cov[len(cov) // 2]:.2f} · 가장 낮음 {cov[0]:.2f}")
print("  사람마다 쓴 영역 수", sorted(len(x) for x in per.values()))
print("== M-5 코어 질의의 역할(질의 기록)")
words = {re.sub(r"\s+", "", str(w).lower()) for e in v.get("search") or [] for w in e.get("words") or []}
krole = lambda key: role(str(key).split(":", 1)[0])
core, top, after, n_all = {}, C(), C(), 0
for f in sorted(glob.glob(os.path.join(qdir, "queries*.local.jsonl"))):
    for line in open(f, encoding="utf-8"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if "q" in r:
            n_all += 1
            core[r.get("id")] = any(w in re.sub(r"\s+", "", str(r["q"]).lower()) for w in words)
            if core[r.get("id")]:
                top.update(krole(t) for t in r.get("top") or [])
        elif core.get(r.get("o")):
            after[(krole(r.get("t", "")), bool(r.get("ok")))] += 1
print("  질의", n_all, "· 코어 질의", sum(core.values()), "· 상위 5 의 역할", top.most_common(),
      "· 뒤이어 부른 도구(역할, 성공)", after.most_common())
EOF
```

- 감사 기록 자리는 `tool_usage_report.py` 와 같다(`GATEWAY_AUDIT`, 없으면 게이트웨이 리포의 `audit.jsonl`). 게이트웨이를 띄운 환경에만 그 변수가 있으면 그 값을 손으로 준다.
- M-6 · M-7 은 따로 한다.

```bash
curl -s --noproxy '*' 127.0.0.1:9110/health | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["core_vocab"]);print(d["search_tuning"])'
curl -s --noproxy '*' 127.0.0.1:9009/health | python3 -c 'import json,sys;print(json.load(sys.stdin)["core_vocab"])'
# 정답 달기(사람) 뒤에
cd ~/Projects/HWAXMcpGateway && ../HWAXAgentServer/.venv/bin/python tool_search_eval/run.py live --detail > ~/e2e4-search-eval-$(date +%F).txt
```

- `~/e2e4-search-eval-*.txt` 에는 질의 원문이 실린다 — 결과 파일에는 판별 숫자만 옮긴다.
- 스냅샷(`~/e2e4-catalog.local.json`)은 도구 설명을 담는다 — 홈에만 두고, 잰 뒤 지워도 된다.
- M-8 의 허브 주소는 이 박스의 설정에서 읽고 결과 파일에도 적지 않는다. 문안 초안에는 사내 이름 · 과제 이름을 넣지 않는다.
- 사람이 PC 에서(선택) — 지금 전체 목록으로 Claude Code · Desktop 이 `hwax` 를 붙는 데 걸리는 시간과 도구 목록이 실리는 모양. Q-11 과 함께 적는다.

## 6. 밖에 물을 것 — 사람이 보낸다

Datahub 플랫폼(허브 셋)에 — Datahub 요청서([`../request-1030/platforms/12-Datahub-platform.md`](../request-1030/platforms/12-Datahub-platform.md))와 같은 묶음으로 사람이 보낸다(10-30 [`../request-1030/outbound.md`](../request-1030/outbound.md) 2절과 같은 길).
답은 그 표의 '답' 칸과 이 문서의 해당 걸음에 옮겨 적는다.

| # | 물을 것 | 왜 |
|---|---|---|
| X-1 | DP-03(설치 소개를 도구 설명에)을 한다면 어떤 꼴(머리 '[…]' · 꼬리 · 줄)이고 언제인가. | 그날 게이트웨이의 정본 소개 줄을 걷는다. E2-2(가족 접기)가 그 꼴과 상관없이 받는지 시험에 그 꼴을 넣는다. |
| X-2 | 도구 103개에 MCP 주석(readOnlyHint · destructiveHint)을 달 계획이 있나. 지금은 없다. | 달리면 쓰기 감점 · 분석 루틴의 읽기 울타리 · 개인 Claude 의 읽기 자동 허락이 이름 추측 대신 그것을 쓴다. |
| X-3 | 세 설치의 판을 같이 올리나, 하나씩 올리나. | 하나씩이면 그 사이 접기 · 이름이 흔들린다 — E2-2 · E2-3 이 받는 경우다. |
| X-4 | 형제 둘의 자기소개(summary · notes)가 비었으면 채워 달라. | 형제 소개 줄(S-B) 문안의 바탕이고, 그쪽 MCP 손님(우리를 거치지 않는 손님)에게도 같은 말이 간다. |

## 7. 순서 · 가늠 · 받아들임

| 차례 | 무엇 | 누가 | 가늠 | 다음으로 가는 조건 |
|---|---|---|---|---|
| 0 | 4절 결정(Q-1 ~ Q-10)과 Q-11 | 사용자(이 세션) | — | 답이 이 문서 4절에 적힌다 |
| 1 | 5절 M-2 ~ M-8(M-1 은 이미 잡힌 재시험) | cae00 세션 · 사람 | 반나절 | 숫자가 dev 에 온다 |
| 2 | E-4 — E4-1 ~ E4-5 | dev | 1.5일 | 시험 통과 · dev 실검증(개인 PAT 로 보기 셋 — 게이트웨이 · 포털 재기동은 사용자 확인 뒤) · 화면 Drive. Q-10 이 b 면 M-1 뒤로 |
| 3 | E-2 — E2-1 ~ E2-4 | dev | 1일 | 시험 통과 · cae00 반영 뒤 M-2 · M-3 을 다시 — 바뀐 이름 0, 접힌 줄이 그대로 |
| 4 | E2-5(기본 끔) | dev → cae00 | 0.5일 | cae00 `run.py live` 에서 `+noncore_demote` 판이 doc · box 의 hit@5 를 떨어뜨리지 않고 코어 box 쌍(M-6 ②)을 올리면 → cae00 덧씌우기 `{"switches": {"noncore_demote": true}}` → 16문항 재시험(OT-06 ~ 10 첫 도구가 코어) |
| 5 | E2-6(미룸) | — | — | M-5 · M-6 에서 형제가 잘못 오르거나 밀리는 것이 보일 때 |

1차 · 2차와 같이, 끝난 리포부터 올리고 cae00 반영은 update-all 이다. dev 서비스 재기동은 사용자 확인 뒤다(다른 세션의 미반영 커밋도 함께 켜진다).
