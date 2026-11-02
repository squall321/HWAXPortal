# 온톨로지 먼저 — cae00 에서 사람이 할 일(받기 · 읽기 표지 · 확인 · 재기)

무엇을 왜 바꿨는지는 [PLAN.md](PLAN.md) · [context-notes.md](context-notes.md)(OF-15 부터 — 지은 것), 할 일은 [checklist.md](checklist.md)다. 이 판은 dev 의
가지 `wt1102/ontology-build`(세 리포)에서 지었고 병합 · 올리기는 이 문서 밖이다. 받는 길은 그대로 `git pull && update-all` 이다.

## 1. 무엇이 바뀌나 — 기본값 그대로인 것과 덧씌우기로 켜는 것

| 걸음 | 받으면 곧바로(기본) | 박스 덧씌우기로 켜야 서는 것 |
|---|---|---|
| F0 좌석 자유 조회 | 겹침 때문에 게이트웨이가 접두를 단 읽기를 원래 이름으로 판정한다(리스크 심사 · 선언 백엔드 · 허브 가족은 그대로) — 게이트웨이 · 에이전트 서버 둘 다 새 판이어야 선다 | — |
| 챗 칸(M1) | 고정 몫이 어휘표 `ontology` 칸에서 온다 — 기본 표는 옛 고정 몫과 같아 챗 프롬프트 · 도구 묶음 · 설명이 바이트까지 그대로다 | 입구(`entry`) — 규칙 ⑧ · '온톨로지 입구' 표지(4절) |
| 검색 손잡이(M3) | `onto_first` 는 끔 — 순위 그대로 | `search_tuning.local.json` 으로 켠다(5절) |
| 심의 미리보기(M4) | 심의 시작 · 챗→심의 브리프에 '온톨로지 먼저 보기' 칸이 보인다 — 주제 과제가 있을 때만 켜지고, 정본 허브 도구 둘이 이 박스에서 읽기로 확인돼야 부른다 | 읽기 표지(2절)가 먼저다 |

## 2. 읽기 표지(M-R) — 미리보기를 쓰기 전에

정본 허브의 `object_resolve` 는 이름에 조회 낱말이 없어(`resolve` 는 일부러 뺐다) 박스 읽기 목록에 올라야 읽기다. `graph_neighbors` 는 이름 낱말
(`neighbors`)로 이미 읽기다. 게이트웨이 박스 덧씌우기 `read_tools.local.json`(게이트웨이 리포 자리, gitignore — 바뀐 시각을 보고 재기동 없이 읽는다)에
더한다. 형제 허브 · DynaForge 온톨로지 셋은 루틴 단계 · 패널에도 쓰려면 함께 더한다(PLAN §8 M-R).

```json
{"tools": ["rootdesigndatahub:object_resolve",
           "failuretrace:object_resolve", "caegroupdatahub:object_resolve",
           "heax-kooremapper_mcp:ontology_types", "heax-kooremapper_mcp:ontology_object", "heax-kooremapper_mcp:ontology_sync_state"]}
```

이미 파일이 있으면 `tools` 목록에 더한다(목록을 통째로 바꾸지 않게). 확인 — `curl -s http://127.0.0.1:9110/tools-map` 의 `routine_read` 에
`rootdesigndatahub_object_resolve` 와 `rootdesigndatahub_graph_neighbors` 가 든다. 빠져 있으면 미리보기는 부르지 않고 '이 박스에서 읽기로 확인되지
않았다 — … read_tools.local.json 에 … 를 더하면 열린다' 를 보인다.

## 3. 받은 뒤 확인

- **F0** — 받은 편지함 Q21 을 다시 읽는다. 새 심의의 '전문가 자유 조회 활성 — N종' 이 Q20 의 '정적' 어림만큼만 오르고, 심의 하나의 좌석별 도구 목록을
  앞뒤로 견줘 새로 든 도구가 분야 도구를 밀어내지 않으며, 게이트웨이 감사의 엔진 호출에 `refused: no-connection` 이 늘지 않는다(PLAN §3.4). `/tools-map`
  에 `orig` 와 선언 백엔드 앱 줄의 `declared: true` 가 보인다. 기준일 심의(as_of — 소급 검증)는 F0 몫을 받지 않으니(OF-22) N 은 기준일 없는 심의로
  견준다.
- **챗 기본값** — 에이전트 서버 `/health` 의 `core_vocab.ontology` 가 `{"present": true, "apps": [4개], "entries": [], "dropped": [], "reserve": 16, "missing": []}`
  꼴이다(허브 둘이 붙은 박스 — `missing` 이 비지 않으면 그 이름이 이 박스 도구 지도에 없다). 두 서비스의 `core_vocab.fingerprint` 가 같다(update-all §6).
- **미리보기** — 실제 주제 하나로 사람이 본다(PLAN §7.3 막는 기준 — 오류 없이 돈다). 심의 시작에서 주제 과제를 고르고 '온톨로지 먼저 보기' → 주제 과제
  · 이웃 행이 보이고, 고른 행이 원천 근거 수에 든다. 심의 결정문의 [e:N] 이 '온톨로지 먼저 · …' 근거를 짚는지, 미리보기에 걸린 시간을 적는다.
  이웃 행을 고르면 주제 과제 칸이 함께 골라지고(그 key · 허브 id 가 근거에 실린다 — 칸에 적혀 있다) 주제 과제를 빼면 고른 이웃 행도 빠진다(OF-29).
  앞 · 뒤 과제(plm_task)는 행에 없다(OF-28). 허브 답을 읽지 못하면 '없음' 이 아니라 '못 물어봄' 으로 보인다(OF-26 · OF-27).

## 4. 챗 입구를 켜고 잰다(M2 — 사용자 결정 OF-14 ④)

`backend/config/core_vocab.local.json`(포털 리포 자리, gitignore — 에이전트 서버 · 게이트웨이가 바뀐 시각을 보고 재기동 없이 읽는다)에 입구를 적는다.
JSON merge patch 라 목록은 통째로 바뀐다 — StepForge 줄은 tools 를 다시 적는다(그 줄은 고정 몫이라 `onto_search` 도 고정 몫에 든다).

```json
{"ontology": {"apps": {
  "heax-step_forge": {"tools": ["find_plm_task", "onto_search"], "entry": "onto_search"},
  "heax-kooremapper_mcp": {"entry": "list_tasks"}
}}}
```

- 입구는 판정(exact · candidates · none)이나 후보 목록을 돌려주는 도구만 적는다. SignalForge `resolve_product_keyword` · MX 백서 `wiki_entity` 는 첫 줄을
  스스로 골라 아직 아니다(OF-5). 허브 가족(정본 · 형제)의 entry 는 버린다.
- StepForge `onto_search` 는 `resolve=true` 일 때 판정을 준다(설명이 말한다) — 재기에서 첫 호출의 인자도 본다(OF-15 의 남은 위험).
- 켠 뒤 `/health core_vocab.ontology.entries` 에 두 줄이 보이고 `dropped` 가 비었는지 본다. 켜고 끄면 챗 에이전트 묶음을 새로 짓는다(캐시 열쇠).
  켜고 끈 직후 게이트웨이가 불통이면 그 턴은 도구 없이 돈다 — 스냅샷 폴백도 입구별이다(OF-24).
- 입구를 켜면 고정 몫도 이 박스 도구 지도로 푼다 — 다른 앱(운영 사본 등)이 쥔 이름은 세우지 않는다. 끄면 지도를 보지 않는 옛 이름 규칙 그대로다(OF-23).
  허브 StepForge · DynaForge 가 내려간 날에는 켬 · 끔의 고정 몫이 달라 재기가 섞이니, 재기 전에 `/tools-map` 에서 `list_tasks` · `find_plm_task` 가
  허브 앱(`heax-kooremapper_mcp` · `heax-step_forge`) 것인지 본다.
- 재기 — 같은 판 · 같은 날, 덧씌우기 끔과 켬으로 10-30 재시험의 16문항 · 운영자 14명(PLAN §7.1의 잴 것 · 받아들일 기준). 하나라도 어기면 덧씌우기를
  지운다(재기동 없이 곧바로).

## 5. 개인 Claude 검색 손잡이(M3)

박스 정답쌍(`tool_search_eval/pairs.local.jsonl`)에 '앱 이름을 부른 질의 → 그 앱 입구' 쌍을 더하고 `/search-eval` 의 `+onto_first` 판을 본다(PLAN §7.2).
입구 쌍의 1위 적중이 오르고 앱을 부르지 않은 질의 · 코어 질의의 순위가 같으면 게이트웨이 `search_tuning.local.json` 에 켠다.

```json
{"switches": {"onto_first": true}}
```

켠 뒤 `/health` 의 `search_tuning.switches_on` 에 `onto_first` 가 보인다. 서버 지침 · 도구 설명은 바뀌지 않는다.

## 6. 받은 편지함

[`../cae00-inbox/2026-11-02.md`](../cae00-inbox/2026-11-02.md) Q20 ~ Q22(읽기만)는 그대로 쓴다 — Q20 은 받기 전후 둘 다(F0 의 '정적' 어림 · 이름 지도),
Q21 은 받은 뒤 다시, Q22 는 미리보기 · 입구를 켠 뒤의 지연 · 크기를 함께 본다.
